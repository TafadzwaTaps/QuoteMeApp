-- ════════════════════════════════════════════════════════════
-- QuoteMe ZW — Site User Accounts
-- Run this in: Supabase Dashboard → SQL Editor
-- ════════════════════════════════════════════════════════════

-- 1. SITE USERS TABLE
CREATE TABLE IF NOT EXISTS site_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(60)  UNIQUE NOT NULL,
    email         VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    is_banned     INTEGER DEFAULT 0,
    ban_reason    VARCHAR(300),
    created_at    TIMESTAMP DEFAULT NOW(),
    last_seen     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_site_users_email    ON site_users(email);
CREATE INDEX IF NOT EXISTS idx_site_users_username ON site_users(username);
CREATE INDEX IF NOT EXISTS idx_site_users_banned   ON site_users(is_banned);

-- 2. Add user_id column to comments (tracks which account left the comment)
ALTER TABLE comments ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES site_users(id);

-- 3. Add user_id column to forumpost (tracks which account made the post)
ALTER TABLE forumpost ADD COLUMN IF NOT EXISTS user_id INTEGER;

-- ════════════════════════════════════════════════════════════
-- After running this migration, the following endpoints work:
--
-- PUBLIC:
--   POST /users/register  — create account (username, email, password)
--   POST /users/login     — sign in (email, password) → JWT token
--   GET  /users/me        — get current user profile from token
--   POST /comments        — requires Bearer token (user must be logged in)
--   POST /forum/post      — requires Bearer token (user must be logged in)
--
-- ADMIN:
--   GET  /admin/users              — list all registered users
--   POST /admin/users/{id}/ban     — ban a user (with reason)
--   POST /admin/users/{id}/unban   — lift a ban
--   DELETE /admin/users/{id}       — permanently delete account
-- ════════════════════════════════════════════════════════════
