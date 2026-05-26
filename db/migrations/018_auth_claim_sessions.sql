-- Migration 018: auth claim sessions
-- Makes password_hash nullable (admin-created users may have no password set yet),
-- adds claimed_at marker to app_user (set when first admin claims via /setup),
-- and creates the api_session table for server-side session storage.

-- Make password nullable for admin-created users that haven't set a password yet
ALTER TABLE app_user ALTER COLUMN password_hash DROP NOT NULL;

-- Claim marker: set when an admin completes /setup or changes their password
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;

-- Backfill: existing admins with a password hash count as already claimed
UPDATE app_user
   SET claimed_at = COALESCE(claimed_at, created_at)
 WHERE role = 'admin' AND password_hash IS NOT NULL;

-- Server-side opaque session store (replaces signed itsdangerous cookie payload)
CREATE TABLE IF NOT EXISTS api_session (
    session_id  TEXT        PRIMARY KEY,
    user_id     BIGINT      NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_session_expires ON api_session(expires_at);
CREATE INDEX IF NOT EXISTS idx_api_session_user    ON api_session(user_id);
