# Centralized authentication and session flow

One Authelia login gates every application page, snapshot, download and API behind the HTTPS gateway. All valid portal users currently have the same access; separate RBAC and mTLS are not implemented. The provider’s login assets and necessary authentication API remain reachable so users can authenticate; these routes do not expose application inventory.

## Login and authorized requests

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser
    participant Edge as HTTPS edge and WAF
    participant Router as Application router
    participant Identity as Authelia
    participant App as Protected application
    User->>Browser: Open configured gateway hostname
    Browser->>Edge: GET protected page
    Edge->>Router: Filtered request
    Router->>Identity: Authorize current session
    Identity-->>Router: No valid session
    Router-->>Browser: Redirect HTML request to login
    User->>Browser: Enter portal credentials locally
    Browser->>Edge: POST authentication request over HTTPS
    Edge->>Identity: Provider authentication route
    Identity->>Identity: Verify Argon2id password hash and login regulation
    Identity-->>Browser: Secure HttpOnly SameSite cookie
    Browser->>Edge: Request page with session cookie
    Edge->>Router: Forward canonical origin and client context
    Router->>Identity: Validate session
    Identity-->>Router: Authorized identity
    Router->>App: Serve or proxy allowed route
    App-->>Browser: Protected response
```

Anonymous JSON/API requests receive an authentication error instead of a misleading login document. An unavailable provider fails closed. Client-supplied identity headers are stripped at the edge; a claimed username is not accepted as proof of authentication. Application write paths require the configured same Origin, while the provider handles its own authentication/session protections. WAF method exceptions are exact Pi-hole operations, not a gateway-wide permission change.

The configured session has a 30-minute inactivity timeout and an eight-hour absolute lifetime. Login regulation limits repeated failed passwords. Passwords are chosen locally; the portal stores an Argon2id hash rather than plaintext. Provider session/storage secrets and state are private, ignored runtime files. A file-backed Compose secret is not an encrypted vault. Do not regenerate a storage key against an existing encrypted provider database.

## Pi-hole without a second user login

```mermaid
sequenceDiagram
    participant Browser
    participant Router as Authorized application router
    participant Bridge as Pi-hole session bridge
    participant Identity as Authelia
    participant Pihole as Native Pi-hole API
    Browser->>Router: Open native admin or API with central cookie
    Router->>Identity: Validate central session
    Identity-->>Router: Authorized
    Router->>Bridge: Forward request and central cookie internally
    Bridge->>Identity: Independently validate central session
    Identity-->>Bridge: Authorized username
    alt No usable native session cached for this user
        Bridge->>Pihole: Authenticate using mounted private backend password
        Pihole-->>Bridge: Native session and CSRF data
    end
    Bridge->>Pihole: Forward request with server-side native authentication
    Pihole-->>Bridge: Native application response
    Bridge-->>Browser: Response through the central gateway
```

Pi-hole’s native password authentication remains enabled. The bridge does not forward the central cookie to Pi-hole or send the backend password to the browser. Cached native sessions remain server-side; every bridge request still needs central authorization. A native authentication failure is retried once with a renewed native session; persistent failure returns unavailable. Direct backend web ports are not published.

## Logout, expiry and failure

```mermaid
sequenceDiagram
    participant Browser
    participant Gateway as HTTPS gateway
    participant Identity as Authelia
    participant App as Protected application
    Browser->>Browser: Clear private dashboard content
    Browser->>Gateway: POST central logout
    Gateway->>Identity: Invalidate shared session
    Identity-->>Browser: Session ended
    Browser->>Gateway: Later protected page or API request
    Gateway->>Identity: Authorize session
    Identity-->>Gateway: Unauthorized
    Gateway-->>Browser: Login redirect for HTML or authentication error for API
    Note over Gateway,App: No protected backend request is authorized
```

The portal revalidates when returning from browser history and clears private data on an authentication failure. Central logout was verified to block both the portal and native Pi-hole. Pi-hole’s separate backend logout action is replaced by the central session flow; it is not another independent login boundary.

For controls, exact WAF exceptions, configuration and validation limits, see [gateway security and operations](GATEWAY.md). For topology, see [architecture](../ARCHITECTURE.md). These diagrams document implemented controls and known boundaries; they are not an assertion of complete OWASP compliance.
