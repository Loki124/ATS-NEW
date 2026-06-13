-- Todo #2: 给 7 核心业务表加 deletedAt 列 + 索引
-- 表: users, departments, demands, positions, candidates, offers, onboardings
-- MySQL 8 不支持 ADD COLUMN IF NOT EXISTS,所以用 stored procedures + information_schema
-- 模式: 14 个 procedure (7 列 + 7 索引),每个都 IF NOT EXISTS 守护,可重复跑

-- ============================================
-- 1) users
-- ============================================
DROP PROCEDURE IF EXISTS add_users_deleted_at;
CREATE PROCEDURE add_users_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'users'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `users` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_users_deleted_at();
DROP PROCEDURE add_users_deleted_at;

DROP PROCEDURE IF EXISTS add_users_deleted_at_idx;
CREATE PROCEDURE add_users_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'users'
                   AND index_name = 'users_deletedAt_idx') THEN
    CREATE INDEX `users_deletedAt_idx` ON `users`(`deletedAt`);
  END IF;
END;
CALL add_users_deleted_at_idx();
DROP PROCEDURE add_users_deleted_at_idx;

-- ============================================
-- 2) departments
-- ============================================
DROP PROCEDURE IF EXISTS add_departments_deleted_at;
CREATE PROCEDURE add_departments_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'departments'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `departments` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_departments_deleted_at();
DROP PROCEDURE add_departments_deleted_at;

DROP PROCEDURE IF EXISTS add_departments_deleted_at_idx;
CREATE PROCEDURE add_departments_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'departments'
                   AND index_name = 'departments_deletedAt_idx') THEN
    CREATE INDEX `departments_deletedAt_idx` ON `departments`(`deletedAt`);
  END IF;
END;
CALL add_departments_deleted_at_idx();
DROP PROCEDURE add_departments_deleted_at_idx;

-- ============================================
-- 3) demands
-- ============================================
DROP PROCEDURE IF EXISTS add_demands_deleted_at;
CREATE PROCEDURE add_demands_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'demands'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `demands` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_demands_deleted_at();
DROP PROCEDURE add_demands_deleted_at;

DROP PROCEDURE IF EXISTS add_demands_deleted_at_idx;
CREATE PROCEDURE add_demands_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'demands'
                   AND index_name = 'demands_deletedAt_idx') THEN
    CREATE INDEX `demands_deletedAt_idx` ON `demands`(`deletedAt`);
  END IF;
END;
CALL add_demands_deleted_at_idx();
DROP PROCEDURE add_demands_deleted_at_idx;

-- ============================================
-- 4) positions
-- ============================================
DROP PROCEDURE IF EXISTS add_positions_deleted_at;
CREATE PROCEDURE add_positions_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'positions'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `positions` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_positions_deleted_at();
DROP PROCEDURE add_positions_deleted_at;

DROP PROCEDURE IF EXISTS add_positions_deleted_at_idx;
CREATE PROCEDURE add_positions_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'positions'
                   AND index_name = 'positions_deletedAt_idx') THEN
    CREATE INDEX `positions_deletedAt_idx` ON `positions`(`deletedAt`);
  END IF;
END;
CALL add_positions_deleted_at_idx();
DROP PROCEDURE add_positions_deleted_at_idx;

-- ============================================
-- 5) candidates
-- ============================================
DROP PROCEDURE IF EXISTS add_candidates_deleted_at;
CREATE PROCEDURE add_candidates_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'candidates'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `candidates` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_candidates_deleted_at();
DROP PROCEDURE add_candidates_deleted_at;

DROP PROCEDURE IF EXISTS add_candidates_deleted_at_idx;
CREATE PROCEDURE add_candidates_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'candidates'
                   AND index_name = 'candidates_deletedAt_idx') THEN
    CREATE INDEX `candidates_deletedAt_idx` ON `candidates`(`deletedAt`);
  END IF;
END;
CALL add_candidates_deleted_at_idx();
DROP PROCEDURE add_candidates_deleted_at_idx;

-- ============================================
-- 6) offers
-- ============================================
DROP PROCEDURE IF EXISTS add_offers_deleted_at;
CREATE PROCEDURE add_offers_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'offers'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `offers` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_offers_deleted_at();
DROP PROCEDURE add_offers_deleted_at;

DROP PROCEDURE IF EXISTS add_offers_deleted_at_idx;
CREATE PROCEDURE add_offers_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'offers'
                   AND index_name = 'offers_deletedAt_idx') THEN
    CREATE INDEX `offers_deletedAt_idx` ON `offers`(`deletedAt`);
  END IF;
END;
CALL add_offers_deleted_at_idx();
DROP PROCEDURE add_offers_deleted_at_idx;

-- ============================================
-- 7) onboardings
-- ============================================
DROP PROCEDURE IF EXISTS add_onboardings_deleted_at;
CREATE PROCEDURE add_onboardings_deleted_at()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'onboardings'
                   AND column_name = 'deletedAt') THEN
    ALTER TABLE `onboardings` ADD COLUMN `deletedAt` DATETIME(3) NULL;
  END IF;
END;
CALL add_onboardings_deleted_at();
DROP PROCEDURE add_onboardings_deleted_at;

DROP PROCEDURE IF EXISTS add_onboardings_deleted_at_idx;
CREATE PROCEDURE add_onboardings_deleted_at_idx()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema = DATABASE()
                   AND table_name = 'onboardings'
                   AND index_name = 'onboardings_deletedAt_idx') THEN
    CREATE INDEX `onboardings_deletedAt_idx` ON `onboardings`(`deletedAt`);
  END IF;
END;
CALL add_onboardings_deleted_at_idx();
DROP PROCEDURE add_onboardings_deleted_at_idx;
