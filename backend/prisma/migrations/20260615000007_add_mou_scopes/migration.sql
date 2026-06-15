-- Drift fix #7: Mou.scopes (G43 字段 ACL 配套)
-- Schema 有, live DB 缺. Idempotent via stored procedure.

DROP PROCEDURE IF EXISTS add_mou_scopes;
CREATE PROCEDURE add_mou_scopes()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'mous'
                   AND column_name = 'scopes') THEN
    ALTER TABLE `mous` ADD COLUMN `scopes` JSON NULL AFTER `description`;
  END IF;
END;
CALL add_mou_scopes();
DROP PROCEDURE add_mou_scopes;
