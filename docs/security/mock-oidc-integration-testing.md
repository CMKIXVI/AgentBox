# AgentBox mock OIDC integration test harness

**Scope:** Backend authentication boundary and simulated OIDC protocol tests  
**Environment:** CI/test only; no external identity provider or network calls  
**Security boundary:** This harness is not a production identity provider and does not replace provider-specific end-to-end testing.

## What it covers

The in-memory test provider in `backend/tests/mock_oidc_provider.py` models:

- OIDC discovery and RSA JWKS documents
- Authorization Code grants bound to an exact client and redirect URI
- PKCE S256 challenge/verifier matching and single-use authorization codes
- State comparison and nonce binding/validation
- Signed ID and API access tokens with issuer, audience, subject, tenant and expiry claims
- Access-token expiry rejection by the real AgentBox OIDC authenticator
- Refresh-token rotation and replay rejection
- Logout-style refresh-token revocation

The API integration tests patch only the network JWKS key resolver. They still exercise the real `OIDCAuthenticator`, FastAPI authentication dependency, active-tenant lifecycle gate, authorization policy evaluation and protected API route.

## Run locally

From the repository root:

```bash
cd backend
pip install -e ".[dev]"
pytest tests/test_oidc_integration.py
ruff check app tests
```

## Security scenarios

| Scenario | Expected result |
|---|---|
| Valid signed token, active tenant, matching grant | Protected API returns success |
| Missing bearer token with OIDC configured | 401 |
| Caller-supplied identity or tenant headers without a token | 401 |
| Forged tenant header with valid token | Header is ignored; signed tenant claim governs |
| Valid token for a different tenant without matching grant | 403 |
| Expired access token | 401 |
| Incorrect PKCE verifier | Authorization-code exchange rejected |
| Replayed authorization code | Rejected |
| State mismatch | Rejected by callback-state check |
| Nonce mismatch | ID-token validation rejected |
| Refresh-token replay | Rejected after rotation |
| Refresh token after logout/revocation | Rejected |

## Explicit limitations

These tests do not start a real HTTP OIDC issuer, drive the Next.js/Auth.js browser callback, automate an Android/iOS system-browser redirect, or verify an external provider's discovery, JWKS rotation, client authentication, logout endpoint, cookie settings, or consent behavior. The simulated state/nonce/PKCE assertions test protocol expectations; they do not independently prove Auth.js or AppAuth callback correctness.

Before production, run browser/device end-to-end tests against a selected non-production provider and deployed AgentBox API. Validate actual redirect registration, state/nonce/PKCE behavior, cookie attributes, refresh rotation, logout/revocation, issuer/audience/JWKS validation, and cross-tenant denial.
