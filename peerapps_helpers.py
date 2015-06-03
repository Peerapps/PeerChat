from bitcoinrpc.authproxy import JSONRPCException

import datetime
import platform
import os

def parse_transaction(rpc_raw, tx_id):
    tx_info = rpc_raw.decoderawtransaction(rpc_raw.getrawtransaction(tx_id))
    for vout in tx_info['vout']:
        if vout['scriptPubKey']['asm'].startswith("OP_RETURN"):
            try:
                op_return_data = vout['scriptPubKey']['asm'].split(' ')[1].decode('hex')
            except:
                continue
            if op_return_data[:5] == "pcstl": #Peerchat op_return data is prefixed with pc
                from_user_address = ""
                for inp in tx_info['vin']:
                    input_raw_tx = rpc_raw.decoderawtransaction(rpc_raw.getrawtransaction(inp['txid']))
                    from_user_address = input_raw_tx['vout'][inp['vout']]['scriptPubKey']['addresses'][0]
                    break
                return {
                    "data": op_return_data,
                    "address": from_user_address,
                    "tx_id": tx_id
                }
    return None

def scan_mempool(rpc_raw):
    """
    returns [{
                "data": op_return_data,
                "address": from_user_address,
                "tx_id": tx_id
            }, ...]
    """
    unconfirmed_transactions = rpc_raw.getrawmempool()
    peerchat_messages = []
    for tx_id in unconfirmed_transactions:
        peerchat_data = parse_transaction(rpc_raw, tx_id)
        if peerchat_data:
            peerchat_messages.append(peerchat_data)
    return peerchat_messages

def scan_block(rpc_raw, block_index):
    """
    returns [{
                "data": op_return_data,
                "address": from_user_address,
                "tx_id": tx_id
            }, ...]
    """
    peerchat_messages = []
    try:
        block_hash = rpc_raw.getblockhash(block_index) #convert block index to block hash
        bi = rpc_raw.getblock(block_hash) #get list of tx_ids in block
        for tx_id in bi['tx']:
            peerchat_data = parse_transaction(rpc_raw, tx_id)
            if peerchat_data:
                peerchat_messages.append(peerchat_data)
    except JSONRPCException:
        pass #at last block
    return peerchat_messages


def submit_opreturn(rpc_connection, address, data):
    from bitcoin.core import CTxIn, CMutableTxOut, CScript, CMutableTransaction, CENT, b2x, b2lx
    from bitcoin.core.script import OP_CHECKSIG, OP_RETURN

    txouts = []

    unspent = sorted([y for y in rpc_connection.listunspent(0) if str(y['address']) == address], key=lambda x: hash(x['amount']))

    txins = [CTxIn(unspent[-1]['outpoint'])]

    value_in = unspent[-1]['amount']

    change_pubkey = rpc_connection.validateaddress(address)['pubkey']
    change_out = CMutableTxOut(int(value_in - 2*CENT), CScript([change_pubkey, OP_CHECKSIG]))
    digest_outs = [CMutableTxOut(1*CENT, CScript([OP_RETURN, data]))]
    txouts = [change_out] + digest_outs
    tx = CMutableTransaction(txins, txouts)

    print "SUCCESS! Raw Transaction =", tx.serialize().encode('hex')
    r = rpc_connection.signrawtransaction(tx)
    assert r['complete']
    tx = r['tx']

    rpc_connection.sendrawtransaction(tx)

def get_config():
    if platform.system() == 'Darwin':
        btc_conf_file = os.path.expanduser('~/Library/Application Support/PPCoin/')
    elif platform.system() == 'Windows':
        btc_conf_file = os.path.join(os.environ['APPDATA'], 'PPCoin')
    else:
        btc_conf_file = os.path.expanduser('~/.ppcoin')
    btc_conf_file = os.path.join(btc_conf_file, 'ppcoin.conf')

    # Extract contents of ppcoin.conf to build service_url
    with open(btc_conf_file, 'r') as fd:
        # PPCoin Core accepts empty rpcuser, not specified in ppc_conf_file
        conf = {'rpcuser': ""}
        for line in fd.readlines():
            if '#' in line:
                line = line[:line.index('#')]
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            conf[k.strip()] = v.strip()

        conf['rpcport'] = int(conf.get('rpcport', -1))
        conf['rpcssl'] = conf.get('rpcssl', '0')

        if conf['rpcssl'].lower() in ('0', 'false'):
            conf['rpcssl'] = False
        elif conf['rpcssl'].lower() in ('1', 'true'):
            conf['rpcssl'] = True
        else:
            raise ValueError('Unknown rpcssl value %r' % conf['rpcssl'])

    if conf['rpcport'] == -1:
        if 'testnet' in conf and conf['testnet'] in ['1', 'true']:
            conf['rpcport'] = 9904
        else:
            conf['rpcport'] = 9902

    conf['file_loc'] = btc_conf_file
    return conf

def get_rpc_url():
    conf = get_config()
    if 'rpcpassword' not in conf:
        raise ValueError('The value of rpcpassword not specified in the configuration file.')
    service_url = ('%s://%s:%s@localhost:%d' %
        ('https' if conf['rpcssl'] else 'http',
         conf['rpcuser'], conf['rpcpassword'],
         conf['rpcport']))
    return service_url

def json_custom_parser(obj):
    """
        A custom json parser to handle json.dumps calls properly for Decimal and Datetime data types.
    """
    import datetime
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        dot_ix = 19 # 'YYYY-MM-DDTHH:MM:SS.mmmmmm+HH:MM'.find('.')
        return obj.isoformat()[:dot_ix]
    else:
        raise TypeError(obj)

def pretty_print(obj):
    import json
    print json.dumps(obj, indent=4, default=json_custom_parser)
