-- Drift fix: Application.currentLinkId (Plan L 漏)
-- Idempotent via stored procedure.

DROP PROCEDURE IF EXISTS add_app_current_link_id;
CREATE PROCEDURE add_app_current_link_id()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'applications'
                   AND column_name = 'currentLinkId') THEN
    ALTER TABLE `applications` ADD COLUMN `currentLinkId` VARCHAR(191) NULL AFTER `currentStageStatus`;
  END IF;
END;
CALL add_app_current_link_id();
DROP PROCEDURE add_app_current_link_id;

DROP PROCEDURE IF EXISTS add_app_current_link_id_idx;
CREATE PROCEDURE add_app_current_link_id_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'applications'
                   AND index_name = 'applications_currentLinkId_idx') THEN
    CREATE INDEX `applications_currentLinkId_idx` ON `applications`(`currentLinkId`);
  END IF;
END;
CALL add_app_current_link_id_idx();
DROP PROCEDURE add_app_current_link_id_idx;
