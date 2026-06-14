-- Todo #1: G38 #11 - 候选人阶段流转记录表
-- 新表 application_stage_records + 4 索引
-- MySQL 8 不支持 CREATE TABLE IF NOT EXISTS 对带外键的表安全(可能因为 FK 命名漂移冲突)
-- 用 stored procedure + information_schema.tables 守护,可重复跑

-- ============================================
-- 1) CREATE TABLE application_stage_records
-- ============================================
DROP PROCEDURE IF EXISTS create_application_stage_records_table;
CREATE PROCEDURE create_application_stage_records_table()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                 WHERE table_schema = DATABASE()
                   AND table_name = 'application_stage_records') THEN
    CREATE TABLE `application_stage_records` (
      `id` VARCHAR(191) NOT NULL,
      `applicationId` VARCHAR(191) NOT NULL,
      `candidateId` VARCHAR(191) NOT NULL,
      `processId` VARCHAR(191) NOT NULL,
      `linkId` VARCHAR(191) NOT NULL,
      `stageId` VARCHAR(191) NOT NULL,
      `fromStatus` VARCHAR(32) NULL,
      `toStatus` VARCHAR(32) NOT NULL,
      `decision` VARCHAR(32) NULL,
      `enteredAt` DATETIME(3) NULL,
      `exitedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
      `decidedBy` VARCHAR(191) NULL,
      `decisionReason` TEXT NULL,
      `autoAdvanced` BOOLEAN NOT NULL DEFAULT false,
      `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
      PRIMARY KEY (`id`),
      INDEX `application_stage_records_applicationId_exitedAt_idx`(`applicationId`, `exitedAt`),
      INDEX `application_stage_records_linkId_exitedAt_idx`(`linkId`, `exitedAt`),
      INDEX `application_stage_records_candidateId_exitedAt_idx`(`candidateId`, `exitedAt`),
      INDEX `application_stage_records_toStatus_idx`(`toStatus`)
    ) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  END IF;
END;
CALL create_application_stage_records_table();
DROP PROCEDURE create_application_stage_records_table;

-- ============================================
-- 2) CREATE INDEX 1: applicationId + exitedAt
-- ============================================
DROP PROCEDURE IF EXISTS idx_asr_app_exited;
CREATE PROCEDURE idx_asr_app_exited()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'application_stage_records'
                   AND index_name = 'application_stage_records_applicationId_exitedAt_idx') THEN
    CREATE INDEX `application_stage_records_applicationId_exitedAt_idx`
      ON `application_stage_records`(`applicationId`, `exitedAt`);
  END IF;
END;
CALL idx_asr_app_exited();
DROP PROCEDURE idx_asr_app_exited;

-- ============================================
-- 3) CREATE INDEX 2: linkId + exitedAt
-- ============================================
DROP PROCEDURE IF EXISTS idx_asr_link_exited;
CREATE PROCEDURE idx_asr_link_exited()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'application_stage_records'
                   AND index_name = 'application_stage_records_linkId_exitedAt_idx') THEN
    CREATE INDEX `application_stage_records_linkId_exitedAt_idx`
      ON `application_stage_records`(`linkId`, `exitedAt`);
  END IF;
END;
CALL idx_asr_link_exited();
DROP PROCEDURE idx_asr_link_exited;

-- ============================================
-- 4) CREATE INDEX 3: candidateId + exitedAt
-- ============================================
DROP PROCEDURE IF EXISTS idx_asr_candidate_exited;
CREATE PROCEDURE idx_asr_candidate_exited()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'application_stage_records'
                   AND index_name = 'application_stage_records_candidateId_exitedAt_idx') THEN
    CREATE INDEX `application_stage_records_candidateId_exitedAt_idx`
      ON `application_stage_records`(`candidateId`, `exitedAt`);
  END IF;
END;
CALL idx_asr_candidate_exited();
DROP PROCEDURE idx_asr_candidate_exited;

-- ============================================
-- 5) CREATE INDEX 4: toStatus
-- ============================================
DROP PROCEDURE IF EXISTS idx_asr_toStatus;
CREATE PROCEDURE idx_asr_toStatus()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'application_stage_records'
                   AND index_name = 'application_stage_records_toStatus_idx') THEN
    CREATE INDEX `application_stage_records_toStatus_idx`
      ON `application_stage_records`(`toStatus`);
  END IF;
END;
CALL idx_asr_toStatus();
DROP PROCEDURE idx_asr_toStatus;