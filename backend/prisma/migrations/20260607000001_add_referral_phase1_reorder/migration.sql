-- DropIndex (guarded: only drop if column exists, because baseline creates `applications` WITHOUT `referralUserId`)
DROP PROCEDURE IF EXISTS drop_referral_user_id_index;
CREATE PROCEDURE drop_referral_user_id_index()
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = DATABASE()
               AND table_name = 'applications'
               AND column_name = 'referralUserId') THEN
    DROP INDEX `applications_referralUserId_idx` ON `applications`;
  END IF;
END;
CALL drop_referral_user_id_index();
DROP PROCEDURE drop_referral_user_id_index;

-- AlterTable (guarded: only drop column if it exists)
DROP PROCEDURE IF EXISTS drop_referral_user_id_column;
CREATE PROCEDURE drop_referral_user_id_column()
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = DATABASE()
               AND table_name = 'applications'
               AND column_name = 'referralUserId') THEN
    ALTER TABLE `applications` DROP COLUMN `referralUserId`;
  END IF;
END;
CALL drop_referral_user_id_column();
DROP PROCEDURE drop_referral_user_id_column;

-- CreateTable
CREATE TABLE IF NOT EXISTS `referral_codes` (
    `id` VARCHAR(191) NOT NULL,
    `code` VARCHAR(16) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `invalidReason` VARCHAR(64) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `referral_codes_code_key`(`code`),
    UNIQUE INDEX `referral_codes_userId_key`(`userId`),
    INDEX `referral_codes_status_idx`(`status`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE IF NOT EXISTS `referral_expert_configs` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `teamId` VARCHAR(191) NOT NULL,
    `expertId` VARCHAR(191) NOT NULL,
    `referralCodeId` VARCHAR(191) NULL,
    `isPrimary` BOOLEAN NOT NULL DEFAULT true,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `referral_expert_configs_userId_idx`(`userId`),
    INDEX `referral_expert_configs_expertId_idx`(`expertId`),
    INDEX `referral_expert_configs_teamId_idx`(`teamId`),
    INDEX `referral_expert_configs_referralCodeId_idx`(`referralCodeId`),
    UNIQUE INDEX `referral_expert_configs_userId_teamId_expertId_key`(`userId`, `teamId`, `expertId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE IF NOT EXISTS `referral_teams` (
    `id` VARCHAR(191) NOT NULL,
    `teamId` VARCHAR(191) NOT NULL,
    `description` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `referral_teams_teamId_key`(`teamId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE IF NOT EXISTS `referral_records` (
    `id` VARCHAR(191) NOT NULL,
    `referrerId` VARCHAR(191) NOT NULL,
    `referrerCode` VARCHAR(16) NOT NULL,
    `candidateId` VARCHAR(191) NOT NULL,
    `resumeId` VARCHAR(191) NULL,
    `positionId` VARCHAR(191) NOT NULL,
    `expertId` VARCHAR(191) NOT NULL,
    `referralCodeId` VARCHAR(191) NULL,
    `referralType` VARCHAR(32) NOT NULL,
    `referralStatus` VARCHAR(32) NOT NULL DEFAULT 'NORMAL',
    `protectionEndAt` DATETIME(3) NULL,
    `invalidReason` VARCHAR(64) NULL,
    `recommendedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `statusChangedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,
    `applicationId` VARCHAR(191) NULL,

    UNIQUE INDEX `referral_records_applicationId_key`(`applicationId`),
    INDEX `referral_records_referrerId_referralStatus_idx`(`referrerId`, `referralStatus`),
    INDEX `referral_records_expertId_referralStatus_idx`(`expertId`, `referralStatus`),
    INDEX `referral_records_positionId_idx`(`positionId`),
    INDEX `referral_records_protectionEndAt_idx`(`protectionEndAt`),
    INDEX `referral_records_referralStatus_statusChangedAt_idx`(`referralStatus`, `statusChangedAt`),
    INDEX `referral_records_referralCodeId_idx`(`referralCodeId`),
    UNIQUE INDEX `referral_records_candidateId_positionId_referrerId_key`(`candidateId`, `positionId`, `referrerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE IF NOT EXISTS `referral_rewards` (
    `id` VARCHAR(191) NOT NULL,
    `recordId` VARCHAR(191) NOT NULL,
    `candidateId` VARCHAR(191) NOT NULL,
    `amount` DECIMAL(10, 2) NOT NULL,
    `reason` VARCHAR(64) NOT NULL,
    `triggerStage` VARCHAR(32) NOT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    `ruleId` VARCHAR(191) NULL,
    `triggeredAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `confirmedBy` VARCHAR(191) NULL,
    `confirmedAt` DATETIME(3) NULL,
    `issuedAt` DATETIME(3) NULL,
    `rejectedAt` DATETIME(3) NULL,
    `rejectReason` VARCHAR(255) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `referral_rewards_recordId_idx`(`recordId`),
    INDEX `referral_rewards_status_idx`(`status`),
    INDEX `referral_rewards_triggeredAt_idx`(`triggeredAt`),
    INDEX `referral_rewards_candidateId_idx`(`candidateId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE IF NOT EXISTS `referral_rules` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(64) NOT NULL,
    `ruleType` VARCHAR(32) NOT NULL,
    `positionLevel` VARCHAR(32) NULL,
    `triggerStage` VARCHAR(32) NULL,
    `conditions` JSON NOT NULL,
    `amount` DECIMAL(10, 2) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdBy` VARCHAR(191) NOT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `referral_rules_name_key`(`name`),
    INDEX `referral_rules_ruleType_status_idx`(`ruleType`, `status`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_0_referral_codes_userId_fkey;
CREATE PROCEDURE add_fk_0_referral_codes_userId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_codes'
                   AND constraint_name = 'referral_codes_userId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_codes` ADD CONSTRAINT `referral_codes_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_0_referral_codes_userId_fkey();
DROP PROCEDURE add_fk_0_referral_codes_userId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_1_referral_expert_configs_userId_fkey;
CREATE PROCEDURE add_fk_1_referral_expert_configs_userId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_expert_configs'
                   AND constraint_name = 'referral_expert_configs_userId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_1_referral_expert_configs_userId_fkey();
DROP PROCEDURE add_fk_1_referral_expert_configs_userId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_2_referral_expert_configs_teamId_fkey;
CREATE PROCEDURE add_fk_2_referral_expert_configs_teamId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_expert_configs'
                   AND constraint_name = 'referral_expert_configs_teamId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_teamId_fkey` FOREIGN KEY (`teamId`) REFERENCES `departments`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_2_referral_expert_configs_teamId_fkey();
DROP PROCEDURE add_fk_2_referral_expert_configs_teamId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_3_referral_expert_configs_expertId_fkey;
CREATE PROCEDURE add_fk_3_referral_expert_configs_expertId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_expert_configs'
                   AND constraint_name = 'referral_expert_configs_expertId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_expertId_fkey` FOREIGN KEY (`expertId`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_3_referral_expert_configs_expertId_fkey();
DROP PROCEDURE add_fk_3_referral_expert_configs_expertId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_4_referral_expert_configs_referralCodeId_fkey;
CREATE PROCEDURE add_fk_4_referral_expert_configs_referralCodeId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_expert_configs'
                   AND constraint_name = 'referral_expert_configs_referralCodeId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_referralCodeId_fkey` FOREIGN KEY (`referralCodeId`) REFERENCES `referral_codes`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_4_referral_expert_configs_referralCodeId_fkey();
DROP PROCEDURE add_fk_4_referral_expert_configs_referralCodeId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_5_referral_teams_teamId_fkey;
CREATE PROCEDURE add_fk_5_referral_teams_teamId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_teams'
                   AND constraint_name = 'referral_teams_teamId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_teams` ADD CONSTRAINT `referral_teams_teamId_fkey` FOREIGN KEY (`teamId`) REFERENCES `departments`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_5_referral_teams_teamId_fkey();
DROP PROCEDURE add_fk_5_referral_teams_teamId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_6_referral_records_referrerId_fkey;
CREATE PROCEDURE add_fk_6_referral_records_referrerId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_records'
                   AND constraint_name = 'referral_records_referrerId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_referrerId_fkey` FOREIGN KEY (`referrerId`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_6_referral_records_referrerId_fkey();
DROP PROCEDURE add_fk_6_referral_records_referrerId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_7_referral_records_candidateId_fkey;
CREATE PROCEDURE add_fk_7_referral_records_candidateId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_records'
                   AND constraint_name = 'referral_records_candidateId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_candidateId_fkey` FOREIGN KEY (`candidateId`) REFERENCES `candidates`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_7_referral_records_candidateId_fkey();
DROP PROCEDURE add_fk_7_referral_records_candidateId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_8_referral_records_resumeId_fkey;
CREATE PROCEDURE add_fk_8_referral_records_resumeId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_records'
                   AND constraint_name = 'referral_records_resumeId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_resumeId_fkey` FOREIGN KEY (`resumeId`) REFERENCES `resumes`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_8_referral_records_resumeId_fkey();
DROP PROCEDURE add_fk_8_referral_records_resumeId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_9_referral_records_positionId_fkey;
CREATE PROCEDURE add_fk_9_referral_records_positionId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_records'
                   AND constraint_name = 'referral_records_positionId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_positionId_fkey` FOREIGN KEY (`positionId`) REFERENCES `positions`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_9_referral_records_positionId_fkey();
DROP PROCEDURE add_fk_9_referral_records_positionId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_10_referral_records_expertId_fkey;
CREATE PROCEDURE add_fk_10_referral_records_expertId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_records'
                   AND constraint_name = 'referral_records_expertId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_expertId_fkey` FOREIGN KEY (`expertId`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_10_referral_records_expertId_fkey();
DROP PROCEDURE add_fk_10_referral_records_expertId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_11_referral_records_referralCodeId_fkey;
CREATE PROCEDURE add_fk_11_referral_records_referralCodeId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_records'
                   AND constraint_name = 'referral_records_referralCodeId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_referralCodeId_fkey` FOREIGN KEY (`referralCodeId`) REFERENCES `referral_codes`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_11_referral_records_referralCodeId_fkey();
DROP PROCEDURE add_fk_11_referral_records_referralCodeId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_12_referral_records_applicationId_fkey;
CREATE PROCEDURE add_fk_12_referral_records_applicationId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_records'
                   AND constraint_name = 'referral_records_applicationId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_applicationId_fkey` FOREIGN KEY (`applicationId`) REFERENCES `applications`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_12_referral_records_applicationId_fkey();
DROP PROCEDURE add_fk_12_referral_records_applicationId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_13_referral_rewards_recordId_fkey;
CREATE PROCEDURE add_fk_13_referral_rewards_recordId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_rewards'
                   AND constraint_name = 'referral_rewards_recordId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_recordId_fkey` FOREIGN KEY (`recordId`) REFERENCES `referral_records`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_13_referral_rewards_recordId_fkey();
DROP PROCEDURE add_fk_13_referral_rewards_recordId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_14_referral_rewards_candidateId_fkey;
CREATE PROCEDURE add_fk_14_referral_rewards_candidateId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_rewards'
                   AND constraint_name = 'referral_rewards_candidateId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_candidateId_fkey` FOREIGN KEY (`candidateId`) REFERENCES `candidates`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_14_referral_rewards_candidateId_fkey();
DROP PROCEDURE add_fk_14_referral_rewards_candidateId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_15_referral_rewards_ruleId_fkey;
CREATE PROCEDURE add_fk_15_referral_rewards_ruleId_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_rewards'
                   AND constraint_name = 'referral_rewards_ruleId_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_ruleId_fkey` FOREIGN KEY (`ruleId`) REFERENCES `referral_rules`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_15_referral_rewards_ruleId_fkey();
DROP PROCEDURE add_fk_15_referral_rewards_ruleId_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_16_referral_rewards_confirmedBy_fkey;
CREATE PROCEDURE add_fk_16_referral_rewards_confirmedBy_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_rewards'
                   AND constraint_name = 'referral_rewards_confirmedBy_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_confirmedBy_fkey` FOREIGN KEY (`confirmedBy`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_16_referral_rewards_confirmedBy_fkey();
DROP PROCEDURE add_fk_16_referral_rewards_confirmedBy_fkey;

-- AddForeignKey

-- AddForeignKey (guarded: only add if not already present)
DROP PROCEDURE IF EXISTS add_fk_17_referral_rules_createdBy_fkey;
CREATE PROCEDURE add_fk_17_referral_rules_createdBy_fkey()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                 WHERE table_schema = DATABASE()
                   AND table_name = 'referral_rules'
                   AND constraint_name = 'referral_rules_createdBy_fkey'
                   AND constraint_type = 'FOREIGN KEY') THEN
    ALTER TABLE `referral_rules` ADD CONSTRAINT `referral_rules_createdBy_fkey` FOREIGN KEY (`createdBy`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END;
CALL add_fk_17_referral_rules_createdBy_fkey();
DROP PROCEDURE add_fk_17_referral_rules_createdBy_fkey;

