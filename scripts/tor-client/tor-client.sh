#!/usr/bin/env bash
# Ubuntu 24.04 manual-session client. Never embeds credentials or peer keys.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
config=/etc/kurukshetra-tor
state=/run/kurukshetra-tor-session
source_dir=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
load_state() {
 [[ -f $state && $(stat -c %u "$state") == 0 ]] || { echo 'No managed session state found.' >&2; exit 1; }
 mapfile -t session < "$state"
 backup=${session[0]:-}; unit=${session[1]:-}
 [[ $backup =~ ^/root/tor-client-trial\.[a-zA-Z0-9]+$ && $unit =~ ^tor-client-trial-[0-9]+$ ]]
}
case "${1:-}" in
 setup)
  [[ $# == 2 ]] || { echo 'Usage: tor-client.sh setup TRUSTED_CONFIG_DIRECTORY'; exit 2; }
  source /etc/os-release
  [[ $ID == ubuntu && $VERSION_ID == 24.04 ]] || { echo 'Validated only for Ubuntu 24.04'; exit 1; }
  for tool in wg nft ip resolvectl systemd-run flock; do command -v "$tool" >/dev/null || { echo "Install prerequisite: $tool"; exit 1; }; done
  [[ -s $2/wg.conf && -s $2/local.env && -s $source_dir/trial.sh ]]
  [[ ! -e $config ]] || { echo 'Existing installed configuration: review rather than overwrite.'; exit 1; }
  install -d -o root -g root -m 700 "$config" /usr/local/lib/kurukshetra-tor
  install -o root -g root -m 600 "$2/wg.conf" "$config/wg.conf"
  install -o root -g root -m 600 "$2/local.env" "$config/local.env"
  install -o root -g root -m 700 "$source_dir/trial.sh" /usr/local/lib/kurukshetra-tor/trial.sh
  install -o root -g root -m 755 "${BASH_SOURCE[0]}" /usr/local/sbin/kurukshetra-tor
  echo 'Installed root-owned client files. No routing changed. Run: sudo kurukshetra-tor connect'
  ;;
 connect)
  [[ $# == 1 && -s $config/wg.conf && -s $config/local.env ]]
  exec bash /usr/local/lib/kurukshetra-tor/trial.sh "$config"
  ;;
 status)
  if ip link show torwg0 >/dev/null 2>&1 && nft list table inet tor_client >/dev/null 2>&1; then
   echo 'Tunnel interface and egress guard present; this alone does not prove Tor reachability.'
   wg show torwg0 latest-handshakes
   if [[ -f $state ]]; then load_state; systemctl is-active "$unit.timer" || true; fi
  else
   echo 'No complete managed Tor session is active.'
  fi
  ;;
 confirm)
  exec 9>/run/kurukshetra-tor.lock
  flock -x 9
  load_state
  ip link show torwg0 >/dev/null
  nft list table inet tor_client >/dev/null
  systemctl is-active --quiet "$unit.timer"
  printf '%s\n%s\nconfirmed\n' "$backup" "$unit" > "$state"
  systemctl stop "$unit.timer"
  echo 'Trial confirmed for this running session only. Not enabled at boot. Disconnect explicitly to restore ordinary Internet.'
  ;;
 disconnect)
  load_state
  bash "$backup/rollback.sh"
  ;;
 *)
  echo 'Usage: sudo kurukshetra-tor {connect|status|confirm|disconnect}'
  echo 'First-time setup: sudo bash tor-client.sh setup TRUSTED_CONFIG_DIRECTORY'
  exit 2
  ;;
esac
