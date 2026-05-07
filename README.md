# localsend-daemon

A headless receive daemon for the [LocalSend Protocol v2.1](https://github.com/localsend/protocol).

Run it on a server, NAS, or Raspberry Pi and receive files from any LocalSend-compatible app —
no display, no GUI, no interaction required.

## Why this exists

[LocalSend](https://localsend.org) is a free, open-source, cross-platform file-sharing app
(Android, iOS, Windows, macOS, Linux) built on a
[documented open protocol](https://github.com/localsend/protocol).
It uses TLS-encrypted HTTP over your local network with no cloud relay and no accounts.

The official app is excellent when you have a screen. But many useful machines don't:
home servers, NAS boxes, Raspberry Pis, CI build hosts, or any headless Linux system.
This daemon fills that gap: it speaks the same protocol, so any phone or desktop running
the official app (or any other compatible client) can send files to it directly — discovered
automatically via UDP multicast, just like a normal LocalSend peer.

## Installation

```
pip install .
```

Or with [uv](https://github.com/astral-sh/uv):

```
uv pip install .
```

## Usage

```
localsend-daemon [config-file] [--log-level LEVEL]
```

The default config file is `localsend-daemon.toml` in the current directory.

```
localsend-daemon /etc/localsend-daemon/config.toml --log-level INFO
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default), `CRITICAL`.

## Configuration

Copy `localsend-daemon.example.toml` to `localsend-daemon.toml` and adjust:

```toml
alias       = "My Server"
port        = 53317
receive_dir = "/tmp/localsend"
pin         = "123456"
```

### All settings

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `alias` | yes | — | Display name shown to other devices on the network |
| `port` | no | `53317` | TCP port for HTTP(S) and UDP port for multicast |
| `receive_dir` | yes | — | Directory where received files are saved |
| `pin` | yes | — | PIN that senders must supply to transfer files |
| `protocol` | no | `"https"` | `"https"` (recommended) or `"http"` |
| `trusted_fingerprints_path` | no | unset | Path to a file of trusted peer fingerprints that may skip the PIN (HTTPS only) |
| `trust_on_first_pin` | no | `false` | Automatically trust a peer after its first successful PIN authentication |

### Trusted fingerprints

In HTTPS mode each peer has a stable fingerprint (SHA-256 of its TLS certificate).
You can list fingerprints that are allowed to send files without entering the PIN:

```
trusted_fingerprints_path = "/etc/localsend-daemon/trusted_fingerprints"
```

The file contains one fingerprint per line (colon-separated or plain hex, case-insensitive).
Lines starting with `#` are comments:

```
# Alice's phone
AA:BB:CC:DD:...
# Bob's laptop
aabbccdd...
```

To populate this file automatically, enable `trust_on_first_pin = true`.
The first time a peer authenticates with the correct PIN its fingerprint is appended to the
file and all future transfers from that device skip the PIN prompt.

> `trusted_fingerprints_path` is required when `trust_on_first_pin = true`.
> The feature is silently disabled when `protocol = "http"` (no stable fingerprint available).

## How it works

On startup the daemon:

1. Generates an ephemeral self-signed TLS certificate (HTTPS mode). Its SHA-256 fingerprint
   becomes the device fingerprint advertised on the network.
2. Sends a UDP multicast announcement so nearby LocalSend peers discover it immediately.
3. Listens for announcements from other peers and responds so they discover the daemon too.
4. Accepts incoming file transfers that supply the correct PIN, streaming each file straight
   to `receive_dir`. If a filename already exists a numeric suffix is appended.

The daemon auto-accepts every transfer — there is no interactive confirmation step.
Access control is entirely through the PIN (and optionally the trusted-fingerprints list).

## Protocol support

Implements [LocalSend Protocol v2.1](https://github.com/localsend/protocol):

- Discovery: UDP multicast announce/listen, `POST /api/localsend/v2/register`
- Upload API: `POST /api/localsend/v2/prepare-upload`, `/upload`, `/cancel`
- Info API: `GET /api/localsend/v2/info`

Sending files and the reverse/download API are out of scope.

## Running as a service

Example systemd unit (`/etc/systemd/system/localsend-daemon.service`):

```ini
[Unit]
Description=LocalSend receive daemon
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/localsend-daemon /etc/localsend-daemon/config.toml
Restart=on-failure
DynamicUser=yes
RuntimeDirectory=localsend-daemon

[Install]
WantedBy=multi-user.target
```
