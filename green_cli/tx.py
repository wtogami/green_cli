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

@green.group(invoke_without_command=True)
@click.pass_context
def tx(ctx):
    """Create transactions"""
    if ctx.invoked_subcommand:
        return

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
    """Load a transaction from json.

    Combined with dump and appropriate json manipulation tools facilitates arbitrary manipulation of
    the json representation of the current transaction. Advanced feature - use with caution.
    """
    raw_tx = tx_json.read()
    tx = json.loads(raw_tx)
    _save_tx(_create_tx(tx))

class Tx:
    """Provides context manager for loading a tx, modifying it and then saving it again"""

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
@click.argument('feerate', type=int)
@with_login
def setfeerate(session, feerate):
    """Set the fee rate (satoshi/kB)."""
    with Tx(allow_errors=True) as tx:
        tx['fee_rate'] = feerate

@tx.group(invoke_without_command=True)
@with_login
@click.pass_context
def outputs(ctx, session):
    """Show and modify transaction outputs.

    With no subcommand shows a summary of the current transaction outputs"""
    if ctx.invoked_subcommand:
        return

    tx = _load_tx(allow_errors=True)
    if tx.get('send_all', False):
        assert len(tx['addressees']) == 1
        click.echo(f"all {tx['addressees'][0]['address']}")
    else:
        for addressee in tx['addressees']:
            click.echo(f"{addressee['satoshi']} {addressee['address']}")

@outputs.command()
@click.argument('address', type=Address(), expose_value=False)
@click.argument('amount', type=Amount(), expose_value=False)
@with_login
def add(session, details):
    """Add a transaction output"""
    with Tx(allow_errors=True) as tx:
        tx.setdefault('addressees', [])
        send_all = details.get('send_all', False)
        if send_all:
            if tx['addressees']:
                raise click.ClickException(
                    "Cannot add send-all output with other outputs present. "
                    "First remove other outputs with `tx outputs clear`.")
            tx['send_all'] = True
        tx['addressees'].extend(details['addressees'])

@outputs.command()
@click.argument('address', type=str)
@with_login
def rm(session, address):
    """Remove a transaction output"""
    with Tx(allow_errors=True) as tx:
        addressees = tx.get('addressees', [])
        addressees = [a for a in addressees if a['address'] != address]
        tx['addressees'] = addressees

@outputs.command()
@with_login
def clear(session):
    """Remove all transaction outputs"""
    with Tx(allow_errors=True) as tx:
        tx['addressees'] = []

def _filter_utxos(txid, vout, utxos):
    selected = []
    for utxo in utxos:
        if txid == '*' or txid == utxo['txhash']:
            if not vout or vout == '*' or int(vout) == utxo['pt_idx']:
                selected.append(utxo)
    return selected

@tx.group(invoke_without_command=True)
@with_login
@click.pass_context
def inputs(ctx, session):
    """Show and modify transaction inputs.

    With no subcommand shows a summary of the current transaction inputs"""
    if ctx.invoked_subcommand:
        return

    tx = _load_tx(allow_errors=True)

    def format_utxo(utxo):
        confs = confs_str(utxo['block_height'])
        return f"{utxo['satoshi']} {utxo['txhash']}:{utxo['pt_idx']} {utxo['address_type']} "\
               f"{confs}"

    for utxo in tx['used_utxos']:
        click.echo(f"* {format_utxo(utxo)}")

    for asset, utxos in tx['utxos'].items():
        for utxo in utxos:
            if not _filter_utxos(utxo['txhash'], utxo['pt_idx'], tx['used_utxos']):
                click.echo(f"- {format_utxo(utxo)}")

@inputs.command()
@with_login
def auto(session):
    """Enable automatic coin selection"""
    with Tx(allow_errors=True) as tx:
        tx['utxo_strategy'] = 'default'

@inputs.command()
@click.argument('txid', default="*", required=False)
@click.argument('vout', default="*", required=False)
@with_login
def add(session, txid, vout):
    """Add transaction input."""
    with Tx(allow_errors=True) as tx:
        tx['utxo_strategy'] = 'manual'
        for utxo in _filter_utxos(txid, vout, tx['utxos']['btc']):
            # Don't append inputs that are already in `used_utxos`
            if not _filter_utxos(utxo["txhash"], utxo["pt_idx"], tx['used_utxos']):
                tx['used_utxos'].append(utxo)

@inputs.command()
@click.argument('txid')
@click.argument('vout', required=False)
@with_login
def rm(session, txid, vout="*"):
    """Remove transaction inputs.
    """
    with Tx(allow_errors=True) as tx:
        tx['utxo_strategy'] = 'manual'
        selected = _filter_utxos(txid, vout, tx['used_utxos'])
        for utxo in selected:
            tx['used_utxos'].remove(utxo)

@inputs.command()
@with_login
def clear(session):
    """Remove transaction inputs.
    """
    with Tx(allow_errors=True) as tx:
        tx['utxo_strategy'] = 'manual'
        tx['used_utxos'] = []

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
