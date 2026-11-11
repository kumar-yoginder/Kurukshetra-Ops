# Central gateway security and operations

See [architecture](../ARCHITECTURE.md), [data flow](../networking/DATA-FLOW.md), and [authentication sequence diagrams](AUTHENTICATION.md) for the system overview.

## Access model

Use the configured gateway hostname over HTTPS. The IP-address URL is deliberately rejected so cookies, certificate names and same-origin checks have one canonical origin. One Authelia session gates the portal, snapshots, inventory, client downloads, Pi-hole and optional monitoring routes. All portal accounts have the same access; no role hierarchy is configured. The login page and its necessary assets/API are the authentication entry point. Backends have no published web ports. HTTP port 80 is closed, rather than redirected.

Request path: TLS Nginx → OWASP CRS WAF → application router → session authorization → application. Identity failure denies application access. Pi-hole retains native password authentication: the internal bridge validates the central session and supplies a native session server-side. Its password is not sent to the browser. Central sign-out invalidates the shared session; the dashboard clears private content and revalidates on return from browser history. Native administrative data remains privileged even though no second login is required.

DNS 53, SSH 22 and WireGuard UDP 51820 are intentional non-web services. This change does not prohibit them. Docker internal listeners are not host-published listeners. Do not expose the Docker socket or identity, WAF, inventory, bridge or application router directly.

## Configuration and credentials

Canonical templates are under `config/gateway/templates/`; reviewed WAF exceptions are under `config/gateway/waf/`. `scripts/security/configure-gateway.py` prepares private runtime configuration after hidden local prompts. It stores an Argon2id password hash and separately generated session/storage secrets. Do not regenerate storage encryption keys against an existing database. Existing identity files are not silently overwritten. Credentials, generated configuration and identity state are ignored by Git and excluded from image build contexts.

File-backed Compose secrets are restricted local files, not an encrypted vault. Keep private directories owner-only and secret files mode 600. Restrict Pi administrator and Docker-group access: Docker administration is privileged. Back up identity state together with its storage encryption key using a private backup destination.

Authelia root filesystem is read-only except state, temporary storage and its single healthcheck metadata file. Startup regulation limits repeated failed passwords. Session inactivity is 30 minutes, absolute lifetime eight hours; browser cookies are Secure, HttpOnly and SameSite=Lax. Reboot behavior and natural long-duration expiry are separate follow-up checks.

## OWASP risk controls

| Risk area | Implemented control | Limit / ongoing responsibility |
| --- | --- | --- |
| Broken access control / API authorization | Default-deny shared session checks on application routes; bridge independently validates session | One equal-access account class; LAN root/Docker administrators remain trusted |
| Cryptographic failures | TLS 1.2/1.3, AEAD cipher allowlist, HSTS, Argon2id hashes, private secret files | Client trust in the local CA must be managed; secrets on disk are not a vault |
| Injection | CRS blocking mode, bounded request sizes, text-only DOM rendering, fixed upstreams | WAF is supplementary; application-specific validation still matters |
| Misconfiguration | Single HTTPS web listener, internal backends, dropped capabilities, immutable/pinned image versions | Updates require reviewed testing; optional profiles need their own end-to-end checks |
| Authentication / session failure | Shared provider, expiry, failed-login regulation, central logout | Password strength and account lifecycle remain operator responsibilities |
| CSRF | Exact canonical Origin for unsafe Pi-hole and monitoring API requests; provider handles login/session CSRF | Browsers must send the expected origin; no wildcard CORS |
| Resource exhaustion | Edge request/connection limits, timeouts, body limits, container resource bounds | Not upstream DDoS protection |
| Logging / sensitive data | Safe access logs omit query strings, cookies and bodies; WAF audit parts AZ | Avoid debug logging real credentials; monitor failed auth and service health |
| SSRF / unsafe API consumption | Fixed bridge upstream, router RPC allowlist, pinned router TLS certificate, no redirect fallback | Router guest write restrictions have not been comprehensively verified |

These controls are a risk reduction baseline, not certification or proof that every OWASP issue is absent.

## WAF exceptions

Global HTTP method policy remains unchanged. Fifteen method-and-endpoint pairs were derived from the running Pi-hole 6 OpenAPI schema; only method-policy rule 911100 is excluded for those pairs. The bridge still requires a valid central session and exact Origin. DELETE `/api/auth` is deliberately not included: use central sign-out. Two exact versioned Authelia JavaScript assets contain `.Password` in their filenames; only REQUEST_FILENAME inspection by rule 930130 is excluded for those two GET/HEAD assets. The six named Ubuntu/Windows controller/helper downloads have a GET/HEAD-only exception for extension rule 920440, while central login and all other WAF rules remain enforced. Other targets/rules remain active. Review these exact asset names when updating Authelia.

## Operations

```bash
./deploy.sh --gateway --inventory config --quiet
./deploy.sh --gateway --inventory up -d --build
./deploy.sh --gateway --inventory ps
./deploy.sh --gateway --inventory logs --tail 30 identity gateway-waf web-router pihole-bridge
```

Do not print generated private configuration or full container environments in shared logs. Keep authentication active during repair; do not restore anonymous fallback routes. Configuration changes need `nginx -t` before reload. The former loopback inventory forwarding workflow is retired. Optional Kibana/Elasticsearch profiles are preserved but were not started or tested by this cutover.

## Verified checkpoint

The deployed gateway passed TLS-verified anonymous rejection for snapshots, inventory and Pi-hole API; login rendering; WAF script-injection blocking; approved Pi-hole method requiring authentication; disallowed method rejection outside those endpoints; direct port closure; authenticated dashboard data, device search, native Pi-hole live statistics without a second login; and central logout preventing Pi-hole access. Browser phone viewport emulation was ineffective in this environment and is not claimed as completed mobile validation. No outage or reboot test was repeated.

Temporary diagnostic access cleanup: the operator removed the scoped sudoers entry and installed diagnostic executable. The executable is absent and a passwordless invocation is denied.
