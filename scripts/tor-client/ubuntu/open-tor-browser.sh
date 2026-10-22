#!/usr/bin/env bash
# Ubuntu desktop helper. Never runs a browser as root or edits the default profile.
set -euo pipefail
[[ $EUID != 0 ]] || { echo 'Launch the browser as your desktop user, not root.' >&2; exit 1; }
url=${1:-http://pzhdfe7jraknpj2qgu5cz2u3i4deuyfwmonvzu5i3nyw4t4bmg7o5pad.onion/}
[[ $url == http://* || $url == https://* ]] || { echo 'Only HTTP and HTTPS URLs are supported.' >&2; exit 1; }
ip link show torwg0 >/dev/null 2>&1 || { echo 'Connect the managed Tor tunnel first.' >&2; exit 1; }
[[ -n ${DISPLAY:-}${WAYLAND_DISPLAY:-} ]] || { echo 'No graphical desktop; browser launch skipped.'; exit 0; }
browser=''
for candidate in google-chrome google-chrome-stable chromium chromium-browser microsoft-edge; do
    if command -v "$candidate" >/dev/null 2>&1; then browser=$candidate; break; fi
done
[[ -n $browser ]] || { echo 'No supported installed Chromium browser found; no browser installed or changed.'; exit 0; }
profile=${XDG_CONFIG_HOME:-$HOME/.config}/kurukshetra-tor-browser
mkdir -p "$profile"
chmod 700 "$profile"
"$browser" "--user-data-dir=$profile" '--proxy-server=socks5://10.77.0.1:9050' \
    '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 10.77.0.1' '--disable-quic' "$url" \
    >/dev/null 2>&1 < /dev/null &
echo 'Launched an installed browser in a separate Tor profile. Tor Browser fingerprint protections are not included.'
