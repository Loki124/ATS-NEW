-- Drift fix: User.lastLoginAt 字段在 schema 但 baseline migration 缺
-- Idempotent via stored procedure.

DROP PROCEDURE IF EXISTS add_user_last_login_at;
CREATE PROCEDURE add_user_last_login_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'users'
                   AND column_name = 'lastLoginAt') THEN
    ALTER TABLE `users` ADD COLUMN `lastLoginAt` DATETIME(3) NULL AFTER `updatedAt`;
  END IF;
END;
CALL add_user_last_login_at();
DROP PROCEDURE add_user_last_login_at;

-- index (登录时间查询 / 排序)
DROP PROCEDURE IF EXISTS add_user_last_login_at_idx;
CREATE PROCEDURE add_user_last_login_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'users'
                   AND index_name = 'users_lastLoginAt_idx') THEN
    CREATE INDEX `users_lastLoginAt_idx` ON `users`(`lastLoginAt`);
  END IF;
END;
CALL add_user_last_login_at_idx();
DROP PROCEDURE add_user_last_login_at_idx;
