# Floppy provider security notes

The Floppy sync provider is designed for self-hosted endpoints and therefore intentionally permits both public and private network addresses.

Security requirements:

- Only `http://` and `https://` server URLs are accepted.
- Embedded URL credentials, query strings, and fragments are rejected.
- TLS certificate verification remains enabled by the underlying `requests` library for HTTPS endpoints.
- Bearer tokens are injected immediately before transport so TMDbHelper's generic request error logger never receives the token-bearing header.
- Tokens containing CR/LF control characters or unexpectedly large values are rejected.
- The token is never placed in the request URL.
- The provider currently performs read-only sync operations only.

For remote Floppy instances, HTTPS should be used. Plain HTTP is intended only for trusted local-network deployments where TLS termination is not configured.
