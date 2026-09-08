# Floppy provider security notes

The Floppy sync provider is designed for self-hosted endpoints and therefore intentionally permits both public and private network addresses.

Security requirements:

- Only `http://` and `https://` server URLs are accepted.
- Embedded URL credentials, query strings, fragments, invalid ports, URL control characters, and host whitespace are rejected.
- TLS certificate verification remains enabled by the underlying `requests` library for HTTPS endpoints.
- Redirect following is disabled while Floppy bearer credentials are attached, preventing credentials from being forwarded to an unexpected redirect target.
- Bearer tokens are injected immediately before transport so TMDbHelper's generic request error logger never receives the token-bearing header.
- Tokens containing control characters or unexpectedly large values are rejected.
- The token is never placed in the request URL.
- API pagination is bounded and response metadata is validated. Malformed or excessive responses fail closed and do not replace a previously valid local sync cache with partial data.
- Provider capabilities are explicitly gated so selecting Floppy cannot silently route unsupported watchlist or collection operations through another provider.
- Provider-specific hidden-state fields are cleared when Floppy is the watched provider to avoid retaining stale Trakt/MDbList filtering state.
- The provider currently performs read-only sync operations only.

For remote Floppy instances, HTTPS should be used. Plain HTTP is intended only for trusted local-network deployments where TLS termination is not configured.
