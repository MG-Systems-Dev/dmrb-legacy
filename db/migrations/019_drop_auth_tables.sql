UPDATE phase_scope SET user_id = NULL WHERE user_id IS NOT NULL;

DROP TABLE IF EXISTS api_session;
DROP TABLE IF EXISTS app_user;
