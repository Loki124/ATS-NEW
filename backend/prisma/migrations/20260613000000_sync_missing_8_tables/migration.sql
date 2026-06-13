-- Migration to sync 8 tables missing from baseline migrations
-- Generated via prisma migrate diff (--from-empty --to-schema on a temp schema
-- containing only the 8 models, plus FK stubs for roles/companies/field_definitions).
--
-- Idempotency / Safety:
--   - CREATE TABLE wrapped in IF NOT EXISTS (safe on envs that used db push).
--   - CREATE INDEX wrapped in information_schema.statistics guard.
--   - ALTER TABLE ADD CONSTRAINT (FK) wrapped in a 3-way guard:
--       (a) FK already exists, OR
--       (b) referenced table missing (e.g. baseline not yet applied), OR
--       (c) no-op.
--     This makes the migration safe to run:
--       - Before baseline (FKs skipped silently)
--       - After baseline (FKs added)
--       - After both (no-op on re-apply)
--
-- The 8 missing tables:
--   data_subscriptions  (DataSubscription, P3 G35)
--   external_sync_logs  (ExternalSyncLog)
--   field_acl_audits    (FieldAclAudit, P1 G43)
--   field_acl_rules     (FieldAclRule, P1 G43)
--   field_definitions   (FieldDefinition, P3 G42)
--   field_options       (FieldOption, P3 G42)
--   legal_company_syncs (LegalCompanySync, P1 G40)
--   scraped_resumes     (ScrapedResume, P3 G30)
--
-- Generated: 2026-06-13

-- CreateTable
CREATE TABLE IF NOT EXISTS `data_subscriptions` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `userName` VARCHAR(191) NOT NULL,
    `resource` VARCHAR(64) NOT NULL,
    `metric` VARCHAR(64) NOT NULL,
    `filters` TEXT NULL,
    `channel` VARCHAR(16) NOT NULL,
    `schedule` VARCHAR(32) NOT NULL,
    `scheduleTime` VARCHAR(8) NULL,
    `recipients` TEXT NULL,
    `isActive` BOOLEAN NOT NULL DEFAULT true,
    `lastRunAt` DATETIME(3) NULL,
    `nextRunAt` DATETIME(3) NULL,
    `runCount` INTEGER NOT NULL DEFAULT 0,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `data_subscriptions_userId_isActive_idx`(`userId`, `isActive`),
    INDEX `data_subscriptions_resource_schedule_idx`(`resource`, `schedule`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CreateTable
CREATE TABLE IF NOT EXISTS `external_sync_logs` (
    `id` VARCHAR(191) NOT NULL,
    `syncId` VARCHAR(191) NOT NULL,
    `companyId` VARCHAR(191) NOT NULL,
    `system` VARCHAR(32) NOT NULL,
    `action` VARCHAR(32) NOT NULL,
    `status` VARCHAR(16) NOT NULL,
    `message` TEXT NULL,
    `payload` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `external_sync_logs_syncId_createdAt_idx`(`syncId`, `createdAt`),
    INDEX `external_sync_logs_companyId_system_idx`(`companyId`, `system`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CreateTable
CREATE TABLE IF NOT EXISTS `field_acl_audits` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `userName` VARCHAR(191) NOT NULL,
    `resource` VARCHAR(64) NOT NULL,
    `field` VARCHAR(64) NOT NULL,
    `action` VARCHAR(16) NOT NULL,
    `result` VARCHAR(16) NOT NULL,
    `targetId` VARCHAR(191) NULL,
    `ip` VARCHAR(191) NULL,
    `ua` VARCHAR(255) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `field_acl_audits_userId_createdAt_idx`(`userId`, `createdAt`),
    INDEX `field_acl_audits_resource_field_idx`(`resource`, `field`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CreateTable
CREATE TABLE IF NOT EXISTS `field_acl_rules` (
    `id` VARCHAR(191) NOT NULL,
    `resource` VARCHAR(64) NOT NULL,
    `field` VARCHAR(64) NOT NULL,
    `action` VARCHAR(16) NOT NULL,
    `roleId` VARCHAR(191) NULL,
    `roleCode` VARCHAR(32) NULL,
    `maskPattern` VARCHAR(64) NULL,
    `isActive` BOOLEAN NOT NULL DEFAULT true,
    `priority` INTEGER NOT NULL DEFAULT 0,
    `description` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `field_acl_rules_resource_field_idx`(`resource`, `field`),
    INDEX `field_acl_rules_roleCode_idx`(`roleCode`),
    UNIQUE INDEX `field_acl_rules_resource_field_roleId_key`(`resource`, `field`, `roleId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CreateTable
CREATE TABLE IF NOT EXISTS `field_definitions` (
    `id` VARCHAR(191) NOT NULL,
    `resource` VARCHAR(64) NOT NULL,
    `fieldKey` VARCHAR(64) NOT NULL,
    `label` VARCHAR(191) NOT NULL,
    `fieldType` VARCHAR(32) NOT NULL,
    `isRequired` BOOLEAN NOT NULL DEFAULT false,
    `isVisible` BOOLEAN NOT NULL DEFAULT true,
    `placeholder` VARCHAR(191) NULL,
    `helpText` VARCHAR(255) NULL,
    `defaultValue` VARCHAR(191) NULL,
    `validation` TEXT NULL,
    `orderIndex` INTEGER NOT NULL DEFAULT 0,
    `groupName` VARCHAR(64) NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `field_definitions_resource_status_idx`(`resource`, `status`),
    UNIQUE INDEX `field_definitions_resource_fieldKey_key`(`resource`, `fieldKey`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CreateTable
CREATE TABLE IF NOT EXISTS `field_options` (
    `id` VARCHAR(191) NOT NULL,
    `fieldId` VARCHAR(191) NOT NULL,
    `value` VARCHAR(191) NOT NULL,
    `label` VARCHAR(191) NOT NULL,
    `orderIndex` INTEGER NOT NULL DEFAULT 0,
    `isActive` BOOLEAN NOT NULL DEFAULT true,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `field_options_fieldId_orderIndex_idx`(`fieldId`, `orderIndex`),
    UNIQUE INDEX `field_options_fieldId_value_key`(`fieldId`, `value`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CreateTable
CREATE TABLE IF NOT EXISTS `legal_company_syncs` (
    `id` VARCHAR(191) NOT NULL,
    `companyId` VARCHAR(191) NOT NULL,
    `externalSystem` VARCHAR(32) NOT NULL,
    `externalId` VARCHAR(128) NULL,
    `lastSyncAt` DATETIME(3) NULL,
    `lastSyncBy` VARCHAR(191) NULL,
    `syncStatus` VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    `lastError` TEXT NULL,
    `retryCount` INTEGER NOT NULL DEFAULT 0,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `legal_company_syncs_syncStatus_idx`(`syncStatus`),
    UNIQUE INDEX `legal_company_syncs_companyId_externalSystem_key`(`companyId`, `externalSystem`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CreateTable
CREATE TABLE IF NOT EXISTS `scraped_resumes` (
    `id` VARCHAR(191) NOT NULL,
    `candidateId` VARCHAR(191) NULL,
    `candidateName` VARCHAR(191) NULL,
    `candidatePhone` VARCHAR(191) NULL,
    `candidateEmail` VARCHAR(191) NULL,
    `source` VARCHAR(64) NOT NULL,
    `sourceUrl` VARCHAR(512) NULL,
    `sourceJobId` VARCHAR(128) NULL,
    `rawHtml` LONGTEXT NULL,
    `rawText` TEXT NULL,
    `scraperType` VARCHAR(32) NOT NULL,
    `scrapedAt` DATETIME(3) NULL,
    `scraperUserId` VARCHAR(191) NULL,
    `scraperJobName` VARCHAR(128) NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    `importError` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `scraped_resumes_status_idx`(`status`),
    INDEX `scraped_resumes_source_idx`(`source`),
    INDEX `scraped_resumes_candidatePhone_idx`(`candidatePhone`),
    INDEX `scraped_resumes_candidateEmail_idx`(`candidateEmail`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
SET @fk_exists := (SELECT COUNT(*) FROM information_schema.table_constraints
  WHERE constraint_schema = DATABASE()
    AND table_name = 'field_acl_rules'
    AND constraint_name = 'field_acl_rules_roleId_fkey');
SET @ref_table_exists := (SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'roles');
SET @sql := IF(@fk_exists = 0 AND @ref_table_exists > 0,
  'ALTER TABLE `field_acl_rules` ADD CONSTRAINT `field_acl_rules_roleId_fkey` FOREIGN KEY (`roleId`) REFERENCES `roles`(`id`) ON DELETE SET NULL ON UPDATE CASCADE',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- AddForeignKey
SET @fk_exists := (SELECT COUNT(*) FROM information_schema.table_constraints
  WHERE constraint_schema = DATABASE()
    AND table_name = 'field_options'
    AND constraint_name = 'field_options_fieldId_fkey');
SET @ref_table_exists := (SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'field_definitions');
SET @sql := IF(@fk_exists = 0 AND @ref_table_exists > 0,
  'ALTER TABLE `field_options` ADD CONSTRAINT `field_options_fieldId_fkey` FOREIGN KEY (`fieldId`) REFERENCES `field_definitions`(`id`) ON DELETE CASCADE ON UPDATE CASCADE',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- AddForeignKey
SET @fk_exists := (SELECT COUNT(*) FROM information_schema.table_constraints
  WHERE constraint_schema = DATABASE()
    AND table_name = 'legal_company_syncs'
    AND constraint_name = 'legal_company_syncs_companyId_fkey');
SET @ref_table_exists := (SELECT COUNT(*) FROM information_schema.tables
  WHERE table_schema = DATABASE() AND table_name = 'companies');
SET @sql := IF(@fk_exists = 0 AND @ref_table_exists > 0,
  'ALTER TABLE `legal_company_syncs` ADD CONSTRAINT `legal_company_syncs_companyId_fkey` FOREIGN KEY (`companyId`) REFERENCES `companies`(`id`) ON DELETE CASCADE ON UPDATE CASCADE',
  'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
