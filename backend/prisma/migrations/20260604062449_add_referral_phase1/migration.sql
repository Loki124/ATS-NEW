-- DropIndex
DROP INDEX `applications_referralUserId_idx` ON `applications`;

-- AlterTable
ALTER TABLE `applications` DROP COLUMN `referralUserId`;

-- CreateTable
CREATE TABLE `referral_codes` (
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
CREATE TABLE `referral_expert_configs` (
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
CREATE TABLE `referral_teams` (
    `id` VARCHAR(191) NOT NULL,
    `teamId` VARCHAR(191) NOT NULL,
    `description` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `referral_teams_teamId_key`(`teamId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `referral_records` (
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
CREATE TABLE `referral_rewards` (
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
CREATE TABLE `referral_rules` (
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
ALTER TABLE `referral_codes` ADD CONSTRAINT `referral_codes_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_teamId_fkey` FOREIGN KEY (`teamId`) REFERENCES `departments`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_expertId_fkey` FOREIGN KEY (`expertId`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_expert_configs` ADD CONSTRAINT `referral_expert_configs_referralCodeId_fkey` FOREIGN KEY (`referralCodeId`) REFERENCES `referral_codes`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_teams` ADD CONSTRAINT `referral_teams_teamId_fkey` FOREIGN KEY (`teamId`) REFERENCES `departments`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_referrerId_fkey` FOREIGN KEY (`referrerId`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_candidateId_fkey` FOREIGN KEY (`candidateId`) REFERENCES `candidates`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_resumeId_fkey` FOREIGN KEY (`resumeId`) REFERENCES `resumes`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_positionId_fkey` FOREIGN KEY (`positionId`) REFERENCES `positions`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_expertId_fkey` FOREIGN KEY (`expertId`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_referralCodeId_fkey` FOREIGN KEY (`referralCodeId`) REFERENCES `referral_codes`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_records` ADD CONSTRAINT `referral_records_applicationId_fkey` FOREIGN KEY (`applicationId`) REFERENCES `applications`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_recordId_fkey` FOREIGN KEY (`recordId`) REFERENCES `referral_records`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_candidateId_fkey` FOREIGN KEY (`candidateId`) REFERENCES `candidates`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_ruleId_fkey` FOREIGN KEY (`ruleId`) REFERENCES `referral_rules`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_rewards` ADD CONSTRAINT `referral_rewards_confirmedBy_fkey` FOREIGN KEY (`confirmedBy`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `referral_rules` ADD CONSTRAINT `referral_rules_createdBy_fkey` FOREIGN KEY (`createdBy`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

