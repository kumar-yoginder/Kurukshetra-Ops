# Host hardening utilities

## Scope and layout

These are existing, site-specific Ubuntu/systemd utilities imported from the host home directory. Organization does not apply any hardening. Review before execution; these scripts can interrupt SSH and networking. They are host administration tools, not Docker entrypoints.

- `scripts/host-hardening/`: executable audit, SSH, LAN firewall and static-network utilities; shared local-settings loader.
- `config/host-hardening/local.env.example`: example site settings.
- `config/host-hardening/lan-hardening.nft.example`: example firewall policy, with documentation-only addresses.
- `config/host-hardening/local.env` and `lan-hardening.nft`: actual site settings; ignored by Git.
- `backups/host-hardening/`: private historical audit report; ignored by Git.
- Original home-directory filenames are compatibility symlinks to the canonical project copies.

## Prepare local configuration

Copy the example files to their suffix-free local paths only on a new installation. Existing local files on this Pi are already populated; do not overwrite them.

```bash
cp config/host-hardening/local.env.example config/host-hardening/local.env
cp config/host-hardening/lan-hardening.nft.example config/host-hardening/lan-hardening.nft
chmod 600 config/host-hardening/local.env config/host-hardening/lan-hardening.nft
```

Replace all example addresses, username and MAC with verified site values. Keep local.env and firewall subnet/prefix values consistent. The shell sources local.env during privileged execution: review its contents and ownership before running; it must not contain commands or untrusted input. Review the scripts themselves as privileged code.

Prerequisites: Bash, Python 3, iproute2, OpenSSH server, nftables, systemd; the static-network utility additionally requires netplan, Python PyYAML, systemd-networkd, dig and ping. The audit also probes sudo, UFW, iptables, AppArmor and automatic-update services; missing optional tools produce incomplete sections. Its exit status is not a security compliance verdict.

## Audit first

From the project root:

```bash
mkdir -p backups/host-hardening
chmod 700 backups/host-hardening
(umask 077; sudo bash scripts/host-hardening/audit-hardening.sh > backups/host-hardening/audit-current.txt 2>&1)
```

The audit is read-only but contains private account policy, listener and firewall information. Do not commit or share the raw report without review.

## Choose one SSH workflow

`harden-ssh.sh` stages key-only SSH. `apply-lan-hardening.sh` stages key-only SSH plus the dedicated LAN firewall. They target the same SSH drop-in: do not run both sequentially. Existing target files/tables intentionally cause a stop for review.

Keep a working recovery terminal open and have console access. Confirm keys work independently before running either workflow.

```bash
sudo bash scripts/host-hardening/harden-ssh.sh
# OR, after reviewing the private rules and site preconditions:
sudo bash scripts/host-hardening/apply-lan-hardening.sh
```

Both arrange a ten-minute rollback. In another terminal verify new SSH key logins, IPv4/IPv6 reachability, Pi-hole DNS and HTTPS. Follow the exact commit/rollback commands printed by that invocation. These refer to restricted backup directories under /root. Do not reboot during the trial: transient rollback timers do not survive reboot. If verification fails, roll back or let the timer expire; do not commit the trial.

The LAN policy uses only its own nftables table and does not flush Docker rules. LAN forwarding is broadly permitted in the imported policy; this is not an isolated Tor-client policy. A future gateway requires a separate reviewed policy and explicit permitted tunnel port. Review ISP prefix changes before reusing these rules.

## Static Ethernet utility — optional, not routine deployment

`configure-eth0-static.sh` expects a particular pre-existing netplan shape, Ethernet MAC, systemd-networkd and a working Wi-Fi recovery address. It refuses unexpected existing configuration. A router DHCP reservation may already meet your address-stability need; do not run this automatically or on other hosts without review.

```bash
sudo bash scripts/host-hardening/configure-eth0-static.sh
```

It backs up netplan and sets a three-minute rollback timer. On successful built-in address, route, gateway and DNS checks it cancels that timer automatically. This is not the same manual commit workflow as SSH hardening. Verify a fresh SSH session immediately; use the printed manual rollback path if needed.

## Verification and recovery

Syntax-check scripts without applying them using `bash -n scripts/host-hardening/*.sh` (check each file individually in a shell loop). Privileged `nft -c -f config/host-hardening/lan-hardening.nft` checks rules without installing them, and `sshd -t` checks SSH configuration. Syntax checks alone do not prove connectivity safety.

Retain root-owned backup directories and generated rollback scripts. Recovery must target only resources created by that trial; never flush the entire firewall to undo these changes. If a policy is already installed, inspect its systemd unit and installed files before attempting an update. Editing repository files does not update active host rules or SSH configuration.

## Import record and outstanding review

Four scripts, the firewall policy and one private audit report were organized. Changes: configuration-path discovery for symlink compatibility, local-settings extraction, example files and operator-oriented messages. No hardening script was executed. Review the actual installed host policy separately before any reapplication. Privileged nftables/SSH validation and a live rollback exercise remain outstanding.

Review follow-up: corrected static-route variable expansion, made address-pattern checks literal, and corrected the printed IPv6 trial summary. Shell syntax and non-mutating local-setting validation pass. No scripts have been applied; sudo is required for remaining host validation.
