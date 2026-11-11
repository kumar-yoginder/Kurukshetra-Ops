# Network observatory design system

## Structure

Desktop uses a collapsible navigation rail, main workspace and a context panel when width permits. The main workspace has a session header, title/refresh action, freshness notice, three metrics, asymmetric DNS chart/presence ring and selectable device cards. Views: overview, inventory, activity history, services, Internet speed and Tor gateway. Narrow layouts stack metrics and content and move navigation/context into the document flow. All inventory presentation lives in this shared portal; there is no separate detailed-inventory page.

## Theme and typography

| Token | Value / purpose |
| --- | --- |
| Background | `#070A0F` |
| Glass surface | `rgba(18,24,38,.65)` with 16px blur |
| Cyan | `#00F0FF` active telemetry |
| Violet | `#7C3AED` secondary accent |
| Main text | `#F8FAFC` |
| Muted text | `#94A3B8` |
| Border | `rgba(0,240,255,.2)` |
| Display | Self-hosted Space Grotesk, geometric headings |
| Body | Self-hosted Inter |
| Data | Self-hosted JetBrains Mono |

Type hierarchy: page title approximately 34px, section headings 20px, body 13–14px, telemetry labels 11px, large metric readouts 40px. Use readable tracking on short uppercase labels, not paragraph text. Font licenses are stored beside the self-hosted files. CSS variables and responsive rules are canonical in `config/portal/www/portal.css`; HTML and behavior are separate files. No external font CDN or inline executable scripts are required.

## Interaction flows

1. Enter the canonical HTTPS hostname → central login → overview. Session gates each data request as well as the document.
2. Open inventory → search name/address/hint or filter observed Wi-Fi versus lease-only → select a record → inspect evidence, addresses and uncertainty.
3. Enable diagnostic view → reveal provenance text; this is a display preference, not a permission or scan control.
4. Adjust display density → change spacing without mutating collection settings.
5. Open Services or Tor → inspect freshness and cached measurements. Downloads remain behind the central session; no private peer profile is published.
6. Sign out → clear private DOM → invalidate shared session → login. Expired or rejected sessions redirect to login; stale collection does not imply devices disconnected.

Motion uses the requested cubic-bezier(.16,1,.3,1) easing, restrained elevation and cursor-following card light. Reduced-motion disables nonessential effects. Controls have names, focus indicators and selected states; status has text as well as color. Charts use real data and text summaries. OS labels are hostname-derived hints, not verified fingerprints. No fabricated charts or confidence percentages are shown.

## Validation limits

Desktop rendering, live data, search and central session flows were checked in the browser. Responsive CSS exists, but the browser viewport override did not change the observed viewport; a real phone check remains advisable. Provider-managed login UI uses Authelia’s dark theme rather than custom credential-handling JavaScript.

Internet speed shows separately timed home/Tor download, upload and HTTPS response samples with byte caps and freshness. See [measurement details](../networking/CONNECTION-SPEED.md). The old standalone detailed-inventory UI was removed; the shared portal uses its retained JSON feed.
