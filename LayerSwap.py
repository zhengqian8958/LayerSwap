import requests
import time
from enum import Enum
from loguru import logger
from web3 import Web3

class BridgeNetwork(Enum):
    ZKERA = "ZKSYNCERA_MAINNET"
    ARBI = "ARBITRUM_MAINNET"
    BSC = "BSC_MAINNET"
    STARKNET = "STARKNET_MAINNET"
    SCROLL = "SCROLL_MAINNET"

def getDepositAddress(sourceWallet, targetWallet, value, sourceNetwork:BridgeNetwork, destinationNetwork:BridgeNetwork):
    headers = {
        'authority': 'identity-api.layerswap.io',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        'access-control-allow-origin': '*',
        'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'origin': 'https://www.layerswap.io',
        'referer': 'https://www.layerswap.io/',
        'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'x-ls-apikey': 'NDBxG+aon6WlbgIA2LfwmcbLU52qUL9qTnztTuTRPNSohf/VnxXpRaJlA5uLSQVqP8YGIiy/0mz+mMeZhLY4/Q',
        'x-ls-correlation-id': '552ba0ea-e8d5-495a-9f53-4d031ff705a4',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    }
    data = {
        'client_id': 'layerswap_bridge_ui',
        'grant_type': 'credentialless',
    }
    client = requests.Session()  
    response = client.post('https://identity-api.layerswap.io/connect/token', headers=headers, data=data)
    logger.debug(f"{response.status_code}:{response.text}")
    if response.status_code == 200:
        accessToken = response.json()['access_token']
    else:
        logger.error(f"Get token failed: {response.status_code}, {response.text}")
        return None
    
    time.sleep(2)
    headers['authorization'] = f'Bearer {accessToken}'
    headers['content-type'] = 'application/json'
    json_data = {
        'amount': str(value),
        'source_network': sourceNetwork.value,
        'destination_network': destinationNetwork.value,
        'source_token': 'ETH',
        'destination_token': 'ETH',
        'source_address': sourceWallet,
        'destination_address': targetWallet,
        'refuel': False,
        'use_deposit_address': False,
    }
    response = client.post('https://api.layerswap.io//api/v2/swaps', headers=headers, json=json_data)
    logger.debug(f"{response.status_code}:{response.text}")
    if response.status_code == 200:
        targetAddress = response.json()['data']['deposit_actions'][0]['to_address']
        callData = response.json()['data']['deposit_actions'][0]['call_data']
    else:
        logger.error(f"Get swapID failed: {response.status_code}, {response.text}")
        return None
    
    return targetAddress, callData


def bridge(w3, wallet, key, targetWallet, value, sourceNetwork:BridgeNetwork, destinationNetwork:BridgeNetwork):
    targetAddress, callData = getDepositAddress(wallet, targetWallet, value, sourceNetwork, destinationNetwork)
    # get current gas
    gas = float(w3.from_wei(w3.eth.gas_price,'gwei')) * 1.1
    # sent tx
    txHash = transaction(w3, wallet, key, targetAddress, gas=gas, value=value, data=callData)
    result = bool(w3.eth.wait_for_transaction_receipt(txHash)['status'])
    if result:
        logger.success(f"{wallet} bridge {value}ETH to success {txHash}")
    else:
        logger.error(f"{wallet} bridge failed {txHash}")


def transaction(w3, wallet, key, to, gas=0, gasLimit=220000, value=0, data="", nonce=0):
    if nonce==0:
        nonce = w3.eth.get_transaction_count(wallet)
    # to address is empty incase contract deployment. Therefore convert to checksum address only if it's not empty
    if len(to) > 0:
        to = w3.to_checksum_address(to)
    tx = {
        'nonce': nonce,
        'from': wallet,
        'to': to,
        'value': w3.to_wei(value, 'ether'),
        'gas': gasLimit, 
        'data': data # can be used to add the mint command
    }
    # Use current live gas fee if it's not specified by user
    if gas == 0 :
        # use the wei value directly
        tx['gasPrice'] = w3.eth.gas_price

    signedTx = w3.eth.account.sign_transaction(tx, key)
    txHash = w3.eth.send_raw_transaction(signedTx.rawTransaction)
    return txHash.hex()

if __name__ == "__main__":
    wallet = "Your Wallet"
    key = "Your Wallet Key"
    value = 0.001 # Your bridge amount
    rpc = "Source Network RPC"
    w3 = Web3(Web3.HTTPProvider(rpc))
    bridge(w3, wallet, key, wallet, value, BridgeNetwork.ARBI, BridgeNetwork.SCROLL)