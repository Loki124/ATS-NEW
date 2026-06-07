-- CreateTable
CREATE TABLE `resume_lock_records` (
    `id` VARCHAR(191) NOT NULL,
    `resumeId` VARCHAR(191) NOT NULL,
    `lockerId` VARCHAR(191) NOT NULL,
    `lockType` VARCHAR(191) NOT NULL,
    `effectiveTime` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `expireTime` DATETIME(3) NULL,
    `isActive` BOOLEAN NOT NULL DEFAULT true,
    `source` VARCHAR(191) NOT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `resume_lock_records_resumeId_isActive_idx`(`resumeId`, `isActive`),
    INDEX `resume_lock_records_lockerId_idx`(`lockerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `special_resume_tags` (
    `id` VARCHAR(191) NOT NULL,
    `resumeId` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NULL,
    `tagName` VARCHAR(191) NOT NULL DEFAULT '特殊简历',
    `approvalId` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `special_resume_tags_resumeId_idx`(`resumeId`),
    UNIQUE INDEX `special_resume_tags_resumeId_positionId_key`(`resumeId`, `positionId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `resume_merge_records` (
    `id` VARCHAR(191) NOT NULL,
    `mainResumeId` VARCHAR(191) NOT NULL,
    `mergedResumeId` VARCHAR(191) NOT NULL,
    `mergeType` VARCHAR(191) NOT NULL,
    `operatorId` VARCHAR(191) NULL,
    `mergeReason` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `resume_merge_records_operatorId_idx`(`operatorId`),
    UNIQUE INDEX `resume_merge_records_mergedResumeId_key`(`mergedResumeId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `special_approval_flows` (
    `id` VARCHAR(191) NOT NULL,
    `resumeId` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NOT NULL,
    `flowType` VARCHAR(32) NOT NULL DEFAULT 'SPECIAL_RESUME',
    `status` VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    `currentNodeId` VARCHAR(191) NULL,
    `nodes` TEXT NOT NULL,
    `result` VARCHAR(191) NULL,
    `resultComment` VARCHAR(191) NULL,
    `decidedAt` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `special_approval_flows_resumeId_status_idx`(`resumeId`, `status`),
    INDEX `special_approval_flows_currentNodeId_idx`(`currentNodeId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `async_scoring_tasks` (
    `id` VARCHAR(191) NOT NULL,
    `resumeId` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NOT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    `matchScore` INTEGER NULL,
    `matchDetails` TEXT NULL,
    `errorMessage` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `completedAt` DATETIME(3) NULL,

    INDEX `async_scoring_tasks_resumeId_status_idx`(`resumeId`, `status`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `resume_flow_logs` (
    `id` VARCHAR(191) NOT NULL,
    `resumeId` VARCHAR(191) NOT NULL,
    `candidateId` VARCHAR(191) NOT NULL,
    `action` VARCHAR(191) NOT NULL,
    `operatorId` VARCHAR(191) NULL,
    `operatorName` VARCHAR(191) NULL,
    `fromStatus` VARCHAR(191) NULL,
    `toStatus` VARCHAR(191) NULL,
    `positionId` VARCHAR(191) NULL,
    `positionName` VARCHAR(191) NULL,
    `detail` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `resume_flow_logs_resumeId_idx`(`resumeId`),
    INDEX `resume_flow_logs_candidateId_idx`(`candidateId`),
    INDEX `resume_flow_logs_operatorId_idx`(`operatorId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `users` (
    `id` VARCHAR(191) NOT NULL,
    `username` VARCHAR(191) NOT NULL,
    `password` VARCHAR(191) NOT NULL,
    `realName` VARCHAR(191) NOT NULL,
    `email` VARCHAR(191) NULL,
    `phone` VARCHAR(191) NULL,
    `avatar` VARCHAR(191) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `roleType` VARCHAR(32) NOT NULL DEFAULT 'HR',
    `departmentId` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,
    `lastLoginAt` DATETIME(3) NULL,
    `wechatWorkUserId` VARCHAR(191) NULL,
    `wechatWorkDeptId` VARCHAR(191) NULL,
    `wechatWorkName` VARCHAR(191) NULL,
    `mochaUserId` VARCHAR(191) NULL,
    `mochaDeptId` VARCHAR(191) NULL,
    `mochaName` VARCHAR(191) NULL,
    `permissionMode` VARCHAR(32) NOT NULL DEFAULT 'MOU',

    UNIQUE INDEX `users_username_key`(`username`),
    UNIQUE INDEX `users_email_key`(`email`),
    UNIQUE INDEX `users_phone_key`(`phone`),
    INDEX `users_departmentId_idx`(`departmentId`),
    INDEX `users_wechatWorkUserId_idx`(`wechatWorkUserId`),
    INDEX `users_wechatWorkDeptId_idx`(`wechatWorkDeptId`),
    INDEX `users_mochaUserId_idx`(`mochaUserId`),
    INDEX `users_mochaDeptId_idx`(`mochaDeptId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `departments` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `parentId` VARCHAR(191) NULL,
    `level` INTEGER NOT NULL DEFAULT 1,
    `path` VARCHAR(191) NOT NULL,
    `managerId` VARCHAR(191) NULL,
    `manager2Id` VARCHAR(191) NULL,
    `manager3Id` VARCHAR(191) NULL,
    `hrbpId` VARCHAR(191) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `sortOrder` INTEGER NOT NULL DEFAULT 0,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `departments_code_key`(`code`),
    INDEX `departments_parentId_idx`(`parentId`),
    INDEX `departments_managerId_idx`(`managerId`),
    INDEX `departments_manager2Id_idx`(`manager2Id`),
    INDEX `departments_manager3Id_idx`(`manager3Id`),
    INDEX `departments_hrbpId_idx`(`hrbpId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `recruitment_processes` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `description` TEXT NULL,
    `applicableRange` VARCHAR(191) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,
    `applicableDepartments` JSON NULL,
    `applicablePositionLevels` JSON NULL,
    `applicableUserIds` JSON NULL,
    `applicableJobs` JSON NULL,
    `applicableMode` VARCHAR(16) NOT NULL DEFAULT 'ALL',
    `validateResumeScore` BOOLEAN NOT NULL DEFAULT true,
    `failPrompt` TEXT NULL,
    `createdBy` VARCHAR(191) NULL,
    `updatedBy` VARCHAR(191) NULL,

    UNIQUE INDEX `recruitment_processes_code_key`(`code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `recruitment_stages` (
    `id` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `stageType` VARCHAR(32) NOT NULL,
    `stageLimit` INTEGER NULL,
    `features` JSON NOT NULL,
    `isSystem` BOOLEAN NOT NULL DEFAULT false,
    `description` TEXT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `recruitment_stages_code_key`(`code`),
    INDEX `recruitment_stages_stageType_status_idx`(`stageType`, `status`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `process_stage_links` (
    `id` VARCHAR(191) NOT NULL,
    `processId` VARCHAR(191) NOT NULL,
    `stageId` VARCHAR(191) NOT NULL,
    `orderIndex` INTEGER NOT NULL DEFAULT 0,
    `customName` VARCHAR(64) NULL,
    `isStart` BOOLEAN NOT NULL DEFAULT false,
    `isEnd` BOOLEAN NOT NULL DEFAULT false,
    `stageLimit` INTEGER NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `process_stage_links_processId_orderIndex_idx`(`processId`, `orderIndex`),
    UNIQUE INDEX `process_stage_links_processId_stageId_key`(`processId`, `stageId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `demands` (
    `id` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `departmentId` VARCHAR(191) NOT NULL,
    `positionCount` INTEGER NOT NULL DEFAULT 1,
    `hiredCount` INTEGER NOT NULL DEFAULT 0,
    `onBoardCount` INTEGER NOT NULL DEFAULT 0,
    `demandType` VARCHAR(32) NOT NULL,
    `demandStatus` VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    `approvalStatus` VARCHAR(32) NOT NULL DEFAULT 'NOT_STARTED',
    `creatorId` VARCHAR(191) NOT NULL,
    `managerId` VARCHAR(191) NULL,
    `assistantIds` VARCHAR(191) NULL,
    `managerIds` VARCHAR(191) NULL,
    `managerSuperIds` VARCHAR(191) NULL,
    `hrbpId` VARCHAR(191) NULL,
    `positionSeries` VARCHAR(32) NULL,
    `jobTitle` VARCHAR(191) NULL,
    `jobLevel` VARCHAR(32) NULL,
    `startDate` DATETIME(3) NULL,
    `endDate` DATETIME(3) NULL,
    `salaryMin` INTEGER NULL,
    `salaryMax` INTEGER NULL,
    `description` TEXT NULL,
    `requirements` TEXT NULL,
    `attachments` TEXT NULL,
    `trialGoals` VARCHAR(191) NULL,
    `talentLevel` VARCHAR(32) NULL,
    `isDoubleA` BOOLEAN NOT NULL DEFAULT false,
    `biddingMode` VARCHAR(32) NOT NULL DEFAULT 'BIDDING',
    `biddingAmount` DECIMAL(12, 2) NULL,
    `biddingUnit` VARCHAR(32) NULL,
    `biddingTalentLevels` VARCHAR(191) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `demands_code_key`(`code`),
    INDEX `demands_departmentId_idx`(`departmentId`),
    INDEX `demands_creatorId_idx`(`creatorId`),
    INDEX `demands_managerId_idx`(`managerId`),
    INDEX `demands_hrbpId_idx`(`hrbpId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `demand_approval_steps` (
    `id` VARCHAR(191) NOT NULL,
    `demandId` VARCHAR(191) NOT NULL,
    `stepIndex` INTEGER NOT NULL,
    `approverRole` VARCHAR(32) NOT NULL,
    `approverId` VARCHAR(191) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'WAITING',
    `comment` TEXT NULL,
    `approvedAt` DATETIME(3) NULL,
    `submittedBy` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `demand_approval_steps_demandId_status_idx`(`demandId`, `status`),
    INDEX `demand_approval_steps_approverId_status_idx`(`approverId`, `status`),
    UNIQUE INDEX `demand_approval_steps_demandId_stepIndex_key`(`demandId`, `stepIndex`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `notification_queues` (
    `id` VARCHAR(191) NOT NULL,
    `recipientId` VARCHAR(191) NOT NULL,
    `templateKey` VARCHAR(64) NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `content` TEXT NOT NULL,
    `context` JSON NULL,
    `priority` VARCHAR(16) NOT NULL DEFAULT 'NORMAL',
    `status` VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    `readAt` DATETIME(3) NULL,
    `sentAt` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `notification_queues_recipientId_status_idx`(`recipientId`, `status`),
    INDEX `notification_queues_status_priority_idx`(`status`, `priority`),
    INDEX `notification_queues_createdAt_idx`(`createdAt`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `notification_templates` (
    `id` VARCHAR(191) NOT NULL,
    `templateKey` VARCHAR(64) NOT NULL,
    `name` VARCHAR(128) NOT NULL,
    `channel` VARCHAR(16) NOT NULL DEFAULT 'SYSTEM',
    `category` VARCHAR(32) NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `content` TEXT NOT NULL,
    `variables` JSON NULL,
    `isActive` BOOLEAN NOT NULL DEFAULT true,
    `description` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `notification_templates_templateKey_key`(`templateKey`),
    INDEX `notification_templates_category_isActive_idx`(`category`, `isActive`),
    INDEX `notification_templates_channel_isActive_idx`(`channel`, `isActive`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `demand_status_history` (
    `id` VARCHAR(191) NOT NULL,
    `demandId` VARCHAR(191) NOT NULL,
    `fromStatus` VARCHAR(32) NULL,
    `toStatus` VARCHAR(32) NOT NULL,
    `reason` TEXT NULL,
    `operatorId` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `demand_status_history_demandId_createdAt_idx`(`demandId`, `createdAt`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `demand_approval_configs` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(128) NOT NULL,
    `departmentId` VARCHAR(191) NULL,
    `positionLevel` VARCHAR(32) NULL,
    `minAmount` INTEGER NULL,
    `maxAmount` INTEGER NULL,
    `steps` JSON NOT NULL,
    `isActive` BOOLEAN NOT NULL DEFAULT true,
    `priority` INTEGER NOT NULL DEFAULT 0,
    `description` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `demand_approval_configs_departmentId_positionLevel_isActive_idx`(`departmentId`, `positionLevel`, `isActive`),
    INDEX `demand_approval_configs_isActive_priority_idx`(`isActive`, `priority`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `positions` (
    `id` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `departmentId` VARCHAR(191) NOT NULL,
    `demandId` VARCHAR(191) NULL,
    `creatorId` VARCHAR(191) NOT NULL,
    `managerId` VARCHAR(191) NULL,
    `assistantIds` VARCHAR(191) NULL,
    `managerIds` VARCHAR(191) NULL,
    `managerSuperIds` VARCHAR(191) NULL,
    `priority` INTEGER NOT NULL DEFAULT 0,
    `positionNature` VARCHAR(32) NULL,
    `positionSeries` VARCHAR(32) NULL,
    `description` TEXT NULL,
    `requirements` TEXT NULL,
    `processId` VARCHAR(191) NULL,
    `companyId` VARCHAR(191) NULL,
    `positionStatus` VARCHAR(32) NOT NULL DEFAULT 'RECRUITING',
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `candidateCount` INTEGER NOT NULL DEFAULT 0,
    `hiredCount` INTEGER NOT NULL DEFAULT 0,
    `publishedAt` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `positions_code_key`(`code`),
    INDEX `positions_departmentId_idx`(`departmentId`),
    INDEX `positions_demandId_idx`(`demandId`),
    INDEX `positions_creatorId_idx`(`creatorId`),
    INDEX `positions_managerId_idx`(`managerId`),
    INDEX `positions_processId_idx`(`processId`),
    INDEX `positions_companyId_idx`(`companyId`),
    INDEX `positions_positionStatus_idx`(`positionStatus`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `position_status_history` (
    `id` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NOT NULL,
    `fromStatus` VARCHAR(32) NULL,
    `toStatus` VARCHAR(32) NOT NULL,
    `reason` TEXT NULL,
    `operatorId` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `position_status_history_positionId_createdAt_idx`(`positionId`, `createdAt`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `position_channels` (
    `id` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NOT NULL,
    `channelType` VARCHAR(32) NOT NULL,
    `channelAccount` VARCHAR(191) NULL,
    `publishStatus` VARCHAR(191) NOT NULL DEFAULT 'NOT_PUBLISHED',
    `publishUrl` VARCHAR(191) NULL,
    `publishedAt` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `position_channels_positionId_idx`(`positionId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `candidates` (
    `id` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `gender` VARCHAR(32) NULL,
    `birthday` DATETIME(3) NULL,
    `phone` VARCHAR(191) NULL,
    `email` VARCHAR(191) NULL,
    `householdLocation` VARCHAR(191) NULL,
    `originLocation` VARCHAR(191) NULL,
    `maritalStatus` VARCHAR(32) NULL,
    `childStatus` VARCHAR(32) NULL,
    `highestEducation` VARCHAR(191) NULL,
    `firstEducation` VARCHAR(191) NULL,
    `firstEducationDuration` INTEGER NULL,
    `firstEducationSchoolType` VARCHAR(191) NULL,
    `workExperience` VARCHAR(191) NULL,
    `jobHoppingRate` INTEGER NULL,
    `lastJobDuration` INTEGER NULL,
    `educationForm` VARCHAR(32) NULL,
    `expectedSalaryMin` INTEGER NULL,
    `expectedSalaryMax` INTEGER NULL,
    `expectedPosition` VARCHAR(191) NULL,
    `intendedJoinDate` DATETIME(3) NULL,
    `channelSource` VARCHAR(191) NULL,
    `channelLink` VARCHAR(191) NULL,
    `recommenderId` VARCHAR(191) NULL,
    `recommenderName` VARCHAR(191) NULL,
    `assignedUserId` VARCHAR(191) NULL,
    `resumeProviderId` VARCHAR(191) NULL,
    `candidateStatus` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `archiveReason` VARCHAR(191) NULL,
    `archiveType` VARCHAR(32) NULL,
    `archiveToPool` VARCHAR(191) NULL,
    `protectionExpiry` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `candidates_code_key`(`code`),
    INDEX `candidates_recommenderId_idx`(`recommenderId`),
    INDEX `candidates_assignedUserId_idx`(`assignedUserId`),
    INDEX `candidates_resumeProviderId_idx`(`resumeProviderId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `resumes` (
    `id` VARCHAR(191) NOT NULL,
    `candidateId` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NULL,
    `name` VARCHAR(191) NOT NULL,
    `fileName` VARCHAR(191) NOT NULL,
    `filePath` VARCHAR(191) NOT NULL,
    `fileType` VARCHAR(191) NOT NULL,
    `fileSize` INTEGER NOT NULL,
    `parsedData` TEXT NULL,
    `source` VARCHAR(32) NOT NULL,
    `uploadLocation` VARCHAR(191) NULL,
    `providerId` VARCHAR(191) NULL,
    `uploaderId` VARCHAR(191) NULL,
    `channelSource` VARCHAR(191) NULL,
    `channelLink` VARCHAR(191) NULL,
    `resumeStatus` VARCHAR(32) NOT NULL DEFAULT 'PENDING_ASSIGN',
    `resumeSubStatus` VARCHAR(191) NULL,
    `parseStatus` VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    `duplicateStatus` VARCHAR(32) NOT NULL DEFAULT 'NOT_DUPLICATE',
    `duplicateOfId` VARCHAR(191) NULL,
    `formalLockerId` VARCHAR(191) NULL,
    `tempLockerId` VARCHAR(191) NULL,
    `tempLockerExpireTime` DATETIME(3) NULL,
    `matchScore` INTEGER NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `resumes_candidateId_idx`(`candidateId`),
    INDEX `resumes_positionId_idx`(`positionId`),
    INDEX `resumes_duplicateOfId_idx`(`duplicateOfId`),
    INDEX `resumes_formalLockerId_idx`(`formalLockerId`),
    INDEX `resumes_tempLockerId_idx`(`tempLockerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `applications` (
    `id` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `candidateId` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NOT NULL,
    `resumeId` VARCHAR(191) NULL,
    `currentStageId` VARCHAR(191) NULL,
    `currentStageName` VARCHAR(191) NULL,
    `currentStageStatus` VARCHAR(191) NOT NULL DEFAULT 'IN_PROGRESS',
    `processId` VARCHAR(191) NOT NULL,
    `processName` VARCHAR(191) NOT NULL,
    `source` VARCHAR(191) NULL,
    `applicationStatus` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `archiveReason` VARCHAR(191) NULL,
    `archivedAt` DATETIME(3) NULL,
    `formalLockerId` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `applications_code_key`(`code`),
    INDEX `applications_candidateId_idx`(`candidateId`),
    INDEX `applications_positionId_idx`(`positionId`),
    INDEX `applications_resumeId_idx`(`resumeId`),
    INDEX `applications_currentStageId_idx`(`currentStageId`),
    INDEX `applications_processId_idx`(`processId`),
    INDEX `applications_formalLockerId_idx`(`formalLockerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `interviews` (
    `id` VARCHAR(191) NOT NULL,
    `applicationId` VARCHAR(191) NOT NULL,
    `roundId` VARCHAR(191) NULL,
    `roundName` VARCHAR(191) NULL,
    `interviewType` VARCHAR(32) NOT NULL,
    `interviewDate` DATETIME(3) NOT NULL,
    `duration` INTEGER NOT NULL DEFAULT 60,
    `location` VARCHAR(191) NULL,
    `meetingLink` VARCHAR(191) NULL,
    `interviewerIds` VARCHAR(191) NULL,
    `interviewerNames` VARCHAR(191) NULL,
    `arrangerId` VARCHAR(191) NOT NULL,
    `arrangerName` VARCHAR(191) NOT NULL,
    `interviewStatus` VARCHAR(32) NOT NULL DEFAULT 'SCHEDULED',
    `feedbackStatus` VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    `cancelReason` VARCHAR(191) NULL,
    `cancelNote` VARCHAR(191) NULL,
    `proposedTimes` VARCHAR(191) NULL,
    `confirmedTime` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `interviews_applicationId_idx`(`applicationId`),
    INDEX `interviews_roundId_idx`(`roundId`),
    INDEX `interviews_arrangerId_idx`(`arrangerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `interview_feedbacks` (
    `id` VARCHAR(191) NOT NULL,
    `interviewId` VARCHAR(191) NOT NULL,
    `interviewerId` VARCHAR(191) NOT NULL,
    `interviewerName` VARCHAR(191) NOT NULL,
    `result` VARCHAR(32) NOT NULL,
    `reason` VARCHAR(191) NULL,
    `values` VARCHAR(191) NULL,
    `comprehensive` VARCHAR(191) NULL,
    `recommendation` VARCHAR(191) NULL,
    `participantFeedback` VARCHAR(191) NULL,
    `previousFeedback` VARCHAR(191) NULL,
    `viewedPrevious` BOOLEAN NOT NULL DEFAULT false,
    `feedbackAt` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `interview_feedbacks_interviewId_idx`(`interviewId`),
    INDEX `interview_feedbacks_interviewerId_idx`(`interviewerId`),
    UNIQUE INDEX `interview_feedbacks_interviewId_interviewerId_key`(`interviewId`, `interviewerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `offers` (
    `id` VARCHAR(191) NOT NULL,
    `applicationId` VARCHAR(191) NOT NULL,
    `demandId` VARCHAR(191) NULL,
    `positionSeries` VARCHAR(32) NULL,
    `positionManagerId` VARCHAR(191) NULL,
    `offerManagerId` VARCHAR(191) NULL,
    `expectedJoinDate` DATETIME(3) NOT NULL,
    `reportLocation` VARCHAR(191) NULL,
    `workLocation` VARCHAR(191) NULL,
    `onboardDepartment` VARCHAR(191) NULL,
    `isDoubleDepartment` BOOLEAN NOT NULL DEFAULT false,
    `jobTitle` VARCHAR(191) NULL,
    `jobLevel` VARCHAR(32) NULL,
    `directLeader` VARCHAR(191) NULL,
    `thoughtLeader` VARCHAR(191) NULL,
    `dottedLeader` VARCHAR(191) NULL,
    `employeeType` VARCHAR(32) NULL,
    `businessType` VARCHAR(32) NULL,
    `talentLevel` VARCHAR(32) NULL,
    `costSharing` BOOLEAN NOT NULL DEFAULT false,
    `trialMonths` INTEGER NULL,
    `contractType` VARCHAR(32) NULL,
    `contractPeriod` VARCHAR(191) NULL,
    `legalCompany` VARCHAR(191) NULL,
    `lastYearAvgSalary` DECIMAL(12, 2) NULL,
    `salaryPlan` VARCHAR(191) NULL,
    `baseSalaryTrial` DECIMAL(12, 2) NULL,
    `baseSalaryFormal` DECIMAL(12, 2) NULL,
    `levelSalaryTrial` DECIMAL(12, 2) NULL,
    `levelSalaryFormal` DECIMAL(12, 2) NULL,
    `performanceTrial` DECIMAL(12, 2) NULL,
    `performanceFormal` DECIMAL(12, 2) NULL,
    `housingSubsidyTrial` DECIMAL(12, 2) NULL,
    `housingSubsidyFormal` DECIMAL(12, 2) NULL,
    `attendanceBonusTrial` DECIMAL(12, 2) NULL,
    `attendanceBonusFormal` DECIMAL(12, 2) NULL,
    `commissionTrial` DECIMAL(12, 2) NULL,
    `commissionFormal` DECIMAL(12, 2) NULL,
    `attachments` TEXT NULL,
    `offerStatus` VARCHAR(32) NOT NULL DEFAULT 'NOT_CREATED',
    `sentAt` DATETIME(3) NULL,
    `senderId` VARCHAR(191) NULL,
    `ccUsers` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `offers_applicationId_key`(`applicationId`),
    INDEX `offers_demandId_idx`(`demandId`),
    INDEX `offers_positionManagerId_idx`(`positionManagerId`),
    INDEX `offers_offerManagerId_idx`(`offerManagerId`),
    INDEX `offers_senderId_idx`(`senderId`),
    INDEX `offers_offerStatus_idx`(`offerStatus`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `offer_status_history` (
    `id` VARCHAR(191) NOT NULL,
    `offerId` VARCHAR(191) NOT NULL,
    `fromStatus` VARCHAR(32) NULL,
    `toStatus` VARCHAR(32) NOT NULL,
    `reason` TEXT NULL,
    `operatorId` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `offer_status_history_offerId_createdAt_idx`(`offerId`, `createdAt`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `background_check_records` (
    `id` VARCHAR(191) NOT NULL,
    `offerId` VARCHAR(191) NOT NULL,
    `checkType` VARCHAR(191) NOT NULL,
    `result` VARCHAR(191) NULL,
    `report` VARCHAR(191) NULL,
    `note` VARCHAR(191) NULL,
    `supplier` VARCHAR(191) NULL,
    `orderedAt` DATETIME(3) NULL,
    `authorizedAt` DATETIME(3) NULL,
    `completedAt` DATETIME(3) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `isSupplement` BOOLEAN NOT NULL DEFAULT false,
    `supplementOfId` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `background_check_records_offerId_idx`(`offerId`),
    INDEX `background_check_records_supplementOfId_idx`(`supplementOfId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `candidate_offer_feedbacks` (
    `id` VARCHAR(191) NOT NULL,
    `offerId` VARCHAR(191) NOT NULL,
    `feedback` VARCHAR(32) NOT NULL,
    `respondedAt` DATETIME(3) NULL,

    UNIQUE INDEX `candidate_offer_feedbacks_offerId_key`(`offerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `onboardings` (
    `id` VARCHAR(191) NOT NULL,
    `applicationId` VARCHAR(191) NOT NULL,
    `demandId` VARCHAR(191) NULL,
    `positionSeries` VARCHAR(32) NULL,
    `positionManagerId` VARCHAR(191) NULL,
    `offerManagerId` VARCHAR(191) NULL,
    `expectedJoinDate` DATETIME(3) NOT NULL,
    `reportLocation` VARCHAR(191) NULL,
    `workLocation` VARCHAR(191) NULL,
    `onboardDepartment` VARCHAR(191) NULL,
    `isDoubleDepartment` BOOLEAN NOT NULL DEFAULT false,
    `jobTitle` VARCHAR(191) NULL,
    `jobLevel` VARCHAR(32) NULL,
    `directLeader` VARCHAR(191) NULL,
    `thoughtLeader` VARCHAR(191) NULL,
    `dottedLeader` VARCHAR(191) NULL,
    `employeeType` VARCHAR(32) NULL,
    `businessType` VARCHAR(32) NULL,
    `talentLevel` VARCHAR(32) NULL,
    `costSharing` BOOLEAN NOT NULL DEFAULT false,
    `trialMonths` INTEGER NULL,
    `contractType` VARCHAR(32) NULL,
    `contractPeriod` VARCHAR(191) NULL,
    `legalCompany` VARCHAR(191) NULL,
    `lastYearAvgSalary` DECIMAL(12, 2) NULL,
    `referrerId` VARCHAR(191) NULL,
    `officeSupplies` VARCHAR(191) NULL,
    `salaryPlan` VARCHAR(191) NULL,
    `baseSalaryTrial` DECIMAL(12, 2) NULL,
    `baseSalaryFormal` DECIMAL(12, 2) NULL,
    `levelSalaryTrial` DECIMAL(12, 2) NULL,
    `levelSalaryFormal` DECIMAL(12, 2) NULL,
    `performanceTrial` DECIMAL(12, 2) NULL,
    `performanceFormal` DECIMAL(12, 2) NULL,
    `housingSubsidyTrial` DECIMAL(12, 2) NULL,
    `housingSubsidyFormal` DECIMAL(12, 2) NULL,
    `attendanceBonusTrial` DECIMAL(12, 2) NULL,
    `attendanceBonusFormal` DECIMAL(12, 2) NULL,
    `commissionTrial` DECIMAL(12, 2) NULL,
    `commissionFormal` DECIMAL(65, 30) NULL,
    `attachments` TEXT NULL,
    `onboardingStatus` VARCHAR(32) NOT NULL DEFAULT 'NOT_STARTED',
    `approvalStatus` VARCHAR(32) NOT NULL DEFAULT 'NOT_STARTED',
    `approvalRecordId` VARCHAR(191) NULL,
    `peopleOnboardId` VARCHAR(191) NULL,
    `syncStatus` VARCHAR(32) NULL,
    `cancelReason` VARCHAR(191) NULL,
    `cancelNote` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,
    `onboardedAt` DATETIME(3) NULL,

    UNIQUE INDEX `onboardings_applicationId_key`(`applicationId`),
    INDEX `onboardings_demandId_idx`(`demandId`),
    INDEX `onboardings_positionManagerId_idx`(`positionManagerId`),
    INDEX `onboardings_offerManagerId_idx`(`offerManagerId`),
    INDEX `onboardings_referrerId_idx`(`referrerId`),
    INDEX `onboardings_approvalRecordId_idx`(`approvalRecordId`),
    INDEX `onboardings_peopleOnboardId_idx`(`peopleOnboardId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `invitation_records` (
    `id` VARCHAR(191) NOT NULL,
    `applicationId` VARCHAR(191) NOT NULL,
    `candidateId` VARCHAR(191) NOT NULL,
    `positionId` VARCHAR(191) NOT NULL,
    `ownerId` VARCHAR(191) NOT NULL,
    `ownerName` VARCHAR(191) NOT NULL,
    `inviterId` VARCHAR(191) NULL,
    `inviterName` VARCHAR(191) NULL,
    `assignType` VARCHAR(32) NOT NULL,
    `assignedAt` DATETIME(3) NULL,
    `invitationStatus` VARCHAR(32) NOT NULL DEFAULT 'PENDING_ASSIGN',
    `claimedAt` DATETIME(3) NULL,
    `claimedById` VARCHAR(191) NULL,
    `claimedByName` VARCHAR(191) NULL,
    `contactAttempts` INTEGER NOT NULL DEFAULT 0,
    `lastContactAt` DATETIME(3) NULL,
    `tags` VARCHAR(191) NULL,
    `note` VARCHAR(191) NULL,
    `interventionCount` INTEGER NOT NULL DEFAULT 0,
    `lastInterventionBy` VARCHAR(191) NULL,
    `biddingAmount` DECIMAL(12, 2) NULL,
    `resultStatus` VARCHAR(32) NULL,
    `resultReason` VARCHAR(191) NULL,
    `resultAt` DATETIME(3) NULL,
    `timeoutAt` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `invitation_records_applicationId_key`(`applicationId`),
    INDEX `invitation_records_candidateId_idx`(`candidateId`),
    INDEX `invitation_records_positionId_idx`(`positionId`),
    INDEX `invitation_records_ownerId_idx`(`ownerId`),
    INDEX `invitation_records_inviterId_idx`(`inviterId`),
    INDEX `invitation_records_claimedById_idx`(`claimedById`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `notifications` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `type` VARCHAR(32) NOT NULL,
    `title` VARCHAR(191) NOT NULL,
    `content` TEXT NOT NULL,
    `data` VARCHAR(191) NULL,
    `readStatus` VARCHAR(32) NOT NULL DEFAULT 'UNREAD',
    `readAt` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `notifications_userId_idx`(`userId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `operation_records` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `userName` VARCHAR(191) NOT NULL,
    `operationType` VARCHAR(32) NOT NULL,
    `targetType` VARCHAR(191) NOT NULL,
    `targetId` VARCHAR(191) NOT NULL,
    `targetName` VARCHAR(191) NULL,
    `detail` VARCHAR(191) NULL,
    `beforeValue` VARCHAR(191) NULL,
    `afterValue` VARCHAR(191) NULL,
    `ipAddress` VARCHAR(191) NULL,
    `userAgent` VARCHAR(191) NULL,
    `metadata` JSON NULL,
    `reason` TEXT NULL,
    `fromState` VARCHAR(32) NULL,
    `toState` VARCHAR(32) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `operation_records_userId_idx`(`userId`),
    INDEX `operation_records_targetId_idx`(`targetId`),
    INDEX `operation_records_targetType_targetId_createdAt_idx`(`targetType`, `targetId`, `createdAt`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `dictionaries` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `description` TEXT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `dictionaries_code_key`(`code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `dictionary_items` (
    `id` VARCHAR(191) NOT NULL,
    `dictionaryId` VARCHAR(191) NOT NULL,
    `parentId` VARCHAR(191) NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `value` VARCHAR(191) NULL,
    `description` TEXT NULL,
    `sortOrder` INTEGER NOT NULL DEFAULT 0,
    `level` INTEGER NOT NULL DEFAULT 1,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `dictionary_items_dictionaryId_idx`(`dictionaryId`),
    INDEX `dictionary_items_parentId_idx`(`parentId`),
    UNIQUE INDEX `dictionary_items_dictionaryId_code_key`(`dictionaryId`, `code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `companies` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `parentCompanyId` VARCHAR(191) NULL,
    `isBenchmark` BOOLEAN NOT NULL DEFAULT false,
    `industry` VARCHAR(191) NULL,
    `scale` VARCHAR(32) NULL,
    `description` TEXT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `companies_code_key`(`code`),
    INDEX `companies_parentCompanyId_idx`(`parentCompanyId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `schools` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `location` VARCHAR(191) NULL,
    `province` VARCHAR(191) NULL,
    `city` VARCHAR(191) NULL,
    `educationLevel` VARCHAR(32) NULL,
    `schoolType` VARCHAR(32) NULL,
    `schoolCategory` VARCHAR(32) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `schools_code_key`(`code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `company_addresses` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `country` VARCHAR(191) NOT NULL DEFAULT '中国',
    `province` VARCHAR(191) NOT NULL,
    `city` VARCHAR(191) NOT NULL,
    `district` VARCHAR(191) NULL,
    `address` VARCHAR(191) NOT NULL,
    `longitude` DOUBLE NULL,
    `latitude` DOUBLE NULL,
    `isLocated` BOOLEAN NOT NULL DEFAULT false,
    `contactPhone` VARCHAR(191) NULL,
    `contactEmail` VARCHAR(191) NULL,
    `companyType` VARCHAR(32) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `scoring_rules` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `description` TEXT NULL,
    `ruleType` VARCHAR(32) NOT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,
    `applicableRange` VARCHAR(191) NULL,

    UNIQUE INDEX `scoring_rules_code_key`(`code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `scoring_conditions` (
    `id` VARCHAR(191) NOT NULL,
    `ruleId` VARCHAR(191) NOT NULL,
    `field` VARCHAR(191) NOT NULL,
    `operator` VARCHAR(191) NOT NULL,
    `value` VARCHAR(191) NOT NULL,
    `level` INTEGER NOT NULL DEFAULT 1,
    `logicType` VARCHAR(191) NOT NULL DEFAULT 'AND',

    INDEX `scoring_conditions_ruleId_idx`(`ruleId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `scoring_results` (
    `id` VARCHAR(191) NOT NULL,
    `ruleId` VARCHAR(191) NOT NULL,
    `conditionId` VARCHAR(191) NULL,
    `field` VARCHAR(191) NULL,
    `matchedScore` INTEGER NOT NULL,
    `unmatchedScore` INTEGER NOT NULL DEFAULT 0,
    `isDefault` BOOLEAN NOT NULL DEFAULT false,

    INDEX `scoring_results_ruleId_idx`(`ruleId`),
    INDEX `scoring_results_conditionId_idx`(`conditionId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `roles` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `description` TEXT NULL,
    `roleType` VARCHAR(191) NOT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `sortOrder` INTEGER NOT NULL DEFAULT 0,
    `isBuiltIn` BOOLEAN NOT NULL DEFAULT false,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `roles_code_key`(`code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `permissions` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `permissionType` VARCHAR(32) NOT NULL,
    `resource` VARCHAR(191) NULL,
    `action` VARCHAR(191) NULL,
    `dataScope` VARCHAR(191) NULL,
    `parentId` VARCHAR(191) NULL,
    `level` INTEGER NOT NULL DEFAULT 1,
    `path` VARCHAR(191) NULL,
    `description` TEXT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `sortOrder` INTEGER NOT NULL DEFAULT 0,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `permissions_code_key`(`code`),
    INDEX `permissions_parentId_idx`(`parentId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `role_permissions` (
    `id` VARCHAR(191) NOT NULL,
    `roleId` VARCHAR(191) NOT NULL,
    `permissionId` VARCHAR(191) NOT NULL,
    `grantType` VARCHAR(32) NOT NULL DEFAULT 'GRANT',
    `conditions` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `role_permissions_roleId_idx`(`roleId`),
    INDEX `role_permissions_permissionId_idx`(`permissionId`),
    UNIQUE INDEX `role_permissions_roleId_permissionId_grantType_key`(`roleId`, `permissionId`, `grantType`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `user_roles` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `roleId` VARCHAR(191) NOT NULL,
    `scope` VARCHAR(191) NULL,
    `startDate` DATETIME(3) NULL,
    `endDate` DATETIME(3) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `createdBy` VARCHAR(191) NULL,

    INDEX `user_roles_userId_idx`(`userId`),
    INDEX `user_roles_roleId_idx`(`roleId`),
    UNIQUE INDEX `user_roles_userId_roleId_key`(`userId`, `roleId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `data_permission_rules` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `description` VARCHAR(191) NULL,
    `permissionType` VARCHAR(32) NOT NULL,
    `ruleScope` VARCHAR(32) NOT NULL,
    `ruleExpression` VARCHAR(191) NULL,
    `roleIds` VARCHAR(191) NULL,
    `priority` INTEGER NOT NULL DEFAULT 0,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `data_permission_rules_code_key`(`code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `user_data_permissions` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `ruleId` VARCHAR(191) NOT NULL,
    `customScope` VARCHAR(191) NULL,
    `deptIds` VARCHAR(191) NULL,
    `userIds` VARCHAR(191) NULL,
    `startDate` DATETIME(3) NULL,
    `endDate` DATETIME(3) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `user_data_permissions_userId_idx`(`userId`),
    INDEX `user_data_permissions_ruleId_idx`(`ruleId`),
    UNIQUE INDEX `user_data_permissions_userId_ruleId_key`(`userId`, `ruleId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `mous` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `type` VARCHAR(32) NOT NULL,
    `description` TEXT NULL,
    `parentMouId` VARCHAR(191) NULL,
    `level` INTEGER NOT NULL DEFAULT 1,
    `path` VARCHAR(191) NULL,
    `metadata` VARCHAR(191) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `startDate` DATETIME(3) NULL,
    `endDate` DATETIME(3) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `mous_code_key`(`code`),
    INDEX `mous_parentMouId_idx`(`parentMouId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `user_mous` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `mouId` VARCHAR(191) NOT NULL,
    `roleInMou` VARCHAR(191) NULL,
    `startDate` DATETIME(3) NULL,
    `endDate` DATETIME(3) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `user_mous_userId_idx`(`userId`),
    INDEX `user_mous_mouId_idx`(`mouId`),
    UNIQUE INDEX `user_mous_userId_mouId_key`(`userId`, `mouId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `permission_containers` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `type` VARCHAR(32) NOT NULL,
    `description` TEXT NULL,
    `mouId` VARCHAR(191) NULL,
    `resourceFilter` VARCHAR(191) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `permission_containers_code_key`(`code`),
    INDEX `permission_containers_mouId_idx`(`mouId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `user_containers` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `containerId` VARCHAR(191) NOT NULL,
    `accessLevel` VARCHAR(191) NULL,
    `startDate` DATETIME(3) NULL,
    `endDate` DATETIME(3) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `user_containers_userId_idx`(`userId`),
    INDEX `user_containers_containerId_idx`(`containerId`),
    UNIQUE INDEX `user_containers_userId_containerId_key`(`userId`, `containerId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `container_resources` (
    `id` VARCHAR(191) NOT NULL,
    `containerId` VARCHAR(191) NOT NULL,
    `resourceType` VARCHAR(32) NOT NULL,
    `resourceId` VARCHAR(191) NOT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `container_resources_containerId_idx`(`containerId`),
    INDEX `container_resources_resourceId_idx`(`resourceId`),
    UNIQUE INDEX `container_resources_containerId_resourceType_resourceId_key`(`containerId`, `resourceType`, `resourceId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `automation_rules` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `code` VARCHAR(191) NOT NULL,
    `description` TEXT NULL,
    `eventType` VARCHAR(191) NOT NULL,
    `condition` VARCHAR(191) NULL,
    `actions` VARCHAR(191) NOT NULL,
    `priority` INTEGER NOT NULL DEFAULT 0,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `automation_rules_code_key`(`code`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `automation_logs` (
    `id` VARCHAR(191) NOT NULL,
    `ruleId` VARCHAR(191) NOT NULL,
    `triggerUserId` VARCHAR(191) NULL,
    `triggerEvent` VARCHAR(191) NULL,
    `executedActions` VARCHAR(191) NULL,
    `result` VARCHAR(191) NULL,
    `errorMessage` VARCHAR(191) NULL,
    `executedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `automation_logs_ruleId_idx`(`ruleId`),
    INDEX `automation_logs_triggerUserId_idx`(`triggerUserId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `mutual_exclusion_groups` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NOT NULL,
    `description` VARCHAR(191) NULL,
    `roleIds` VARCHAR(191) NOT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `permission_audit_logs` (
    `id` VARCHAR(191) NOT NULL,
    `userId` VARCHAR(191) NOT NULL,
    `userName` VARCHAR(191) NULL,
    `action` VARCHAR(32) NOT NULL,
    `targetType` VARCHAR(191) NOT NULL,
    `targetId` VARCHAR(191) NOT NULL,
    `targetName` VARCHAR(191) NULL,
    `source` VARCHAR(32) NOT NULL,
    `operatorId` VARCHAR(191) NULL,
    `operatorName` VARCHAR(191) NULL,
    `detail` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `permission_audit_logs_userId_idx`(`userId`),
    INDEX `permission_audit_logs_targetId_idx`(`targetId`),
    INDEX `permission_audit_logs_operatorId_idx`(`operatorId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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

-- CreateTable
CREATE TABLE `stage_rules` (
    `id` VARCHAR(191) NOT NULL,
    `linkId` VARCHAR(191) NOT NULL,
    `processId` VARCHAR(191) NOT NULL,
    `autoAdvanceType` VARCHAR(32) NOT NULL DEFAULT 'NONE',
    `autoAdvanceTiming` VARCHAR(16) NOT NULL DEFAULT 'NONE',
    `autoAdvanceDays` INTEGER NULL,
    `defaultHandlerType` VARCHAR(32) NOT NULL DEFAULT 'CUSTOM',
    `defaultHandlerFields` JSON NULL,
    `defaultHandlerUserIds` JSON NULL,
    `timeLimit` INTEGER NULL,
    `timeLimitScope` VARCHAR(16) NOT NULL DEFAULT 'NEW_ONLY',
    `interviewRoundIds` JSON NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `stage_rules_linkId_key`(`linkId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `entry_conditions` (
    `id` VARCHAR(191) NOT NULL,
    `linkId` VARCHAR(191) NOT NULL,
    `processId` VARCHAR(191) NOT NULL,
    `matchType` VARCHAR(16) NOT NULL DEFAULT 'ALL',
    `conditionType` VARCHAR(32) NOT NULL DEFAULT 'MIXED',
    `prompt` TEXT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `entry_conditions_linkId_key`(`linkId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `condition_items` (
    `id` VARCHAR(191) NOT NULL,
    `entryConditionId` VARCHAR(191) NOT NULL,
    `parentId` VARCHAR(191) NULL,
    `relationToParent` VARCHAR(8) NULL,
    `field` VARCHAR(64) NOT NULL,
    `operator` VARCHAR(32) NOT NULL,
    `value` JSON NULL,
    `refStageId` VARCHAR(191) NULL,
    `refDictId` VARCHAR(191) NULL,
    `orderIndex` INTEGER NOT NULL DEFAULT 0,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `condition_items_entryConditionId_parentId_idx`(`entryConditionId`, `parentId`),
    INDEX `condition_items_parentId_orderIndex_idx`(`parentId`, `orderIndex`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `interview_rounds` (
    `id` VARCHAR(191) NOT NULL,
    `code` VARCHAR(16) NOT NULL,
    `name` VARCHAR(64) NOT NULL,
    `description` TEXT NULL,
    `evaluationFormName` VARCHAR(64) NULL,
    `isUniversal` BOOLEAN NOT NULL DEFAULT false,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `createdBy` VARCHAR(191) NULL,
    `updatedBy` VARCHAR(191) NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `interview_rounds_code_key`(`code`),
    INDEX `interview_rounds_status_idx`(`status`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `auto_archive_rules` (
    `id` VARCHAR(191) NOT NULL,
    `processId` VARCHAR(191) NOT NULL,
    `ruleType` VARCHAR(32) NOT NULL,
    `enabled` BOOLEAN NOT NULL DEFAULT true,
    `config` JSON NOT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    INDEX `auto_archive_rules_processId_enabled_idx`(`processId`, `enabled`),
    UNIQUE INDEX `auto_archive_rules_processId_ruleType_key`(`processId`, `ruleType`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `resume_lock_records` ADD CONSTRAINT `resume_lock_records_resumeId_fkey` FOREIGN KEY (`resumeId`) REFERENCES `resumes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `resume_lock_records` ADD CONSTRAINT `resume_lock_records_lockerId_fkey` FOREIGN KEY (`lockerId`) REFERENCES `users`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `special_resume_tags` ADD CONSTRAINT `special_resume_tags_resumeId_fkey` FOREIGN KEY (`resumeId`) REFERENCES `resumes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `resume_merge_records` ADD CONSTRAINT `resume_merge_records_mainResumeId_fkey` FOREIGN KEY (`mainResumeId`) REFERENCES `resumes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `resume_merge_records` ADD CONSTRAINT `resume_merge_records_mergedResumeId_fkey` FOREIGN KEY (`mergedResumeId`) REFERENCES `resumes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `special_approval_flows` ADD CONSTRAINT `special_approval_flows_resumeId_fkey` FOREIGN KEY (`resumeId`) REFERENCES `resumes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `async_scoring_tasks` ADD CONSTRAINT `async_scoring_tasks_resumeId_fkey` FOREIGN KEY (`resumeId`) REFERENCES `resumes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `resume_flow_logs` ADD CONSTRAINT `resume_flow_logs_resumeId_fkey` FOREIGN KEY (`resumeId`) REFERENCES `resumes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `users` ADD CONSTRAINT `users_departmentId_fkey` FOREIGN KEY (`departmentId`) REFERENCES `departments`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `departments` ADD CONSTRAINT `departments_parentId_fkey` FOREIGN KEY (`parentId`) REFERENCES `departments`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `recruitment_processes` ADD CONSTRAINT `recruitment_processes_createdBy_fkey` FOREIGN KEY (`createdBy`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `recruitment_processes` ADD CONSTRAINT `recruitment_processes_updatedBy_fkey` FOREIGN KEY (`updatedBy`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `process_stage_links` ADD CONSTRAINT `process_stage_links_processId_fkey` FOREIGN KEY (`processId`) REFERENCES `recruitment_processes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `process_stage_links` ADD CONSTRAINT `process_stage_links_stageId_fkey` FOREIGN KEY (`stageId`) REFERENCES `recruitment_stages`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `demands` ADD CONSTRAINT `demands_departmentId_fkey` FOREIGN KEY (`departmentId`) REFERENCES `departments`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `demand_approval_steps` ADD CONSTRAINT `demand_approval_steps_demandId_fkey` FOREIGN KEY (`demandId`) REFERENCES `demands`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `demand_status_history` ADD CONSTRAINT `demand_status_history_demandId_fkey` FOREIGN KEY (`demandId`) REFERENCES `demands`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `positions` ADD CONSTRAINT `positions_departmentId_fkey` FOREIGN KEY (`departmentId`) REFERENCES `departments`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `positions` ADD CONSTRAINT `positions_demandId_fkey` FOREIGN KEY (`demandId`) REFERENCES `demands`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `positions` ADD CONSTRAINT `positions_processId_fkey` FOREIGN KEY (`processId`) REFERENCES `recruitment_processes`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `position_status_history` ADD CONSTRAINT `position_status_history_positionId_fkey` FOREIGN KEY (`positionId`) REFERENCES `positions`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `position_channels` ADD CONSTRAINT `position_channels_positionId_fkey` FOREIGN KEY (`positionId`) REFERENCES `positions`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `candidates` ADD CONSTRAINT `candidates_assignedUserId_fkey` FOREIGN KEY (`assignedUserId`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `candidates` ADD CONSTRAINT `candidates_resumeProviderId_fkey` FOREIGN KEY (`resumeProviderId`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `resumes` ADD CONSTRAINT `resumes_candidateId_fkey` FOREIGN KEY (`candidateId`) REFERENCES `candidates`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `applications` ADD CONSTRAINT `applications_candidateId_fkey` FOREIGN KEY (`candidateId`) REFERENCES `candidates`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `applications` ADD CONSTRAINT `applications_positionId_fkey` FOREIGN KEY (`positionId`) REFERENCES `positions`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `interviews` ADD CONSTRAINT `interviews_applicationId_fkey` FOREIGN KEY (`applicationId`) REFERENCES `applications`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `interview_feedbacks` ADD CONSTRAINT `interview_feedbacks_interviewId_fkey` FOREIGN KEY (`interviewId`) REFERENCES `interviews`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `offers` ADD CONSTRAINT `offers_applicationId_fkey` FOREIGN KEY (`applicationId`) REFERENCES `applications`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `offer_status_history` ADD CONSTRAINT `offer_status_history_offerId_fkey` FOREIGN KEY (`offerId`) REFERENCES `offers`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `background_check_records` ADD CONSTRAINT `background_check_records_offerId_fkey` FOREIGN KEY (`offerId`) REFERENCES `offers`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `candidate_offer_feedbacks` ADD CONSTRAINT `candidate_offer_feedbacks_offerId_fkey` FOREIGN KEY (`offerId`) REFERENCES `offers`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `onboardings` ADD CONSTRAINT `onboardings_applicationId_fkey` FOREIGN KEY (`applicationId`) REFERENCES `applications`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `invitation_records` ADD CONSTRAINT `invitation_records_applicationId_fkey` FOREIGN KEY (`applicationId`) REFERENCES `applications`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `dictionary_items` ADD CONSTRAINT `dictionary_items_dictionaryId_fkey` FOREIGN KEY (`dictionaryId`) REFERENCES `dictionaries`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `dictionary_items` ADD CONSTRAINT `dictionary_items_parentId_fkey` FOREIGN KEY (`parentId`) REFERENCES `dictionary_items`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `companies` ADD CONSTRAINT `companies_parentCompanyId_fkey` FOREIGN KEY (`parentCompanyId`) REFERENCES `companies`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `scoring_conditions` ADD CONSTRAINT `scoring_conditions_ruleId_fkey` FOREIGN KEY (`ruleId`) REFERENCES `scoring_rules`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `scoring_results` ADD CONSTRAINT `scoring_results_ruleId_fkey` FOREIGN KEY (`ruleId`) REFERENCES `scoring_rules`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `scoring_results` ADD CONSTRAINT `scoring_results_conditionId_fkey` FOREIGN KEY (`conditionId`) REFERENCES `scoring_conditions`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `permissions` ADD CONSTRAINT `permissions_parentId_fkey` FOREIGN KEY (`parentId`) REFERENCES `permissions`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `role_permissions` ADD CONSTRAINT `role_permissions_roleId_fkey` FOREIGN KEY (`roleId`) REFERENCES `roles`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `role_permissions` ADD CONSTRAINT `role_permissions_permissionId_fkey` FOREIGN KEY (`permissionId`) REFERENCES `permissions`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_roles` ADD CONSTRAINT `user_roles_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_roles` ADD CONSTRAINT `user_roles_roleId_fkey` FOREIGN KEY (`roleId`) REFERENCES `roles`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_data_permissions` ADD CONSTRAINT `user_data_permissions_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_data_permissions` ADD CONSTRAINT `user_data_permissions_ruleId_fkey` FOREIGN KEY (`ruleId`) REFERENCES `data_permission_rules`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `mous` ADD CONSTRAINT `mous_parentMouId_fkey` FOREIGN KEY (`parentMouId`) REFERENCES `mous`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_mous` ADD CONSTRAINT `user_mous_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_mous` ADD CONSTRAINT `user_mous_mouId_fkey` FOREIGN KEY (`mouId`) REFERENCES `mous`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `permission_containers` ADD CONSTRAINT `permission_containers_mouId_fkey` FOREIGN KEY (`mouId`) REFERENCES `mous`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_containers` ADD CONSTRAINT `user_containers_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `user_containers` ADD CONSTRAINT `user_containers_containerId_fkey` FOREIGN KEY (`containerId`) REFERENCES `permission_containers`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `container_resources` ADD CONSTRAINT `container_resources_containerId_fkey` FOREIGN KEY (`containerId`) REFERENCES `permission_containers`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `automation_logs` ADD CONSTRAINT `automation_logs_ruleId_fkey` FOREIGN KEY (`ruleId`) REFERENCES `automation_rules`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `permission_audit_logs` ADD CONSTRAINT `permission_audit_logs_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

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

-- AddForeignKey
ALTER TABLE `stage_rules` ADD CONSTRAINT `stage_rules_linkId_fkey` FOREIGN KEY (`linkId`) REFERENCES `process_stage_links`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `stage_rules` ADD CONSTRAINT `stage_rules_processId_fkey` FOREIGN KEY (`processId`) REFERENCES `recruitment_processes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `entry_conditions` ADD CONSTRAINT `entry_conditions_linkId_fkey` FOREIGN KEY (`linkId`) REFERENCES `process_stage_links`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `entry_conditions` ADD CONSTRAINT `entry_conditions_processId_fkey` FOREIGN KEY (`processId`) REFERENCES `recruitment_processes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `condition_items` ADD CONSTRAINT `condition_items_entryConditionId_fkey` FOREIGN KEY (`entryConditionId`) REFERENCES `entry_conditions`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `condition_items` ADD CONSTRAINT `condition_items_parentId_fkey` FOREIGN KEY (`parentId`) REFERENCES `condition_items`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `interview_rounds` ADD CONSTRAINT `interview_rounds_createdBy_fkey` FOREIGN KEY (`createdBy`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `interview_rounds` ADD CONSTRAINT `interview_rounds_updatedBy_fkey` FOREIGN KEY (`updatedBy`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `auto_archive_rules` ADD CONSTRAINT `auto_archive_rules_processId_fkey` FOREIGN KEY (`processId`) REFERENCES `recruitment_processes`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;

