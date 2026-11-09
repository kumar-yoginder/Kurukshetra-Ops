# Kurukshetra-Ops standing requirements

- All web pages and application APIs must be served through the HTTPS Nginx gateway behind one centralized authenticated session. No per-feature sign-in or new direct host web ports. The centralized gateway is deployed and verified; preserve shared authorization on every new route.
- Preserve essential DNS, WireGuard and SSH recovery protocols while tightening web exposure. Do not confuse those protocols with extra web entry points.
- All valid portal users have the same access for now; separate RBAC is not requested.
- Apply OWASP web/API risk controls and evidence-based security tests. A WAF is one layer, not proof of compliance. Never bypass backend authorization silently to simulate single sign-on.
- Keep private device data, credentials, keys, site configuration, and implementation plans out of Git. Secrets are entered locally and never logged or displayed.
- Saved JSON must use two-space indentation, readable Unicode, and a trailing newline; preserve atomic writes and private permissions.
- Follow the existing feature structure, use Pydantic contracts and small Python classes for new collector services, keep UI HTML/CSS/JavaScript separate, and label inferred/stale telemetry accurately.
