import os
import time
import json
import threading
import schedule
from datetime import datetime, timedelta
from monero.wallet import Wallet
from monero.backends.jsonrpc import JSONRPCWallet
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class MoneroWalletManager:
    def __init__(self, master_wallet_address):
        self.master_wallet_address = master_wallet_address
        self.active_wallets = {}
        self.wallet_lock = threading.Lock()
        self.data_file = "wallet_data.json"
        self.load_wallet_data()
        
        self.cleanup_thread = threading.Thread(target=self._cleanup_scheduler, daemon=True)
        self.cleanup_thread.start()

    def load_wallet_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.active_wallets = {
                    k: {**v, 'created_at': datetime.fromisoformat(v['created_at'])}
                    for k, v in data.items()
                }

    def save_wallet_data(self):
        with open(self.data_file, 'w') as f:
            data = {
                k: {**v, 'created_at': v['created_at'].isoformat()}
                for k, v in self.active_wallets.items()
            }
            json.dump(data, f)

    def create_temporary_wallet(self):
        wallet = Wallet(JSONRPCWallet(port=18081, host='monerod'))
        address = wallet.address()
        
        with self.wallet_lock:
            self.active_wallets[address] = {
                'created_at': datetime.now(),
                'wallet': wallet
            }
            self.save_wallet_data()
        
        return address

    def delete_wallet(self, address):
        with self.wallet_lock:
            if address in self.active_wallets:
                self._transfer_funds_to_master(address)
                del self.active_wallets[address]
                self.save_wallet_data()
                return True
        return False

    def get_active_wallets(self):
        current_time = datetime.now()
        active_wallets = []
        
        with self.wallet_lock:
            for address, data in self.active_wallets.items():
                time_remaining = (data['created_at'] + timedelta(minutes=30) - current_time)
                if time_remaining.total_seconds() > 0:
                    active_wallets.append({
                        'address': address,
                        'minutes_remaining': int(time_remaining.total_seconds() / 60),
                        'balance': self._get_wallet_balance(address)
                    })
        
        return active_wallets

    def _get_wallet_balance(self, address):
        wallet_data = self.active_wallets.get(address)
        if wallet_data:
            return wallet_data['wallet'].balance()
        return 0

    def _transfer_funds_to_master(self, address):
        wallet_data = self.active_wallets.get(address)
        if wallet_data:
            balance = self._get_wallet_balance(address)
            if balance > 0:
                wallet_data['wallet'].transfer(self.master_wallet_address, balance)

    def _cleanup_expired_wallets(self):
        current_time = datetime.now()
        expired_addresses = []
        
        with self.wallet_lock:
            for address, data in self.active_wallets.items():
                if current_time - data['created_at'] > timedelta(minutes=30):
                    expired_addresses.append(address)
            
            for address in expired_addresses:
                self.delete_wallet(address)

    def _cleanup_scheduler(self):
        schedule.every(1).minutes.do(self._cleanup_expired_wallets)
        
        while True:
            schedule.run_pending()
            time.sleep(60)

master_wallet = os.getenv('MASTER_WALLET_ADDRESS', '')
if not master_wallet:
    raise ValueError("Please set the MASTER_WALLET_ADDRESS environment variable.")

wallet_manager = MoneroWalletManager(master_wallet)

@app.route('/wallet', methods=['POST'])
def create_wallet():
    """Create a new temporary wallet"""
    address = wallet_manager.create_temporary_wallet()
    return jsonify({
        'status': 'success',
        'address': address
    })

@app.route('/wallet/<address>', methods=['DELETE'])
def delete_wallet(address):
    """Delete a specific wallet"""
    success = wallet_manager.delete_wallet(address)
    return jsonify({
        'status': 'success' if success else 'error',
        'message': 'Wallet deleted' if success else 'Wallet not found'
    })

@app.route('/wallets', methods=['GET'])
def list_wallets():
    """List all active wallets"""
    wallets = wallet_manager.get_active_wallets()
    return jsonify({
        'status': 'success',
        'wallets': wallets
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)