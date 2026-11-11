# Home Internet and Tor speed samples

Open **Internet speed** in the authenticated portal. Separate cards show download Mbps, upload Mbps, HTTPS response time, measurement timestamp, and complete/partial/stale/unavailable status. Tests run on the Pi, not the viewing device. All results require the central login; no new web port or command-trigger endpoint is exposed.

## Measurement paths and limits

- Home Internet: the Pi’s normal uplink to Cloudflare. Three small HTTPS requests provide median end-to-end response time, followed by one 4 MiB download and one 1 MiB random-data upload.
- Tor: a SOCKS5 connection inside the gateway container. The probe first verifies its path with the Tor Project API; then measures Cloudflare response time, a 256 KiB download and a 64 KiB upload. It never falls back to direct HTTP. A failed Tor verification publishes no speed values.
- These are bounded single-request throughput estimates including setup/response overhead, not multi-stream maximum ISP line-speed tests. HTTPS response time includes DNS/TCP/TLS/application overhead where applicable and is not ICMP ping. The small Tor upload/download samples can underestimate throughput substantially.
- Targets are fixed to Cloudflare measurement endpoints and Tor’s verification API; visitors cannot submit hosts, commands, sample sizes or arbitrary URLs. TLS verification is enabled. Tor execution has a 120-second subprocess timeout; direct reads have socket timeouts, byte caps and a 45-second per-request deadline.
- Up to approximately 5 MiB of home traffic and 320 KiB of Tor traffic per scheduled sample, plus protocol overhead and small verification responses. No personal files are uploaded; upload bodies are generated random bytes.

## Schedule and refresh

The existing 15-minute `collect-tor-metrics.py` job now collects both paths under a nonblocking lock. No additional cron schedule was installed. The portal refreshes saved results every 30 seconds while visible; **Refresh data** fetches results but does not launch another bandwidth test. Data older than 20 minutes is displayed as stale with no current speeds. A failed step remains unavailable rather than becoming zero Mbps; completed measurements survive a later step failing.

The existing private monitoring Python environment supplies pinned Pydantic dependencies. The entry point hands off to that environment when invoked with system Python. Missing dependencies stop collection rather than installing packages automatically. Persisted results use two-space JSON indentation and a trailing newline, validated models, temporary files and atomic replacement. Generated result files remain Git-ignored.

## Source and operations

- `scripts/monitoring/network_speed.py`: Pydantic contracts and bounded direct probe.
- `scripts/monitoring/tor-probe.py`: Tor-only measurements inside its network namespace.
- `scripts/monitoring/collect-tor-metrics.py`: scheduler entry, locking, validation and atomic publication.
- `config/portal/www/`: shared speed view and presentation; no duplicate UI files.
- `config/nginx/www/speed-metrics.json`: ignored generated combined result.
- `/speed-metrics.json`: authenticated gateway route.

```bash
# Read-only code checks; no network measurements
.venv-router/bin/python scripts/monitoring/test-network-speed.py
python3 tests/gateway/verify-edge.py

# Run one bounded sample now on the Pi; normally the existing cron handles this
python3 scripts/monitoring/collect-tor-metrics.py
```

Five mocked tests cover truncated downloads, upload failure, connection failure, nonfinite values, and rejecting unverified Tor speed values. Both live paths completed during deployment. Inventory continues through its internal JSON-only endpoint; its separate HTML/CSS/JavaScript page and build context have been removed.

Measurement API reference: https://github.com/cloudflare/speedtest
