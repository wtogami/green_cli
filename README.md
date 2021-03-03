# GreenAddress command line interface

## Installation

It's recommended that you first create and activate a (python3)
virtualenv and use that to install the green-cli.

Note that the package installs two scripts: green-cli for use with the
bitcoin network an green-liquid-cli for the liquid network.

# Basic install

1) Install requirements
```
$ pip install -r requirements.txt
```

2) Install green_cli
```
$ pip install .
```

3) [Optional] Enable bash completion
for green-cli:
```
$ eval "$(_GREEN_CLI_COMPLETE=source green-cli)"
```

for green-liquid-cli:
```
$ eval "$(_GREEN_LIQUID_CLI_COMPLETE=source green-liquid-cli)"
```

# Hardware wallet support (via hwi) [BETA]

To enable hardware wallet support (via the `--auth hardware` option)
additional dependencies must be installed from requirements-hwi.txt.

1) Install libudev and libusb. This is platform specific but for
debian-based systems:
```
$ sudo apt-get install libudev-dev libusb-1.0-0-dev
```

2) Install extra requirements
```
$ pip install -r requirements-hwi.txt
```

You can now run green-cli (or green-liquid-cli) passing the `--auth
hardware` option.

# Software authenticator support (via libwally) [BETA]

There is another authenticator option `--auth wally` which delegates the
possession of key material (the mnemonic) and authentication services to
python code external to the gdk using the hardware wallet interface.
This is useful for testing and as a demonstration of the technique. In
order to enable this option libwally must be installed:

```
$ pip install -r requirements-wally.txt
```

# Example usage

Log in to a testnet wallet and report the balance:
```
$ green-cli --network testnet set mnemonic -f /file/containing/testnet/mnemonics
$ green-cli --network testnet getbalance
```

Log in to a mainnet wallet and send 0.1 BTC to an address
```
$ green-cli --network mainnet set mnemonic "mainnet mnemonic here ..."
$ green-cli --network mainnet sendtoaddress $ADDR 0.1
```

Log in to a liquid wallet and send an asset to an address
```
$ green-liquid-cli --network liquid set mnemonic "liquid mnemonic here ..."
$ green-liquid-cli --network liquid sendtoaddress
```

For now wallet creation is disabled on use on mainnet/liquid mainnet

# Manual coin selection (alpha - use at your own risk)

WARNING: Please note that green-cli in general and the tx/coin selection
functions in particular are alpha software and not currently recommended
for mainnet use. Loss of funds may occur.

First, create a new 'scratch' transaction using the `tx` command
```
$ green-cli --network testnet tx new
```

Add outputs to the transaction. At any time you can start again by
running `tx new` again which will discard the scratch tx and create a
new one.
```
$ green-cli --network testnet tx addoutput mkHS9ne12qx9pS9VojpwU5xtRd4T7X7ZUt 1000
```

At any point you can examine the scratch tx using `tx info`, e.g.
```
$ green-cli --network testnet tx info
user signed: False
server signed: False
output: mkHS9ne12qx9pS9VojpwU5xtRd4T7X7ZUt 1000
total btc: 1000
fee: 210 sat
fee rate: 1000 sat/kb
```

Use `tx coin status` to see the currently selected and available
coins/utxos:

```
$ green-cli --network testnet tx coin status
selected:
	1970 csv 2431 confs f4c8b1923428f335727deef33d1d96fcd6131d4acef1e64f234d0c40fec2ba0e:1
	total: 1970
available:
	1970 csv 2431 confs f4c8b1923428f335727deef33d1d96fcd6131d4acef1e64f234d0c40fec2ba0e:1
	994760 csv 2430 confs 2d2ad400ccdc7413e7f0df1d1d547666a7cff870682a3daf376597fd95576405:0
	1234 csv 2422 confs 5a81ef1596441bdcb7e2dea7a50577c209811f1a6bb52bfc6ccec472b27c4405:1
	1234 csv 2421 confs 9b9792dc90a9ab20cc8fa0d47ce9cce6be2e00034d6ce17d715bcd41dc130c5d:0
	total: 999198
```

Coins can be added using `tx coin select`

```
$ green-cli --network testnet tx coin select 5a81ef1596441bdcb7e2dea7a50577c209811f1a6bb52bfc6ccec472b27c4405:1
$ green-cli --network testnet tx coin status
selected:
	1970 csv 2431 confs f4c8b1923428f335727deef33d1d96fcd6131d4acef1e64f234d0c40fec2ba0e:1
	1234 csv 2422 confs 5a81ef1596441bdcb7e2dea7a50577c209811f1a6bb52bfc6ccec472b27c4405:1
	total: 3204
available:
	1970 csv 2431 confs f4c8b1923428f335727deef33d1d96fcd6131d4acef1e64f234d0c40fec2ba0e:1
	994760 csv 2430 confs 2d2ad400ccdc7413e7f0df1d1d547666a7cff870682a3daf376597fd95576405:0
	1234 csv 2422 confs 5a81ef1596441bdcb7e2dea7a50577c209811f1a6bb52bfc6ccec472b27c4405:1
	1234 csv 2421 confs 9b9792dc90a9ab20cc8fa0d47ce9cce6be2e00034d6ce17d715bcd41dc130c5d:0
	total: 999198
```

Coins can be deselected using `tx coin deselect`. Both `tx coin select`
and `tx coin deselect` accept wildcards, for example to select all
available coins:

```
$ green-cli --network testnet tx coin select *:*
```

When tx transaction is ready, use `tx sign` and `tx send`. The raw
transaction can be inspected first by calling `tx raw`
