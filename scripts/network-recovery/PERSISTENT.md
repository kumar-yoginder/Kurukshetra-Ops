# Persistent Ethernet-preferred Wi-Fi recovery

The live trial was accepted by the operator. No additional outage simulation is required by these installation scripts. Persistent activation still requires a local, reviewed sudo operation.

From the Kurukshetra-Ops checkout on the Pi, review these files, then run:

```sh
sudo sh scripts/network-recovery/install-persistent.sh
```

The default uses the existing private `/etc/kurukshetra-network-recovery.json` from the trial. To supply another reviewed private JSON file, provide its absolute path as the sole argument. Keep actual addresses and private settings out of Git. No netplan, Wi-Fi credential file, or router configuration is rewritten.

The installer validates configuration and the unit, stops only recognized project transient rollback units, stops an old monitor safely, installs root-owned binaries/configuration, and enables the service for future boots. An unexpected unit or rollback command is refused rather than overwritten. Existing project-owned units can be updated by rerunning the installer; this briefly stops monitoring and restores Wi-Fi first.

The service starts after networkd/network.target, not network-online.target. Its recovery-success threshold supplies startup hysteresis. It restarts on failures after twenty seconds, limited to three starts within five minutes. Its independent stop-post restore also runs after a killed monitor; restoration requests Wi-Fi up and refreshes its local reply policy. This does not claim successful association. Inspect service status and logs for actual results:

```sh
sudo systemctl status kurukshetra-network-recovery.service --no-pager
sudo journalctl -u kurukshetra-network-recovery.service -n 60 --no-pager
sudo /usr/local/sbin/kurukshetra-network-recovery --status
```

Disable boot activation, stop monitoring, and independently restore Wi-Fi:

```sh
sudo sh scripts/network-recovery/disable-persistent.sh
```

Remove the owned persistent service unit as well:

```sh
sudo sh scripts/network-recovery/disable-persistent.sh --uninstall
```

Both commands retain the installed recovery binaries and private configuration. They intentionally retain the exact recovery source rule/table until reboot, since removing the policy during an Ethernet failure could interrupt SSH. They do not delete credentials or change other firewall, routes, or network-manager settings. A restoration error stops uninstallation and should be investigated locally.

Emergency standalone recovery:

```sh
sudo /usr/local/sbin/kurukshetra-network-recovery-rollback
```

Ethernet remains administratively up. Wi-Fi activates on repeated link/router-probe failures, then disconnects after sustained Ethernet recovery. Same-subnet replies from the Wi-Fi address are routed through Wi-Fi; Internet default routing and Ethernet-bound services do not migrate. Hard radio blocks, invalid Wi-Fi credentials, router-wide outages, and upstream Internet failure are outside this feature's recovery guarantees.
