import os
import time
import json
import threading
import schedule
from datetime import datetime, timedelta
from monero.wallet import Wallet
from monero.backends.jsonrpc import JSONRPCWallet

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
        wallet = Wallet(JSONRPCWallet(port=28088))
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

def main():
    master_wallet = os.getenv('MASTER_WALLET_ADDRESS', '')
    
    if not master_wallet:
        print("Please set the MASTER_WALLET_ADDRESS environment variable.")
        return

    manager = MoneroWalletManager(master_wallet)
    
    while True:
        print("\nMonero Temporary Wallet Manager")
        print("1. Create new temporary wallet")
        print("2. View active wallets")
        print("3. Delete a wallet")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ")
        
        if choice == "1":
            address = manager.create_temporary_wallet()
            print(f"Created new temporary wallet: {address}")
        
        elif choice == "2":
            active_wallets = manager.get_active_wallets()
            if not active_wallets:
                print("No active wallets")
            else:
                for wallet in active_wallets:
                    print(f"\nAddress: {wallet['address']}")
                    print(f"Time remaining: {wallet['minutes_remaining']} minutes")
                    print(f"Balance: {wallet['balance']} XMR")
        
        elif choice == "3":
            address = input("Enter wallet address to delete: ")
            if manager.delete_wallet(address):
                print("Wallet deleted successfully")
            else:
                print("Wallet not found")
        
        elif choice == "4":
            print("Exiting...")
            break
        
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()