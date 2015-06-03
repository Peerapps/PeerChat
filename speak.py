from bitcoinrpc.authproxy import AuthServiceProxy as rpcRawProxy #Deals with just raw bytes
from bitcoin.rpc import Proxy as rpcProcessedProxy #Mimic actual bitcoin core C structures

import peerapps_helpers

rpc_raw = rpcRawProxy(peerapps_helpers.get_rpc_url())
rpc_processed = rpcProcessedProxy()

my_addresses = rpc_raw.listunspent(0)
#peerapps_helpers.pretty_print(my_addresses)

while True:
    speak = raw_input("Speak: ")
    print
    peerapps_helpers.submit_opreturn(rpc_processed, my_addresses[0]['address'], "pcstl"+speak)
    print
    print