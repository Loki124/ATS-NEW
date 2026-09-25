"""简历解析测试夹具 (test fixtures)

开发 / 测试环境在无真实 Affinda API key 时，使用本模块提供的**真实结构、字段类型一致**
的测试简历数据，替代原先的单一示例 mock。

设计要点：
- 每份夹具都是合法 ``ParsedResume`` 的数据（字段、类型与真实 Affinda 返回完全一致），
  供解析结果落 ``Candidate.extra``、指标快照、查重等链路无差别消费。
- 选中策略：依据上传文件名稳定哈希，同一文件始终映射到同一份夹具，保证可复现的
  测试 / 演示结果；不同文件分布到不同夹具，贴近真实多候选人场景。
- 仅作「无 key 兜底」用途；生产环境配置真实 ``AFFINDA_API_KEY`` 后走真实解析，本模块不被调用。
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List

# 字段结构与 apps.add_candidate.services.resume_parser.ParsedResume 完全对齐：
#   name/phone/email/gender/age/edu 基本字段 + educations[]/experiences[] 子段。
# period 使用 "YYYY-YYYY" 与 "YYYY-至今" 两种真实简历常见写法，
# 与 metrics.services.resume_struct.parse_period 兼容。
FIXTURE_DATA: List[Dict[str, Any]] = [
    {
        'name': '张伟',
        'phone': '13800138000',
        'email': 'zhangwei@example.com',
        'gender': '男',
        'age': 32,
        'edu': '硕士',
        'educations': [
            {'period': '2008-2012', 'school': '浙江大学', 'major': '计算机科学与技术', 'degree': '本科'},
            {'period': '2012-2015', 'school': '浙江大学', 'major': '软件工程', 'degree': '硕士'},
        ],
        'experiences': [
            {'period': '2015-2018', 'company': '阿里巴巴', 'position': '后端工程师',
             'summary': '负责交易核心链路开发与稳定性治理'},
            {'period': '2018-至今', 'company': '蚂蚁集团', 'position': '高级工程师',
             'summary': '主导支付清结算系统重构，担任团队技术负责人'},
        ],
        'confidence': 0.96,
    },
    {
        'name': '李娜',
        'phone': '13912345678',
        'email': 'lina@example.com',
        'gender': '女',
        'age': 28,
        'edu': '本科',
        'educations': [
            {'period': '2014-2018', 'school': '南京大学', 'major': '市场营销', 'degree': '本科'},
        ],
        'experiences': [
            {'period': '2018-2021', 'company': '字节跳动', 'position': '产品经理',
             'summary': '负责内容社区增长策略与活动运营'},
            {'period': '2021-至今', 'company': '美团', 'position': '高级产品经理',
             'summary': '主导本地生活业务线商家端产品规划'},
        ],
        'confidence': 0.93,
    },
    {
        'name': '王强',
        'phone': '13700001111',
        'email': 'wangqiang@example.com',
        'gender': '男',
        'age': 35,
        'edu': '博士',
        'educations': [
            {'period': '2006-2010', 'school': '清华大学', 'major': '自动化', 'degree': '本科'},
            {'period': '2010-2013', 'school': '清华大学', 'major': '控制科学与工程', 'degree': '博士'},
        ],
        'experiences': [
            {'period': '2013-2017', 'company': '华为', 'position': '算法工程师',
             'summary': '从事机器视觉算法研发与落地'},
            {'period': '2017-至今', 'company': '商汤科技', 'position': '资深研究员',
             'summary': '带领团队攻关多模态大模型训练框架'},
        ],
        'confidence': 0.98,
    },
    {
        'name': '陈静',
        'phone': '13622223333',
        'email': 'chenjing@example.com',
        'gender': '女',
        'age': 26,
        'edu': '本科',
        'educations': [
            {'period': '2016-2020', 'school': '武汉大学', 'major': '视觉传达设计', 'degree': '本科'},
        ],
        'experiences': [
            {'period': '2020-2022', 'company': '腾讯', 'position': 'UI 设计师',
             'summary': '负责 B 端产品界面与组件库设计'},
            {'period': '2022-至今', 'company': '小红书', 'position': '高级 UI 设计师',
             'summary': '主导社区核心频道视觉改版'},
        ],
        'confidence': 0.91,
    },
    {
        'name': '刘洋',
        'phone': '13544445555',
        'email': 'liuyang@example.com',
        'gender': '男',
        'age': 30,
        'edu': '硕士',
        'educations': [
            {'period': '2011-2015', 'school': '哈尔滨工业大学', 'major': '电子信息工程', 'degree': '本科'},
            {'period': '2015-2018', 'school': '哈尔滨工业大学', 'major': '计算机技术', 'degree': '硕士'},
        ],
        'experiences': [
            {'period': '2018-2021', 'company': '大疆创新', 'position': '嵌入式工程师',
             'summary': '负责飞控系统底层驱动开发'},
            {'period': '2021-至今', 'company': '小米', 'position': '系统架构师',
             'summary': '牵头 IoT 设备端到端通信协议设计'},
        ],
        'confidence': 0.95,
    },
    {
        'name': '赵敏',
        'phone': '13866667777',
        'email': 'zhaomin@example.com',
        'gender': '女',
        'age': 33,
        'edu': '硕士',
        'educations': [
            {'period': '2009-2013', 'school': '上海财经大学', 'major': '会计学', 'degree': '本科'},
            {'period': '2013-2016', 'school': '上海财经大学', 'major': '财务管理', 'degree': '硕士'},
        ],
        'experiences': [
            {'period': '2016-2019', 'company': '普华永道', 'position': '审计员',
             'summary': '负责 TMT 行业上市公司年审'},
            {'period': '2019-至今', 'company': '拼多多', 'position': '财务经理',
             'summary': '统筹事业部预算管理与经营分析'},
        ],
        'confidence': 0.94,
    },
]


def get_fixture_data(filename: str) -> Dict[str, Any]:
    """依据文件名稳定哈希选择一份测试简历夹具。

    同一文件始终返回同一份，保证可复现；不同文件分布到不同夹具。
    """
    seed = int(hashlib.md5((filename or 'resume.pdf').encode('utf-8')).hexdigest(), 16)
    return FIXTURE_DATA[seed % len(FIXTURE_DATA)]
