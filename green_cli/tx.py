import json
import logging
import os

import click

import greenaddress as gdk

from . import context
from green_cli.gdk_resolve import gdk_resolve
from .green import green
from green_cli.decorators import (
    confs_str,
    details_json,
    with_login,
)
from green_cli.param_types import (
    Address,
    Amount,
)


@green.group()
def tx():
    """Create transactions"""

def _get_tx_filename(txid):
    tx_path = os.path.join(context.config_dir, 'tx')
    os.makedirs(tx_path, exist_ok=True)
    return os.path.join(tx_path, txid)

def _load_tx(txid='scratch', allow_errors=False):
    with open(_get_tx_filename(txid), 'r') as f:
        raw_tx = f.read()
        tx = json.loads(raw_tx)
        if tx['error'] and not allow_errors:
            raise click.ClickException(tx['error'])
    return tx

def _save_tx(tx, txid='scratch'):
    with open(_get_tx_filename(txid), 'w') as f:
        f.write(json.dumps(tx))
    return tx

def _create_tx(tx):
    return gdk_resolve(gdk.create_transaction(context.session.session_obj, json.dumps(tx)))

class Tx:

    def __init__(self, allow_errors=False, recreate=True):
        self.allow_errors = allow_errors
        self.recreate = recreate

    def __enter__(self):
        self._tx = _load_tx(allow_errors=self.allow_errors)
        return self._tx

    def __exit__(self, type, value, traceback):
        if self.recreate:
            self._tx = _create_tx(self._tx)
        self._tx = _save_tx(self._tx)
        if self._tx.get('error', ''):
            click.echo(f"ERROR: {self._tx['error']}")
        elif 'txhash' in self._tx:
            click.echo(f"{self._tx['txhash']}")
        return False

@tx.command()
@click.option('--subaccount', default=0, expose_value=False, callback=details_json)
@with_login
def new(session, details):
    """Create a new transaction"""
    return _save_tx(_create_tx(details))

@tx.command()
@click.argument('address', type=Address(), expose_value=False)
@click.argument('amount', type=Amount(), expose_value=False)
@with_login
def addoutput(session, details):
    """Add a transaction output"""
    with Tx(allow_errors=True) as tx:
        tx.setdefault('addressees', [])
        tx['addressees'].extend(details['addressees'])

@tx.command()
def raw():
    """Get the raw transaction hex"""
    click.echo(_load_tx(allow_errors=False)['transaction'])

@tx.command()
def dump():
    """Dump the full transaction json representation"""
    click.echo(json.dumps(_load_tx(allow_errors=True)))

@tx.command()
@click.argument('tx_json', type=click.File('r'))
@with_login
def load(session, tx_json):
    """Load a transaction from json, see also dump"""
    raw_tx = tx_json.read()
    tx = json.loads(raw_tx)
    _save_tx(_create_tx(tx))

@tx.command()
def info():
    """Show summary information about the current tx"""
    tx = _load_tx(allow_errors=True)
    if tx['error']:
        click.echo(f"ERROR: {tx['error']}")

    if 'txhash' in tx:
        click.echo(f"txhash: {tx['txhash']}")
    click.echo(f"user signed: {tx['user_signed']}")
    click.echo(f"server signed: {tx['server_signed']}")
    for addressee in tx['addressees']:
        click.echo(f"output: {addressee['address']} {addressee['satoshi']}")
    for asset, amount in tx['satoshi'].items():
        click.echo(f"total {asset}: {amount}")
    click.echo(f"fee: {tx['fee']} sat")
    click.echo(f"fee rate: {tx['calculated_fee_rate']} sat/kb")

@tx.group(name='coin')
def tx_coin():
    """Coin selection"""
    pass

@tx_coin.command()
@with_login
def status(session):
    """Show status of coins for current tx"""
    tx = _load_tx(allow_errors=True)

    selected = 0
    click.echo("selected:")
    for utxo in tx['used_utxos']:
        confs = confs_str(utxo['block_height'])
        click.echo(f"\t{utxo['satoshi']} {utxo['address_type']} {confs} {utxo['txhash']}:{utxo['pt_idx']}")
        selected += utxo['satoshi']
    click.echo(f"\ttotal: {selected}")

    available = 0
    click.echo("available:")
    for asset, utxos in tx['utxos'].items():
        for utxo in utxos:
            confs = confs_str(utxo['block_height'])
            click.echo(f"\t{utxo['satoshi']} {utxo['address_type']} {confs} {utxo['txhash']}:{utxo['pt_idx']}")
            available += utxo['satoshi']
        click.echo(f"\ttotal: {available}")

def _filter_utxos(utxo_filter, utxos):
    txhash, _, vout = utxo_filter.partition(':')
    selected = []
    for utxo in utxos:
        if txhash == '*' or txhash == utxo['txhash']:
            if not vout or vout == '*' or int(vout) == utxo['pt_idx']:
                selected.append(utxo)
    return selected

@tx_coin.command()
@with_login
def auto(session):
    """Enable automatic coin selection"""
    with Tx(allow_errors=True) as tx:
        tx['utxo_strategy'] = 'default'

@tx_coin.command()
@click.argument('utxo')
@with_login
def select(session, utxo):
    """Select coins/utxos"""
    with Tx(allow_errors=True) as tx:
        tx['utxo_strategy'] = 'manual'
        for utxo in _filter_utxos(utxo, tx['utxos']['btc']):
            # Use 'existing_filter' to avoid duplicating inputs
            existing_filter = f'{utxo["txhash"]}:{utxo["pt_idx"]}'
            existing =  _filter_utxos(existing_filter, tx['used_utxos'])
            if not _filter_utxos(existing_filter, tx['used_utxos']):
                tx['used_utxos'].append(utxo)

@tx_coin.command()
@click.argument('utxo')
@with_login
def deselect(session, utxo):
    """Deselect coins/utxos"""
    with Tx(allow_errors=True) as tx:
        tx['utxo_strategy'] = 'manual'
        selected = _filter_utxos(utxo, tx['used_utxos'])
        for utxo in selected:
            tx['used_utxos'].remove(utxo)

@tx.command()
@with_login
def sign(session):
    """Sign the current transaction"""
    with Tx(allow_errors=False, recreate=False) as tx:
        signed = gdk_resolve(gdk.sign_transaction(session.session_obj, json.dumps(tx)))
        tx.clear()
        tx.update(signed)

@tx.command()
@with_login
def send(session):
    """Send/broadcast the current transaction"""
    with Tx(allow_errors=False, recreate=False) as tx:
        sent = gdk_resolve(gdk.send_transaction(session.session_obj, json.dumps(tx)))
        tx.clear()
        tx.update(sent)
