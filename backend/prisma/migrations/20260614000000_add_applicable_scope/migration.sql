-- Plan L #11: 添加 applicableScope JSON 列 (2026-06-14 drift fix)
-- Schema has it, baseline missing. Idempotent via stored proc.

DROP PROCEDURE IF EXISTS add_applicable_scope;
CREATE PROCEDURE add_applicable_scope()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'recruitment_processes'
                   AND column_name = 'applicableScope') THEN
    ALTER TABLE `recruitment_processes`
      ADD COLUMN `applicableScope` JSON NULL AFTER `applicableMode`;
  END IF;
END;
CALL add_applicable_scope();
DROP PROCEDURE add_applicable_scope;
