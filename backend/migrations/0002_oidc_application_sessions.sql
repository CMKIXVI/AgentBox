-- AgentBox opaque OIDC application sessions, migration 0002.
-- Persist only SHA-256 hashes of session and CSRF credentials.
CREATE TABLE IF NOT EXISTS oidc_application_sessions (
    token_hash CHAR(64) PRIMARY KEY CHECK(token_hash ~ '^[0-9a-f]{64}$'),
    csrf_token_hash CHAR(64) NOT NULL CHECK(csrf_token_hash ~ '^[0-9a-f]{64}$'),
    subject_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    issuer TEXT NOT NULL,
    client_id TEXT NOT NULL,
    created_at_epoch BIGINT NOT NULL,
    expires_at_epoch BIGINT NOT NULL,
    revoked_at_epoch BIGINT,
    CHECK(expires_at_epoch > created_at_epoch),
    CHECK(expires_at_epoch - created_at_epoch <= 43200),
    CHECK(revoked_at_epoch IS NULL OR revoked_at_epoch >= created_at_epoch)
);
CREATE INDEX IF NOT EXISTS idx_oidc_application_sessions_expiry
    ON oidc_application_sessions (expires_at_epoch);
CREATE INDEX IF NOT EXISTS idx_oidc_application_sessions_tenant
    ON oidc_application_sessions (tenant_id, subject_id);
