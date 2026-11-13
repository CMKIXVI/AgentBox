-- AgentBox OIDC callback transaction store, migration 0001.
-- Store hashes and secret-manager references only; never raw OAuth/OIDC secrets.
CREATE TABLE IF NOT EXISTS oidc_callback_transactions (
    transaction_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    state_hash CHAR(64) NOT NULL CHECK (state_hash ~ '^[0-9a-f]{64}$'),
    nonce_hash CHAR(64) NOT NULL CHECK (nonce_hash ~ '^[0-9a-f]{64}$'),
    pkce_verifier_ref TEXT NOT NULL,
    created_at_epoch BIGINT NOT NULL,
    expires_at_epoch BIGINT NOT NULL,
    CHECK (expires_at_epoch > created_at_epoch),
    CHECK (expires_at_epoch - created_at_epoch <= 600)
);
CREATE INDEX IF NOT EXISTS idx_oidc_callback_transactions_expiry
    ON oidc_callback_transactions (expires_at_epoch);
