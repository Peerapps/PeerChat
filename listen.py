from bitcoinrpc.authproxy import AuthServiceProxy as rpcRawProxy #Deals with just raw bytes

import peerapps_helpers
import time

rpc_raw = rpcRawProxy(peerapps_helpers.get_rpc_url())

processed_transactions = {}
while True:
    peerchat_transactions = peerapps_helpers.scan_mempool(rpc_raw) #[(op_return_data, from_user_address, tx_id), ...]
    for tx in peerchat_transactions:
        if tx['tx_id'] not in processed_transactions:
            processed_transactions[tx['tx_id']] = tx
            print tx['address'] + ": " + tx['data'][5:]
    time.sleep(1)


