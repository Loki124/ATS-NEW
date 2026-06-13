-- Plan L #11: 添加 process_stage_links.stageType 列 (2026-06-14 drift fix)
-- Schema has it, baseline missing. Idempotent via stored proc.

DROP PROCEDURE IF EXISTS add_link_stage_type;
CREATE PROCEDURE add_link_stage_type()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'process_stage_links'
                   AND column_name = 'stageType') THEN
    ALTER TABLE `process_stage_links`
      ADD COLUMN `stageType` VARCHAR(32) NOT NULL DEFAULT 'SCREENING' AFTER `orderIndex`;
  END IF;
END;
CALL add_link_stage_type();
DROP PROCEDURE add_link_stage_type;
