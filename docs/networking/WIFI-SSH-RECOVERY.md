# Emergency Wi-Fi SSH recovery

## Purpose and current state

Ethernet is the permanent Pi connection. Wi-Fi is an emergency local maintenance path with its own address; it is not transparent failover for Pi-hole, HTTPS or Tor services bound to the Ethernet address. The monitor is prepared for a reversible trial, not installed or enabled persistently.

The monitor uses systemd-networkd's existing Wi-Fi configuration and saved credentials. It never reads, copies or versions the Wi-Fi password. It does not restart the network manager or disable Ethernet.

## Behavior

- With Ethernet link and local-router reachability healthy for the configured recovery period, disconnect Wi-Fi administratively.
- With carrier absent or repeated Ethernet-bound router probes failing, bring Wi-Fi up.
- Add a dedicated source-routing policy for Wi-Fi replies to the local subnet, so an unhealthy but lower-metric Ethernet path does not trap recovery SSH replies.
- Preserve normal default Internet routes; this is local SSH recovery only. Both links using one failed router cannot create connectivity.
- A single failed probe must not switch interfaces. Probe counts, interval and recovery delay are configurable.
- Stopping the monitor attempts to bring Wi-Fi back up. Its maintenance reply policy remains until reboot rather than immediately removing the emergency path. Review its routing-table/rule ownership before manual cleanup.

Administrative disconnect is not a guarantee that the radio is physically powered off. Association and DHCP after fallback take time. Local access is enough; Internet access is not required. Reserve the Wi-Fi address separately in the router if you want a predictable SSH target. Do not reuse the Ethernet reservation or assume both interfaces share an IP.

## Files

- `scripts/network-recovery/ethernet_wifi_recovery.py`: read-only status by default; root-only monitor mode.
- `scripts/network-recovery/install-trial.sh`: reviewed root installation and independent trial timer; no persistent boot service.
- `scripts/network-recovery/rollback.sh`: independent recovery even after a monitor crash.
- `scripts/network-recovery/test_decisions.py`: mocked tests; no live networking required.
- `config/network-recovery/recovery.json.example`: Git-safe example.
- `config/network-recovery/recovery.json`: ignored site configuration already prepared for this Pi.

## Inspect before any changes

From the project directory:

```bash
python3 scripts/network-recovery/ethernet_wifi_recovery.py --config config/network-recovery/recovery.json --status
python3 scripts/network-recovery/test_decisions.py
```

Review the script, installer and private settings locally before running them as root. Example documentation addresses must be replaced on a new machine. Do not place router/Wi-Fi credentials in the JSON.

## Controlled trial

Keep Fusion/Ubuntu testing separate. Have local console access and physical access to the Ethernet cable. Keep an Ethernet SSH terminal open and know the separately reserved Wi-Fi SSH address before beginning.

```bash
sudo sh scripts/network-recovery/install-trial.sh "$PWD/config/network-recovery/recovery.json"
sudo journalctl -u kurukshetra-network-recovery.service -f
```

The installer starts a three-minute transient trial. Its separate rollback timer stops the monitor; shutdown restores Wi-Fi. It does not enable the feature at boot. Do not reboot during the trial: the rollback timer is transient. A script crash, reboot or missing credentials can still require console recovery; the timer is a safeguard, not a guarantee.

Early rollback:

```bash
sudo /usr/local/sbin/kurukshetra-network-recovery-rollback
```

## Acceptance checks before persistent installation

1. Ethernet healthy: after the recovery delay, Wi-Fi disconnects; Ethernet SSH/DNS/HTTPS and Tor gateway health remain normal.
2. Unplug Ethernet: Wi-Fi reconnects after the failure threshold; open a fresh SSH connection to its own address.
3. Verify SSH replies use Wi-Fi for that address even if Ethernet retains carrier but cannot reach the router. The source-policy table must include the Wi-Fi subnet route.
4. Reconnect Ethernet: confirm fresh Ethernet SSH before Wi-Fi disconnects after the recovery delay.
5. Stop the service and verify Wi-Fi is restored; inspect trial timer behavior.
6. Test Wi-Fi unavailable and router unavailable without rapid cycling. No broad route or firewall flush is an acceptable recovery method.

These describe the full validation scope. The operator accepted the observed trial and declined additional outage testing; remaining cases are documented limitations. Record evidence and issues in the recovery plan. Existing diagnostic-only sudo does not authorize running this network-changing service; the installation command is entered locally by the user.

## Repeating a completed trial

Do not replace an active trial or rollback timer. After explicitly restoring Wi-Fi, stop the named transient units before rerunning the installer:

```bash
sudo /usr/local/sbin/kurukshetra-network-recovery-rollback
sudo systemctl stop kurukshetra-network-recovery-rollback.timer kurukshetra-network-recovery-rollback.service kurukshetra-network-recovery.service
sudo systemctl reset-failed kurukshetra-network-recovery-rollback.service kurukshetra-network-recovery.service
```

A message that an already-absent unit is not loaded can occur. Inspect unit state rather than changing unrelated services. Eight mocked tests and syntax validation passed; these do not replace physical cable and fresh Wi-Fi SSH tests.

## Updated test timing

User requested shorter tests: new monitor trials use a three-minute rollback.
A separate sixty-second Ethernet-restore timer must be armed before any
administrative Ethernet-down simulation. It is not armed by the trial installer.
Previously started timers keep their original deadline until explicitly replaced.

## Optional administrative Ethernet-down simulation

After the monitor has disconnected Wi-Fi and Ethernet SSH is healthy, run
`sudo sh scripts/network-recovery/simulate-ethernet-loss.sh`. The helper refuses
if Wi-Fi is still up or the monitor is inactive. It first arms independent
Ethernet restoration after 60 seconds and monitor rollback after three minutes,
then disables Ethernet. SSH is expected to drop. Both timers use one-second
accuracy; the configured delay is measured from timer arming, not from cable/link
loss. This does not replace a physical cable and router-failure test.

Attempt a fresh SSH connection to the Wi-Fi maintenance address during the
60-second window. If it cannot connect, wait for Ethernet restoration rather
than disabling anything else. Do not run overlapping simulations.

## Accepted trial scope

User accepted the observed trial and declined further disruption tests. Record the untested physical/ICMP cases as limitations; do not repeat them as an activation prerequisite without a new user request. The transient trial is now stopped. Persistent installer preparation follows this accepted checkpoint, with no live boot activation yet.

## Persistent activation after accepted trial

The installer is prepared and reviewed; the operator completed local sudo installation and the service is enabled and active. No further outage simulation is required.

```sh
sudo sh scripts/network-recovery/install-persistent.sh
```

It uses the private configuration already installed during the trial, validates ownership and configuration, removes recognized trial rollback timers, and enables the recovery service at boot. It does not disable Ethernet. Fourteen mocked recovery and installation-guard tests passed; live reboot behavior has not been tested.

To disable monitoring and boot activation while restoring Wi-Fi:

```sh
sudo sh scripts/network-recovery/disable-persistent.sh
```

See [persistent installation details](../../scripts/network-recovery/PERSISTENT.md) for status, logs, uninstall, and recovery commands.

## Persistent activation checkpoint

Operator installed the persistent service. Read-only checks confirmed enabled, active/running, zero restarts, Ethernet up, and Pi-hole/Tor containers healthy. No further outage simulation or reboot was performed. Wi-Fi may remain up during the initial Ethernet stability delay.
