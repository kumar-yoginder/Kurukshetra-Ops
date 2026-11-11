# Lightweight operational log viewer

Open the central portal and select **Logs**, or use `/#logs`. Chitragupt also has a View operational events shortcut. The same central session protects the page and `/log-events.json`. No new service, database, Docker socket mount or host port is added. Grafana remains the metrics viewer.

## What is retained

The existing host minute job calls `scripts/monitoring/collect-logs.py`. It reads only ten fixed container names through the local Docker CLI. Each read has a two-second timeout, 256 KiB output limit and 200-line input tail. First collection reads at most five minutes of history. Later collections use per-service timestamp cursors.

Raw lines stay in process memory. The collector emits only a validated Docker timestamp, fixed service name, severity enum and category enum. It never publishes original messages, stack traces, logger names, request paths, credentials, addresses or Telegram identities. This intentionally trades diagnostic detail for a strict privacy boundary; regex redaction alone would not reliably identify every private value. Unrecognized lines are discarded. Categories are inferred from log wording, not authoritative incident classifications.

The snapshot retains at most 2,000 events across all services for up to 24 hours. Equal timestamp/service/category/severity entries are collapsed. The UI shows the newest 300 matching events, with service and severity filters. A source marked bounded may have lost events; unavailable means the read failed. No events does not prove the application is healthy. Full output remains available using local `docker logs`.

## Storage and lifecycle

Only the sanitized snapshot is published under ignored `config/nginx/www/log-events.json`. It is readable by the internal application router and requires gateway authentication externally. Private cursors and a non-overlap lock live under ignored owner-only `config/observability/private/logs/`. Snapshot publication is atomic, indented and newline-terminated. No raw log history is copied.

Retention is applied on each successful collector run. If the schedule stops, the last file remains on disk and the UI marks it stale after three minutes; the 24-hour window is not a guaranteed deletion deadline during an outage. Busy sources, restarts, Docker rotation, input caps and clock changes can leave gaps. Cursor advancement after a bounded read intentionally prevents retry storms. This is an operational summary, not an audit log or a full-text log search system.

## Maintenance and verification

```bash
.venv-router/bin/python scripts/monitoring/test-logs.py
python3 scripts/monitoring/collect-logs.py
python3 tests/gateway/verify-edge.py
```

There is no new schedule to install. Keep the existing status job enabled. To disable collection, remove only the log-collector invocation from that job; deleting a snapshot alone does not disable its producer. No bot restart is needed.
