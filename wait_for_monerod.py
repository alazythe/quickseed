import time
import requests

def is_node_synchronized():
    try:
        response = requests.post('http://monerod:18081/json_rpc', json={
            "jsonrpc": "2.0",
            "id": "0",
            "method": "get_info"
        })
        data = response.json()
        if 'result' in data:
            result = data['result']
            return (result['target_height'] == 0 or 
                    result['height'] == result['target_height']) and not result.get('synchronized', False)
    except Exception as e:
        print(f"Error checking node synchronization: {e}")
    return False

def wait_for_sync():
    print("Waiting for Monero node to synchronize...")
    while not is_node_synchronized():
        time.sleep(10) 
    print("Monero node is synchronized.")

if __name__ == "__main__":
    wait_for_sync()