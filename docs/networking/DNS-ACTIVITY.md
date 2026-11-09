# Public DNS activity view

The service dashboard includes a rolling 24-hour summary from the persisted Pi-hole query database. This is DNS usage, not router association history or a physical-device inventory. Device type remains unknown.

The existing minute status cron invokes scripts/monitoring/collect-dns-activity.py. It opens the database read-only with a 25-second query timeout and atomically publishes dns-activity.json. Collection errors publish an unavailable state. The browser fetches every 30 seconds while visible and clears values if unavailable or older than three minutes. Persisted records can lag live Pi-hole counters.

The summary export allowlist contains anonymous rank labels, counts, minutes since last query, and 24 hourly totals. No client addresses, hostnames, MAC addresses or queried domains are exported. Labels are snapshot ranks, not stable identifiers. Filtering includes private IPv4 192.168/16 and 10/8; loopback, Docker 172/12, public addresses and IPv6 are excluded in this initial lab-specific implementation. Hosts in those excluded ranges will not be counted. Multiple IPs do not necessarily mean multiple devices.

Run verification with `python3 scripts/monitoring/test-dns-activity.py`. Roll back by removing the collector invocation at the end of collect-status.py and the DNS section/script from the landing page. No container restart, Pi-hole configuration change, credentials or router access is required.

All web access to this summary now requires the centralized HTTPS login. Anonymous labels remain useful for minimizing data, but the export is no longer a public endpoint.
