# Chitragupt integration

The existing [Chitragupt bot](https://github.com/kumar-yoginder/chitragupt) remains managed by its separate Compose project. Kurukshetra-Ops does not start another Telegram poller or alter the bot’s source, credentials or registry.

The portal has a Chitragupt section and a link to its Grafana dashboard. Both require the existing central HTTPS login. There are no message, role-editing, restart or Telegram administration controls.

## Collection boundary

The existing host minute job runs `collect-chitragupt.py`. It inspects only selected runtime fields, then executes a bounded standard-library probe as the application user inside the running container. Each supported registry input is capped at 2 MiB. Only anonymous totals leave the container, and Pydantic validates the output before atomic publication. Web services receive neither the Docker socket nor the bot databases.

The protected snapshot reports runtime state, uptime, restarts, registered identity/chat counts, fixed chat categories, bounded numeric role-level counts and schema availability. It excludes IDs, names, chat titles, custom role names, messages, credentials and raw logs. Missing or malformed inputs become unavailable rather than a fabricated zero. Generated JSON and metric files are ignored by Git.

## Meaning and limits

A running container does not prove Telegram connectivity. Application health, polling heartbeat and request latency remain uninstrumented. Stored identities are not verified humans, online users or current Telegram group membership. Counts describe registry state at collection time. Stale observations are labeled; history begins when collection starts.

The optional observability profile stores only allowlisted aggregate metrics. Its OTLP receiver is internal and privacy-filtered, but the bot has not yet been instrumented to emit application metrics. Raw Telegram HTTP tracing must not be enabled without removing token-bearing URLs and personal attributes.

## Maintenance

Run the privacy tests with `.venv-router/bin/python scripts/monitoring/test-chitragupt.py`. A collection failure must not restart the bot or fall back to dumping its logs/configuration. When changing the upstream schema or container name, update and test the adapter explicitly. See [observability operations](../observability/README.md).
