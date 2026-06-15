-- ════════════════════════════════════════════════════════════
-- QuoteMe ZW v3 — Moderation & User Management Migration
-- Run in: Supabase Dashboard → SQL Editor
-- ════════════════════════════════════════════════════════════

-- 1. Add role, bio, avatar to site_users
ALTER TABLE site_users ADD COLUMN IF NOT EXISTS role        VARCHAR(20)  DEFAULT 'user';
ALTER TABLE site_users ADD COLUMN IF NOT EXISTS bio         VARCHAR(300);
ALTER TABLE site_users ADD COLUMN IF NOT EXISTS avatar_url  VARCHAR(400);

-- 2. Add is_hidden to comments (soft-delete by admin)
ALTER TABLE comments ADD COLUMN IF NOT EXISTS is_hidden  BOOLEAN DEFAULT FALSE;

-- 3. Add user_id to comments (already in previous migration, idempotent)
ALTER TABLE comments ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES site_users(id);

-- 4. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_comments_is_hidden   ON comments(is_hidden);
CREATE INDEX IF NOT EXISTS idx_comments_sentiment   ON comments(sentiment);
CREATE INDEX IF NOT EXISTS idx_comments_item        ON comments(item_type, item_id);
CREATE INDEX IF NOT EXISTS idx_site_users_role      ON site_users(role);

-- ════════════════════════════════════════════════════════════
-- New endpoints after this migration:
--
-- GET  /admin/comments?sentiment_filter=&item_type=&show_hidden=all
-- POST /admin/comments/{id}/hide
-- POST /admin/comments/{id}/restore
-- GET  /admin/comments/stats
-- GET  /admin/users/stats
-- POST /admin/users/{id}/promote      { role: "moderator"|"user"|"admin" }
-- POST /admin/users/{id}/suspend      { reason: "..." }
-- POST /admin/users/{id}/reactivate
-- POST /admin/users/{id}/reset-password { new_password: "..." }
-- POST /users/change-password         { current_password, new_password } (user JWT)
-- GET  /admin/stats/extended
-- ════════════════════════════════════════════════════════════
