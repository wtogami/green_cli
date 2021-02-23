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

This creates a new temporary local transaction. At any time you can
start again by running `tx new` which will discard the scratch tx and
create a new one.

Add outputs to the transaction.
```
$ green-cli --network testnet tx outputs add mkHS9ne12qx9pS9VojpwU5xtRd4T7X7ZUt 1000
```

Show the current outputs
```
$ green-cli --network testnet tx outputs
1000 mkHS9ne12qx9pS9VojpwU5xtRd4T7X7ZUt
```

At any point you can examine the scratch tx using `tx`, e.g.
```
$ green-cli --network testnet tx
user signed: False
server signed: False
output: mkHS9ne12qx9pS9VojpwU5xtRd4T7X7ZUt 1000
total btc: 1000
fee: 210 sat
fee rate: 1000 sat/kb
```

Use `tx inputs` to see the currently selected and available inputs/utxos:
```
$ green-cli --network testnet tx inputs
* 997590 86b29eeed79ad3fe977f49c37fd7cc415887b422892ad943187196fec019e5c4:1 csv 805 confs
- 660000 bbe2c68e8af9e777988823682f4ecc59ab3c94bcaf42c50aba99016f868f0ebd:0 csv unconfirmed
- 30000 c6b84a5ab4fbd6ee963e165aed36bd5a40c7aadede818be79b8445f3992f0031:1 csv unconfirmed
- 100000 0c0863f5ab4e11c6844b25b2883a4056be8f245aa2da09e34b54d8a61b840d26:1 csv unconfirmed
```

Select inputs manually using `tx input add`
```
$ green-cli --network testnet tx inputs add c6b84a5ab4fbd6ee963e165aed36bd5a40c7aadede818be79b8445f3992f0031
$ green-cli --network testnet tx inputs
* 997590 86b29eeed79ad3fe977f49c37fd7cc415887b422892ad943187196fec019e5c4:1 csv 805 confs
* 30000 c6b84a5ab4fbd6ee963e165aed36bd5a40c7aadede818be79b8445f3992f0031:1 csv unconfirmed
- 660000 bbe2c68e8af9e777988823682f4ecc59ab3c94bcaf42c50aba99016f868f0ebd:0 csv unconfirmed
- 100000 0c0863f5ab4e11c6844b25b2883a4056be8f245aa2da09e34b54d8a61b840d26:1 csv unconfirmed
```

tx inputs and outputs can be cleared using `tx inputs clear` and `tx
outputs clear`, or individually removed using `tx inputs rm` and `tx
outputs rm`

## Sending to all
You can add an output which consumes all of the available inputs, less
the fee, by specifying 'all' as the amount. Before doing so, if
necessary either create a new transaction or use `tx outputs clear`.
Once an 'all' output is set the inputs can be manually selected as usual
and the amount paid to the output will automatically adjust usch that
there is no change. E.g.
```
```


When tx transaction is ready, use `tx sign` and `tx send`. The raw
transaction can be inspected first by calling `tx raw`
