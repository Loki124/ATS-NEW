"""
手动定义 Django 初始迁移（migration stubs）

由于环境限制，无法执行 python manage.py makemigrations。
本文件提供所有 app 的初始迁移 SQL 参考，
部署时先执行 python manage.py makemigrations，
再执行 python manage.py migrate。

如果 makemigrations 失败，可自行对照本文件手写 migration。
"""
from django.db import connection


# =============================================================================
# 数据库表结构参考（PostgreSQL 15）
# =============================================================================

TABLES_SQL = """

-- =========================================================================
-- 1. core 模块
-- =========================================================================

CREATE TABLE IF NOT EXISTS departments (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    parent_id VARCHAR(32) REFERENCES departments(id) ON DELETE SET NULL,
    path VARCHAR(500) DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    leader_id VARCHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP NULL,
    is_superuser BOOLEAN DEFAULT FALSE,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) DEFAULT '',
    last_name VARCHAR(150) DEFAULT '',
    email VARCHAR(254) DEFAULT '',
    is_staff BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    date_joined TIMESTAMP DEFAULT NOW(),
    employee_id VARCHAR(50) UNIQUE NULL,
    phone VARCHAR(20) NULL,
    avatar VARCHAR(500) NULL,
    department_id VARCHAR(32) REFERENCES departments(id) ON DELETE SET NULL,
    direct_manager_id VARCHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    position_title VARCHAR(100) NULL,
    level VARCHAR(50) NULL,
    bu_president_id VARCHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    solid_vp_id VARCHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    dotted_vp_id VARCHAR(32) REFERENCES users(id) ON DELETE SET NULL,
    moka_user_id VARCHAR(100) NULL,
    last_assignment_at TIMESTAMP NULL,
    deleted_at TIMESTAMP NULL,
    last_login_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS users_department_is_active_idx ON users(department_id, is_active);
CREATE INDEX IF NOT EXISTS users_level_idx ON users(level);
CREATE INDEX IF NOT EXISTS users_phone_idx ON users(phone);
CREATE INDEX IF NOT EXISTS users_deleted_at_idx ON users(deleted_at);

CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    is_builtin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    module VARCHAR(50) NOT NULL,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id VARCHAR(32) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    department_id VARCHAR(32) REFERENCES departments(id) ON DELETE SET NULL,
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(user_id, role_id, department_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id BIGSERIAL PRIMARY KEY,
    role_id VARCHAR(32) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(32) NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- =========================================================================
-- 2. common 模块（抽象基类，不生成表）
-- =========================================================================
-- TimestampedModel, SoftDeleteModel, FullAuditModel 是抽象基类
-- 字段会直接附加到各子表的 created_at, updated_at, deleted_at, created_by_id, updated_by_id

-- =========================================================================
-- 3. process 模块
-- =========================================================================

CREATE TABLE IF NOT EXISTS recruitment_stages (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(20) UNIQUE NOT NULL,
    stage_type VARCHAR(20) NOT NULL,
    status VARCHAR(16) DEFAULT 'ENABLED',
    is_builtin BOOLEAN DEFAULT FALSE,
    default_features JSONB DEFAULT '[]',
    optional_features JSONB DEFAULT '[]',
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS recruitment_stages_type_idx ON recruitment_stages(stage_type);

CREATE TABLE IF NOT EXISTS recruitment_processes (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(30) NOT NULL,
    current_version VARCHAR(20) DEFAULT '1.0',
    applicable_scope JSONB DEFAULT '{}',
    is_template BOOLEAN DEFAULT FALSE,
    template_code VARCHAR(50) NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    validate_resume_score BOOLEAN DEFAULT TRUE,
    description VARCHAR(100) DEFAULT '',
    status VARCHAR(16) DEFAULT 'ENABLED',
    archived_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS process_stage_links (
    id VARCHAR(32) PRIMARY KEY,
    process_id VARCHAR(32) NOT NULL REFERENCES recruitment_processes(id) ON DELETE CASCADE,
    stage_id VARCHAR(32) NOT NULL REFERENCES recruitment_stages(id) ON DELETE PROTECT,
    "order" INTEGER DEFAULT 0,
    is_required BOOLEAN DEFAULT TRUE,
    entry_rule_expression VARCHAR(500) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(process_id, stage_id)
);

CREATE TABLE IF NOT EXISTS stage_rules (
    id VARCHAR(32) PRIMARY KEY,
    link_id VARCHAR(32) UNIQUE NOT NULL REFERENCES process_stage_links(id) ON DELETE CASCADE,
    data_source VARCHAR(32) DEFAULT '',
    data_field VARCHAR(64) DEFAULT '',
    processing_rule VARCHAR(32) DEFAULT 'DIRECT',
    processor_order JSONB DEFAULT '[]',
    current_processor_index INTEGER DEFAULT 0,
    auto_skip_n_plus_two BOOLEAN DEFAULT FALSE,
    inherit_prior_consensus BOOLEAN DEFAULT FALSE,
    legacy_time_limit_days INTEGER NULL,
    legacy_grab_threshold INTEGER NULL,
    is_grab_mode BOOLEAN DEFAULT FALSE,
    grab_threshold INTEGER DEFAULT 30,
    interview_rounds INTEGER DEFAULT 1,
    interview_format VARCHAR(32) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS process_templates (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    category VARCHAR(50) DEFAULT '',
    snapshot JSONB DEFAULT '{}',
    is_builtin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =========================================================================
-- 4. entry_condition 模块
-- =========================================================================

CREATE TABLE IF NOT EXISTS entry_condition_rules (
    id VARCHAR(32) PRIMARY KEY,
    link_id VARCHAR(32) NOT NULL REFERENCES process_stage_links(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    rule_json JSONB DEFAULT '[]',
    logic VARCHAR(8) DEFAULT 'ALL',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =========================================================================
-- 5. time_limit 模块
-- =========================================================================

CREATE TABLE IF NOT EXISTS time_limit_rules (
    id VARCHAR(32) PRIMARY KEY,
    link_id VARCHAR(32) NOT NULL REFERENCES process_stage_links(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    time_limit_days INTEGER NOT NULL,
    effective_scope VARCHAR(16) DEFAULT 'ALL',
    priority INTEGER DEFAULT 100,
    status VARCHAR(16) DEFAULT 'ENABLED',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =========================================================================
-- 6. automation 模块
-- =========================================================================

CREATE TABLE IF NOT EXISTS automation_rules (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    process_id VARCHAR(32) NOT NULL REFERENCES recruitment_processes(id) ON DELETE CASCADE,
    stage_id VARCHAR(32) NOT NULL REFERENCES recruitment_stages(id) ON DELETE CASCADE,
    trigger_type VARCHAR(32) NOT NULL,
    trigger_timing VARCHAR(32) NOT NULL,
    trigger_delay_hours INTEGER NULL,
    condition_logic VARCHAR(8) DEFAULT 'ALL',
    condition_json JSONB DEFAULT '[]',
    action_type VARCHAR(32) NOT NULL,
    next_stage_id VARCHAR(32) REFERENCES recruitment_stages(id) ON DELETE SET NULL,
    skip_check BOOLEAN DEFAULT FALSE,
    scope_json JSONB DEFAULT '{}',
    priority VARCHAR(8) DEFAULT 'P1',
    enabled BOOLEAN DEFAULT TRUE,
    failure_rate_threshold FLOAT DEFAULT 0.5,
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS automation_rules_process_stage_idx ON automation_rules(process_id, stage_id);
CREATE INDEX IF NOT EXISTS automation_rules_enabled_priority_idx ON automation_rules(enabled, priority);

CREATE TABLE IF NOT EXISTS automation_logs (
    id VARCHAR(32) PRIMARY KEY,
    rule_id VARCHAR(32) NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    candidate_id VARCHAR(32) NOT NULL,
    trigger_time TIMESTAMP DEFAULT NOW(),
    evaluate_result VARCHAR(16) NOT NULL,
    action_taken VARCHAR(200) DEFAULT '',
    skip_reason VARCHAR(500) DEFAULT '',
    error_message TEXT DEFAULT '',
    execution_ms INTEGER NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS automation_logs_rule_time_idx ON automation_logs(rule_id, trigger_time);
CREATE INDEX IF NOT EXISTS automation_logs_candidate_idx ON automation_logs(candidate_id);

-- =========================================================================
-- 7. candidate 模块
-- =========================================================================

CREATE TABLE IF NOT EXISTS candidates (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100) NULL,
    gender VARCHAR(8) DEFAULT '',
    age INTEGER NULL,
    birth_date DATE NULL,
    id_card_no VARCHAR(20) DEFAULT '',
    highest_education VARCHAR(50) DEFAULT '',
    work_years DECIMAL(4,1) NULL,
    current_city VARCHAR(50) DEFAULT '',
    expected_city VARCHAR(50) DEFAULT '',
    current_company VARCHAR(100) DEFAULT '',
    current_position VARCHAR(100) DEFAULT '',
    expected_salary DECIMAL(10,2) NULL,
    resume_file_url VARCHAR(500) NULL,
    resume_text TEXT DEFAULT '',
    source_channel_id VARCHAR(32) REFERENCES channels(id) ON DELETE SET NULL,
    referrer_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    referral_type VARCHAR(16) DEFAULT '',
    resume_score DECIMAL(5,2) NULL,
    extra JSONB DEFAULT '{}',
    current_state VARCHAR(32) DEFAULT 'APPLIED',
    tags JSONB DEFAULT '[]',
    is_blacklisted BOOLEAN DEFAULT FALSE,
    blacklist_reason VARCHAR(200) DEFAULT '',
    moka_candidate_id VARCHAR(100) NULL,
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS candidates_name_phone_idx ON candidates(name, phone);
CREATE INDEX IF NOT EXISTS candidates_state_idx ON candidates(current_state);
CREATE INDEX IF NOT EXISTS candidates_blacklist_idx ON candidates(is_blacklisted);
CREATE INDEX IF NOT EXISTS candidates_moka_idx ON candidates(moka_candidate_id);

CREATE TABLE IF NOT EXISTS candidate_tags (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    color VARCHAR(20) DEFAULT 'blue',
    category VARCHAR(32) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS candidate_histories (
    id VARCHAR(32) PRIMARY KEY,
    candidate_id VARCHAR(32) NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    action VARCHAR(64) NOT NULL,
    detail JSONB DEFAULT '{}',
    operator_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS candidate_histories_candidate_time_idx ON candidate_histories(candidate_id, created_at);

-- =========================================================================
-- 8. position 模块
-- =========================================================================

CREATE TABLE IF NOT EXISTS positions (
    id VARCHAR(32) PRIMARY KEY,
    -- ... 省略完整字段，执行 makemigrations 后自动生成
    code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(100) NOT NULL,
    -- 等
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =========================================================================
-- 9. application 模块（最核心）
-- =========================================================================

CREATE TABLE IF NOT EXISTS applications (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    candidate_id VARCHAR(32) NOT NULL REFERENCES candidates(id) ON DELETE PROTECT,
    position_id VARCHAR(32) NOT NULL REFERENCES positions(id) ON DELETE PROTECT,
    process_id VARCHAR(32) NOT NULL REFERENCES recruitment_processes(id) ON DELETE PROTECT,
    workflow_version VARCHAR(20) NOT NULL,
    current_link_id VARCHAR(32) REFERENCES process_stage_links(id) ON DELETE SET NULL,
    current_stage_id VARCHAR(32) REFERENCES recruitment_stages(id) ON DELETE SET NULL,
    state VARCHAR(32) DEFAULT 'PENDING',
    time_limit_rule_id VARCHAR(32) NULL,
    total_time_limit_days INTEGER NULL,
    stage_entered_at TIMESTAMP NULL,
    stage_deadline TIMESTAMP NULL,
    is_grabbed BOOLEAN DEFAULT FALSE,
    grabbed_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    grabbed_at TIMESTAMP NULL,
    last_advanced_at TIMESTAMP NULL,
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS applications_candidate_position_idx ON applications(candidate_id, position_id);
CREATE INDEX IF NOT EXISTS applications_state_stage_idx ON applications(state, current_stage_id);
CREATE INDEX IF NOT EXISTS applications_deadline_idx ON applications(stage_deadline);

CREATE TABLE IF NOT EXISTS application_stage_records (
    id VARCHAR(32) PRIMARY KEY,
    application_id VARCHAR(32) NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    link_id VARCHAR(32) NOT NULL REFERENCES process_stage_links(id) ON DELETE PROTECT,
    stage_id VARCHAR(32) NOT NULL REFERENCES recruitment_stages(id) ON DELETE PROTECT,
    state VARCHAR(20) DEFAULT 'NOT_STARTED',
    entered_at TIMESTAMP NULL,
    exited_at TIMESTAMP NULL,
    duration_days INTEGER NULL,
    time_limit_rule_id VARCHAR(32) NULL,
    total_time_limit_days INTEGER NULL,
    deadline TIMESTAMP NULL,
    current_handlers JSONB DEFAULT '[]',
    auto_promoted BOOLEAN DEFAULT FALSE,
    automation_rule_id VARCHAR(32) NULL,
    note TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS stage_records_app_stage_idx ON application_stage_records(application_id, state);
CREATE INDEX IF NOT EXISTS stage_records_deadline_idx ON application_stage_records(deadline);

CREATE TABLE IF NOT EXISTS application_histories (
    id VARCHAR(32) PRIMARY KEY,
    application_id VARCHAR(32) NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    action VARCHAR(32) NOT NULL,
    from_stage_id VARCHAR(32) REFERENCES recruitment_stages(id) ON DELETE SET NULL,
    to_stage_id VARCHAR(32) REFERENCES recruitment_stages(id) ON DELETE SET NULL,
    detail JSONB DEFAULT '{}',
    operator_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    is_auto BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS app_histories_app_time_idx ON application_histories(application_id, created_at);

-- =========================================================================
-- 10. 其他模块（demand/offer/onboarding/interview/invitation/referral/
--            talent_pool/channel/analytics/notification/audit/gdpr/
--            integration/field_acl）
-- 省略... 部署时执行 makemigrations 自动生成
-- =========================================================================

""";


def preview_sqls():
    """打印所有建表 SQL（仅预览，不执行）"""
    print(TABLES_SQL)
    print("\n-- 请复制以上 SQL 到 PostgreSQL 执行，或运行 python manage.py makemigrations + migrate")


def run_sqls():
    """直接执行 SQL（慎用！仅在空数据库时使用）"""
    with connection.cursor() as cursor:
        for stmt in TABLES_SQL.split(';'):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)
    print('✅ 所有表创建完成')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--run':
        run_sqls()
    else:
        preview_sqls()
