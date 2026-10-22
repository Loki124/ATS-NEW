/**
 * 校招生管理 · 示例（mock）数据
 *
 * 用途：校招各页在**真实数据为空**时用示例数据兜底，便于评审 UI 版式与交互
 *      （dev 库目前只有 8 个部门、直播间/客服/班级/档案几乎为空，页面全是空态）。
 *
 * 约定（重要）：
 * 1. **只读**。示例行不落库：展示示例数据时页面禁用新建/编辑/删除，避免把假 id 写进后端
 *    （这正是「能点但数据假」的坑，见 CandidateList 2026-09-25 的同类整改）。
 * 2. **部门按名字引用**，不写死 id —— 各环境（dev/test/prod）部门 id 不同。
 *    由 `resolveDeptRefs()` 在运行时用部门 store 把名字换成真实 id；换不到时保留名字，
 *    列表列的 `deptName()` 兜底会直接显示该名字，不会出现 undefined。
 * 3. 字段名与后端序列化器**逐字段对齐**（camelCase），保证列渲染路径与真实数据一致。
 * 4. 所有 mock 行的 id 一律 `MOCK_` 前缀，与真实主键不可能撞号。
 */

/**
 * 示例轮岗资源（RotationResource 序列化字段）。
 *
 * ⚠️ 2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」一张表 →
 *   原 MOCK_LIVE_ROOMS / MOCK_SERVICE_DEPTS 两份示例合并为 MOCK_RESOURCES 一份，
 *   用 `resourceType` 区分形态（直播间 / 客服部门 / 其他）。
 *   字段与后端序列化器逐字段对齐：resourceNo / name / resourceType / department /
 *   bu / mentor / mentorName / platform / location / capacity / socialCount /
 *   campusCount / isActive。
 *   品牌 / 客服类型 / 工位类型 / 是否需培训认证已随字段下线而移除。
 */
export const MOCK_RESOURCES: any[] = [
  // —— 直播间形态（LR+4）——
  { id: 'MOCK_RS_01', resourceNo: 'LR0001', name: '视频号直播-上海-01', resourceType: 'LIVE_ROOM', department: '技术中心', bu: '能智BG', mentor: '王建国（带教导师）', mentorName: '王建国', platform: 'VIDEO_ACCOUNT', location: '上海', capacity: 20, socialCount: 3, campusCount: 12, isActive: true },
  { id: 'MOCK_RS_02', resourceNo: 'LR0002', name: '腾讯会议-北京-面试间', resourceType: 'LIVE_ROOM', department: '产品中心', bu: '能智BG', mentor: '李晓萌（带教导师）', mentorName: '李晓萌', platform: 'TENCENT_MEETING', location: '北京', capacity: 8, socialCount: 1, campusCount: 5, isActive: true },
  { id: 'MOCK_RS_03', resourceNo: 'LR0003', name: '企微直播-深圳-客服号', resourceType: 'LIVE_ROOM', department: '运营中心', bu: '能智BG', mentor: '陈志远（带教导师）', mentorName: '陈志远', platform: 'WECHAT_WORK_LIVE', location: '深圳', capacity: 15, socialCount: 4, campusCount: 9, isActive: true },
  { id: 'MOCK_RS_04', resourceNo: 'LR0004', name: '视频号直播-成都-校招专场', resourceType: 'LIVE_ROOM', department: '产品中心', bu: '醒市', mentor: '赵一鸣（带教导师）', mentorName: '赵一鸣', platform: 'VIDEO_ACCOUNT', location: '成都', capacity: 30, socialCount: 6, campusCount: 18, isActive: true },
  { id: 'MOCK_RS_05', resourceNo: 'LR0005', name: '企微直播-上海-新人训练营', resourceType: 'LIVE_ROOM', department: '技术中心', bu: '能良', mentor: '孙悦（带教导师）', mentorName: '孙悦', platform: 'WECHAT_WORK_LIVE', location: '上海', capacity: 12, socialCount: 2, campusCount: 7, isActive: true },
  { id: 'MOCK_RS_06', resourceNo: 'LR0006', name: '腾讯会议-深圳-评审室', resourceType: 'LIVE_ROOM', department: '运营中心', bu: '醒市', mentor: '周航（带教导师）', mentorName: '周航', platform: 'TENCENT_MEETING', location: '深圳', capacity: 6, socialCount: 0, campusCount: 2, isActive: true },
  { id: 'MOCK_RS_07', resourceNo: 'LR0007', name: '视频号直播-北京-旧场地', resourceType: 'LIVE_ROOM', department: '技术中心', bu: '能良', mentor: '吴倩（带教导师）', mentorName: '吴倩', platform: 'VIDEO_ACCOUNT', location: '北京', capacity: 10, socialCount: 1, campusCount: 0, isActive: false },
  { id: 'MOCK_RS_08', resourceNo: 'LR0008', name: '企微直播-成都-宣讲候场', resourceType: 'LIVE_ROOM', department: '产品中心', bu: '能智BG', mentor: '郑凯（带教导师）', mentorName: '郑凯', platform: 'WECHAT_WORK_LIVE', location: '成都', capacity: 18, socialCount: 5, campusCount: 11, isActive: true },
  // —— 客服部门形态（SD+4）——
  { id: 'MOCK_RS_09', resourceNo: 'SD0001', name: '上海在线客服一部', resourceType: 'SERVICE_DEPT', department: '技术中心', bu: '能智BG', mentor: '林曼（客服主管）', mentorName: '林曼', platform: '', location: '上海', capacity: 40, socialCount: 8, campusCount: 22, isActive: true },
  { id: 'MOCK_RS_10', resourceNo: 'SD0002', name: '上海外呼客服组', resourceType: 'SERVICE_DEPT', department: '运营中心', bu: '能智BG', mentor: '黄磊（客服主管）', mentorName: '黄磊', platform: '', location: '上海', capacity: 25, socialCount: 5, campusCount: 10, isActive: true },
  { id: 'MOCK_RS_11', resourceNo: 'SD0003', name: '北京售后客服部', resourceType: 'SERVICE_DEPT', department: '产品中心', bu: '醒市', mentor: '冯雪（客服主管）', mentorName: '冯雪', platform: '', location: '北京', capacity: 18, socialCount: 4, campusCount: 6, isActive: true },
  { id: 'MOCK_RS_12', resourceNo: 'SD0004', name: '深圳在线客服二部', resourceType: 'SERVICE_DEPT', department: '运营中心', bu: '醒市', mentor: '邓超（客服主管）', mentorName: '邓超', platform: '', location: '深圳', capacity: 30, socialCount: 9, campusCount: 14, isActive: true },
  { id: 'MOCK_RS_13', resourceNo: 'SD0005', name: '成都共享服务中心', resourceType: 'SERVICE_DEPT', department: '技术中心', bu: '能良', mentor: '罗静（客服主管）', mentorName: '罗静', platform: '', location: '成都', capacity: 22, socialCount: 3, campusCount: 8, isActive: true },
  { id: 'MOCK_RS_14', resourceNo: 'SD0006', name: '北京旧客服组', resourceType: 'SERVICE_DEPT', department: '产品中心', bu: '能良', mentor: '钱进（客服主管）', mentorName: '钱进', platform: '', location: '北京', capacity: 12, socialCount: 2, campusCount: 0, isActive: false },
  // —— 其他形态（OT+4）——
  { id: 'MOCK_RS_15', resourceNo: 'OT0001', name: '深圳共享培训场地', resourceType: 'OTHER', department: '运营中心', bu: '醒市', mentor: '周航（带教导师）', mentorName: '周航', platform: '', location: '深圳', capacity: 15, socialCount: 1, campusCount: 4, isActive: true },
]

/** 示例班级（ClassRoom 序列化字段）。 */
export const MOCK_CLASS_ROOMS: any[] = [
  // 2026-10-22：班级名称 = 从 1 开始的流水号；本页不再维护 班主任/HRBP/批次
  // （模型字段仍在，仅班级管理页不展示 —— hrbp 是行级隔离 scope 字段）。
  // stageCounts = 阶段分布（待分配 / 轮岗中 / 已完成），与 studentCount 对齐。
  { id: 'MOCK_CR_01', code: 'CL001', name: '1', batch: '2026秋招', headTeacher: '林曼（班主任）', hrbp: '刘婷（HRBP）', classMonitor: 'MOCK_U_1', classMonitorName: '周小舟（班长）', studentCount: 32, stageCounts: { PENDING: 8, ONGOING: 20, DONE: 4 }, isActive: true },
  { id: 'MOCK_CR_02', code: 'CL002', name: '2', batch: '2026秋招', headTeacher: '黄磊（班主任）', hrbp: '刘婷（HRBP）', classMonitor: 'MOCK_U_2', classMonitorName: '许一诺（班长）', studentCount: 28, stageCounts: { PENDING: 5, ONGOING: 19, DONE: 4 }, isActive: true },
  { id: 'MOCK_CR_03', code: 'CL003', name: '3', batch: '2026秋招', headTeacher: '冯雪（班主任）', hrbp: '赵敏（HRBP）', classMonitor: 'MOCK_U_3', classMonitorName: '赵小棠（班长）', studentCount: 26, stageCounts: { PENDING: 6, ONGOING: 17, DONE: 3 }, isActive: true },
  { id: 'MOCK_CR_04', code: 'CL004', name: '4', batch: '2026春招', headTeacher: '邓超（班主任）', hrbp: '赵敏（HRBP）', classMonitor: 'MOCK_U_4', classMonitorName: '林小满（班长）', studentCount: 24, stageCounts: { PENDING: 3, ONGOING: 16, DONE: 5 }, isActive: true },
  { id: 'MOCK_CR_05', code: 'CL005', name: '5', batch: '2026春招', headTeacher: '罗静（班主任）', hrbp: '刘婷（HRBP）', classMonitor: 'MOCK_U_5', classMonitorName: '陈小舟（班长）', studentCount: 19, stageCounts: { PENDING: 2, ONGOING: 13, DONE: 4 }, isActive: true },
  { id: 'MOCK_CR_06', code: 'CL006', name: '6', batch: '2025秋招', headTeacher: '邓超（班主任）', hrbp: '赵敏（HRBP）', classMonitor: 'MOCK_U_1', classMonitorName: '周小舟（班长）', studentCount: 0, stageCounts: { PENDING: 0, ONGOING: 0, DONE: 0 }, isActive: false },
]

/** 示例校招生档案（Person 序列化字段）。 */
export const MOCK_PERSONS: any[] = [
  // 2026-10-22（兵哥指令：列表列重排 + 筛选项增加）：补齐新列所需的字段
  //   mentorName 带教导师 / hrbpName HRBP / batch 批次 /
  //   rotationStatus 轮岗状态（code）+ rotationStatusLabel 中文 /
  //   rotationDept 当前轮岗部门 / overallScore 综合评分 /
  //   schoolName 真实校名（school 仍是院校标签）/ majorName 真实专业名
  { id: 'MOCK_PS_01', name: '张一鸣', employeeId: '25080001', status: '在职', expectedEntryDate: '2026-07-01', actualEntryDate: '2026-07-01', classRoomName: '1', headTeacherName: '林曼', bu: '能智BG', position: '技术研发', level: 'L2', sex: '男', school: '985', major: '工学', schoolName: '华中科技大学', majorName: '计算机科学与技术', mentorName: '陈志远', hrbpName: '刘婷', batch: '2026秋招', rotationStatus: 'ONGOING', rotationStatusLabel: '轮岗中', rotationDept: '技术中心', overallScore: 88.5 },
  { id: 'MOCK_PS_02', name: '李思远', employeeId: '25080002', status: '在职', expectedEntryDate: '2026-07-01', actualEntryDate: '2026-07-01', classRoomName: '1', headTeacherName: '林曼', bu: '能智BG', position: '产品', level: 'L2', sex: '女', school: '211', major: '工学', schoolName: '武汉理工大学', majorName: '工业工程', mentorName: '王建国', hrbpName: '刘婷', batch: '2026秋招', rotationStatus: 'ONGOING', rotationStatusLabel: '轮岗中', rotationDept: '产品中心', overallScore: 82.0 },
  { id: 'MOCK_PS_03', name: '王雨桐', employeeId: '25080003', status: '在职', expectedEntryDate: '2026-07-08', actualEntryDate: '2026-07-08', classRoomName: '2', headTeacherName: '黄磊', bu: '能智BG', position: '运营', level: 'L1', sex: '女', school: '双一流', major: '其他', schoolName: '南京邮电大学', majorName: '市场营销', mentorName: '李晓萌', hrbpName: '赵敏', batch: '2026秋招', rotationStatus: 'DONE', rotationStatusLabel: '已完成', rotationDept: '运营中心', overallScore: 91.2 },
  { id: 'MOCK_PS_04', name: '陈嘉禾', employeeId: '25080004', status: '在职', expectedEntryDate: '2026-07-08', actualEntryDate: '2026-07-08', classRoomName: '2', headTeacherName: '黄磊', bu: '能智BG', position: '技术研发', level: 'L3', sex: '男', school: '985', major: '工学', schoolName: '华中科技大学', majorName: '软件工程', mentorName: '陈志远', hrbpName: '赵敏', batch: '2026秋招', rotationStatus: 'ONGOING', rotationStatusLabel: '轮岗中', rotationDept: '技术中心', overallScore: 76.8 },
  { id: 'MOCK_PS_05', name: '刘星辰', employeeId: '25080005', status: '在职', expectedEntryDate: '2026-07-15', actualEntryDate: '2026-07-15', classRoomName: '3', headTeacherName: '冯雪', bu: '醒市', position: '职能', level: 'L2', sex: '男', school: '其他', major: '其他', schoolName: '湖北工业大学', majorName: '工商管理', mentorName: '钱进', hrbpName: '赵敏', batch: '2026秋招', rotationStatus: 'PENDING', rotationStatusLabel: '待分配', rotationDept: '醒市', overallScore: null },
  { id: 'MOCK_PS_06', name: '赵欣然', employeeId: '25080006', status: '在职', expectedEntryDate: '2026-07-15', actualEntryDate: '2026-07-15', classRoomName: '3', headTeacherName: '冯雪', bu: '醒市', position: '设计', level: 'L2', sex: '女', school: '211', major: '工学', schoolName: '武汉理工大学', majorName: '视觉传达设计', mentorName: '孙悦', hrbpName: '赵敏', batch: '2026秋招', rotationStatus: 'ONGOING', rotationStatusLabel: '轮岗中', rotationDept: '运营中心', overallScore: 85.4 },
  { id: 'MOCK_PS_07', name: '孙浩然', employeeId: '25080007', status: '在职', expectedEntryDate: '2026-07-22', actualEntryDate: '2026-07-22', classRoomName: '4', headTeacherName: '邓超', bu: '醒市', position: '销售', level: 'L1', sex: '男', school: '985', major: '其他', schoolName: '华中科技大学', majorName: '市场营销', mentorName: '李晓萌', hrbpName: '刘婷', batch: '2026春招', rotationStatus: 'APPROVING', rotationStatusLabel: '审批中', rotationDept: '技术中心', overallScore: 71.5 },
  { id: 'MOCK_PS_08', name: '周静怡', employeeId: '25080008', status: '在职', expectedEntryDate: '2026-07-22', actualEntryDate: '2026-07-22', classRoomName: '4', headTeacherName: '邓超', bu: '醒市', position: '技术研发', level: 'L2', sex: '女', school: '双一流', major: '工学', schoolName: '南京邮电大学', majorName: '通信工程', mentorName: '王建国', hrbpName: '刘婷', batch: '2026春招', rotationStatus: 'ONGOING', rotationStatusLabel: '轮岗中', rotationDept: '技术中心', overallScore: 90.1 },
  { id: 'MOCK_PS_09', name: '吴天佑', employeeId: '', status: '待入职', expectedEntryDate: '2026-08-03', actualEntryDate: '', classRoomName: '5', headTeacherName: '罗静', bu: '能良', position: '技术研发', level: 'L2', sex: '男', school: '211', major: '工学', schoolName: '武汉理工大学', majorName: '自动化', mentorName: '陈志远', hrbpName: '刘婷', batch: '2026春招', rotationStatus: 'PENDING', rotationStatusLabel: '待分配', rotationDept: '能良', overallScore: null },
  { id: 'MOCK_PS_10', name: '郑晓月', employeeId: '', status: '待入职', expectedEntryDate: '2026-08-03', actualEntryDate: '', classRoomName: '5', headTeacherName: '罗静', bu: '能良', position: '运营', level: 'L1', sex: '女', school: '其他', major: '其他', schoolName: '湖北工业大学', majorName: '市场营销', mentorName: '孙悦', hrbpName: '刘婷', batch: '2026春招', rotationStatus: 'PENDING', rotationStatusLabel: '待分配', rotationDept: '能良', overallScore: null },
  { id: 'MOCK_PS_11', name: '冯乐言', employeeId: '', status: '待入职', expectedEntryDate: '2026-08-17', actualEntryDate: '', classRoomName: '1', headTeacherName: '林曼', bu: '能智BG', position: '产品', level: 'L2', sex: '男', school: '985', major: '工学', schoolName: '华中科技大学', majorName: '工业工程', mentorName: '钱进', hrbpName: '刘婷', batch: '2026秋招', rotationStatus: 'PENDING', rotationStatusLabel: '待分配', rotationDept: '能智BG', overallScore: null },
  { id: 'MOCK_PS_12', name: '许可欣', employeeId: '', status: '待入职', expectedEntryDate: '2026-09-01', actualEntryDate: '', classRoomName: '', headTeacherName: '', bu: '能智BG', position: '技术研发', level: 'L1', sex: '女', school: '双一流', major: '工学', schoolName: '南京邮电大学', majorName: '计算机科学与技术', mentorName: '', hrbpName: '', batch: '', rotationStatus: '', rotationStatusLabel: '', rotationDept: '能智BG', overallScore: null },
  { id: 'MOCK_PS_13', name: '何俊杰', employeeId: '25050013', status: '离职', expectedEntryDate: '2025-07-01', actualEntryDate: '2025-07-01', classRoomName: '6', headTeacherName: '邓超', bu: '醒市', position: '技术研发', level: 'L2', sex: '男', school: '985', major: '工学', schoolName: '华中科技大学', majorName: '软件工程', mentorName: '陈志远', hrbpName: '赵敏', batch: '2025秋招', rotationStatus: 'TERMINATED', rotationStatusLabel: '已终止', rotationDept: '技术中心', overallScore: 58.3 },
]

/** 示例轮岗安排（RotationArrangement 序列化字段）。 */
export const MOCK_ROTATION_ARRANGEMENTS: any[] = [
  { id: 'MOCK_RA_01', personId: 10001, intentBu: '能智BG', currentDept: '技术中心', headTeacher: '林曼（班主任）', directManager: '王建国（直属上级）', classRoom: '1', stage: 'PENDING', employeeStatus: '待入职', finalDept: '', result: '', note: '待分配第一段轮岗', rotationStart: '', rotationEnd: '' },
  { id: 'MOCK_RA_02', personId: 10002, intentBu: '能智BG', currentDept: '产品中心', headTeacher: '黄磊（班主任）', directManager: '李晓萌（直属上级）', classRoom: '2', stage: 'PENDING', employeeStatus: '待入职', finalDept: '', result: '', note: '待确认带教导师', rotationStart: '', rotationEnd: '' },
  { id: 'MOCK_RA_03', personId: 10003, intentBu: '醒市', currentDept: '运营中心', headTeacher: '邓超（班主任）', directManager: '陈志远（直属上级）', classRoom: '4', stage: 'PENDING', employeeStatus: '待入职', finalDept: '', result: '', note: '待补充信息', rotationStart: '', rotationEnd: '' },
  { id: 'MOCK_RA_04', personId: 10004, intentBu: '能良', currentDept: '技术中心', headTeacher: '罗静（班主任）', directManager: '孙悦（直属上级）', classRoom: '5', stage: 'PENDING', employeeStatus: '待入职', finalDept: '', result: '', note: '', rotationStart: '', rotationEnd: '' },
  { id: 'MOCK_RA_05', personId: 10005, intentBu: '能智BG', currentDept: '技术中心', headTeacher: '林曼（班主任）', directManager: '王建国（直属上级）', classRoom: '1', stage: 'ONGOING', employeeStatus: '在职', finalDept: '', result: '', note: '第一段轮岗中', rotationStart: '2026-08-01', rotationEnd: '2026-08-28' },
  { id: 'MOCK_RA_06', personId: 10006, intentBu: '能智BG', currentDept: '产品中心', headTeacher: '黄磊（班主任）', directManager: '李晓萌（直属上级）', classRoom: '2', stage: 'ONGOING', employeeStatus: '在职', finalDept: '', result: '', note: '第一段轮岗中', rotationStart: '2026-08-01', rotationEnd: '2026-08-28' },
  { id: 'MOCK_RA_07', personId: 10007, intentBu: '醒市', currentDept: '运营中心', headTeacher: '邓超（班主任）', directManager: '陈志远（直属上级）', classRoom: '4', stage: 'ONGOING', employeeStatus: '在职', finalDept: '', result: '', note: '第二段轮岗中', rotationStart: '2026-08-20', rotationEnd: '2026-09-15' },
  { id: 'MOCK_RA_08', personId: 10008, intentBu: '醒市', currentDept: '产品中心', headTeacher: '冯雪（班主任）', directManager: '钱进（直属上级）', classRoom: '3', stage: 'ONGOING', employeeStatus: '在职', finalDept: '', result: '', note: '第一段轮岗中', rotationStart: '2026-08-05', rotationEnd: '2026-09-02' },
  { id: 'MOCK_RA_09', personId: 10009, intentBu: '能良', currentDept: '技术中心', headTeacher: '罗静（班主任）', directManager: '孙悦（直属上级）', classRoom: '5', stage: 'ONGOING', employeeStatus: '在职', finalDept: '', result: '', note: '第一段轮岗中', rotationStart: '2026-08-10', rotationEnd: '2026-09-07' },
  { id: 'MOCK_RA_10', personId: 10010, intentBu: '能智BG', currentDept: '产品中心', headTeacher: '林曼（班主任）', directManager: '李晓萌（直属上级）', classRoom: '1', stage: 'DONE', employeeStatus: '在职', finalDept: '技术中心', result: '优秀', note: '轮岗完成，已定岗', rotationStart: '2026-06-01', rotationEnd: '2026-06-26' },
  { id: 'MOCK_RA_11', personId: 10011, intentBu: '醒市', currentDept: '运营中心', headTeacher: '邓超（班主任）', directManager: '陈志远（直属上级）', classRoom: '4', stage: 'DONE', employeeStatus: '在职', finalDept: '运营中心', result: '合格', note: '轮岗完成', rotationStart: '2026-06-01', rotationEnd: '2026-06-26' },
  { id: 'MOCK_RA_12', personId: 10012, intentBu: '能智BG', currentDept: '技术中心', headTeacher: '黄磊（班主任）', directManager: '王建国（直属上级）', classRoom: '2', stage: 'DONE', employeeStatus: '离职', finalDept: '产品中心', result: '待改进', note: '考核不达标，已终止', rotationStart: '2026-05-06', rotationEnd: '2026-05-31' },
]

/**
 * 把示例行里按**名字**引用的部门换成真实 id。
 *
 * @param rows        示例行（department / bu 字段填的是部门名）
 * @param departments 部门列表（来自 department store，字段 id / name）
 * @returns          新数组：department / bu 变为 id（换不到则保留原名字），
 *                   并补 departmentName / buName 供 BU 汇总聚合与展示使用
 */
export function resolveDeptRefs<T extends { department?: any; bu?: any }>(
  rows: T[],
  departments: any[],
): T[] {
  const idByName = new Map<string, string>()
  ;(departments || []).forEach((d: any) => {
    if (d?.name && d?.id != null) idByName.set(String(d.name), String(d.id))
  })
  const toId = (v: any) => (v == null ? v : idByName.get(String(v)) ?? v)
  return rows.map((row) => {
    const next: any = { ...row }
    if (next.department != null) {
      next.departmentName = String(next.department)
      next.department = toId(next.department)
    }
    if (next.bu != null) {
      next.buName = String(next.bu)
      next.bu = toId(next.bu)
    }
    return next as T
  })
}

/**
 * 由示例轮岗资源聚合出 BU 汇总（四段式：直播间 / 客服部门 / 其他 / 总数据）。
 * 与后端 `GET /campus-rotation/resources/bu-summary/` 的结构一致，
 * 保证「资源测算页签」的数字与「轮岗资源页签」的示例行自洽。
 *
 * ⚠️ 2026-10-22：直播间 + 客服部门合并为一张资源表后，按 `resourceType` 分段，
 *    每段各自算 count 与 capacity（不再共用一个 capacity 池）。
 */
export function buildMockBuSummary(resources: any[]) {
  type Seg = { buId: string | null; buName: string; anchorCount: number; csCount: number; otherCount: number; capacity: number }
  const agg = new Map<string, Seg>()
  const touch = (name: string) => {
    const key = name || '未分配'
    if (!agg.has(key)) {
      agg.set(key, { buId: null, buName: key, anchorCount: 0, csCount: 0, otherCount: 0, capacity: 0 })
    }
    return agg.get(key)!
  }
  ;(resources || []).forEach((r) => {
    const row = touch(r.buName || r.bu || '未分配')
    const used = r.campusCount || 0
    if (r.resourceType === 'SERVICE_DEPT') row.csCount += used
    else if (r.resourceType === 'OTHER') row.otherCount += used
    else row.anchorCount += used
  })
  const list = [...agg.values()].sort((a, b) => a.buName.localeCompare(b.buName))
  const rate = (count: number, capacity: number) => (capacity > 0 ? count / capacity : null)
  const live = list.map((r) => ({
    buId: r.buId,
    buName: r.buName,
    anchorCount: r.anchorCount,
    capacity: r.capacity,
    usedRate: rate(r.anchorCount, r.capacity),
  }))
  const service = list.map((r) => ({
    buId: r.buId,
    buName: r.buName,
    csCount: r.csCount,
    capacity: r.capacity,
    usedRate: rate(r.csCount, r.capacity),
  }))
  const other = list.map((r) => ({
    buId: r.buId,
    buName: r.buName,
    otherCount: r.otherCount,
    capacity: r.capacity,
    usedRate: rate(r.otherCount, r.capacity),
  }))
  const liveAnchorTotal = live.reduce((s, r) => s + r.anchorCount, 0)
  const serviceTotal = service.reduce((s, r) => s + r.csCount, 0)
  const otherTotal = other.reduce((s, r) => s + r.otherCount, 0)
  return {
    live,
    service,
    other,
    total: {
      liveAnchorTotal,
      serviceTotal,
      otherTotal,
      grandTotal: liveAnchorTotal + serviceTotal + otherTotal,
      buList: list.map((r) => ({ buId: r.buId, buName: r.buName })),
    },
  }
}

/* ========================================================================
 * 个人档案（示例数据聚合）
 * ----------------------------------------------------------------------
 * 背景：示例行的 id 形如 `MOCK_PS_01`，**后端没有这条记录** —— 若点姓名
 *      走真实接口 `GET /campus/persons/MOCK_PS_01/profile/` 必然 404。
 *      故示例数据下由本地把 mock 行拼成与后端同构的档案载荷，弹窗直接渲染，
 *      不发任何请求（与「示例数据只读、不落库」的约定一致）。
 * ======================================================================== */

/** 院校标签 → 院校名称（档案详情「院校名称」展示项）。 */
const MOCK_SCHOOL_NAMES: Record<string, string> = {
  '985': '华中科技大学',
  '211': '武汉理工大学',
  '双一流': '南京邮电大学',
  '其他': '湖北工业大学',
}

/** 由示例班级行反查（按班级名）。 */
function findMockClassRoom(name: string) {
  if (!name) return null
  return MOCK_CLASS_ROOMS.find((c) => c.name === name) || null
}

/**
 * 把示例校招生行拼成「个人档案」载荷（结构与后端 `GET /campus/persons/{id}/profile/`
 * 的 `data` 逐字段对齐）。
 *
 * @param p MOCK_PERSONS 中的一行
 */
export function buildMockPersonProfile(p: any) {
  const classRoom = findMockClassRoom(p?.classRoomName || '')
  return {
    person: {
      id: p?.id || '',
      code: p?.id || '',
      name: p?.name || '',
      employeeId: p?.employeeId || '',
      status: p?.status || '',
      sex: p?.sex || '',
      bu: p?.bu || '',
      position: p?.position || '',
      level: p?.level || '',
      school: p?.school || '',
      schoolName: MOCK_SCHOOL_NAMES[p?.school] || p?.school || '',
      major: p?.major || '',
      education: '本科',
      phone: '',
      month: '8月',
      expectedEntryDate: p?.expectedEntryDate || '',
      actualEntryDate: p?.actualEntryDate || '',
      counted: true,
      classRoomId: classRoom?.id || '',
      classRoomName: p?.classRoomName || '',
      headTeacherId: '',
      headTeacherName: p?.headTeacherName || '',
      mentorId: '',
      mentorName: '',
      batch: classRoom?.batch || '',
    },
    classRoom: classRoom
      ? {
          id: classRoom.id,
          code: classRoom.code,
          name: classRoom.name,
          batch: classRoom.batch || '',
          headTeacher: classRoom.headTeacher || '',
          hrbp: classRoom.hrbp || '',
          studentCount: classRoom.studentCount ?? 0,
        }
      : null,
    rotation: null,
    stats: {
      rotationAvgScore: null,
      monthlyAvgScore: null,
      overallScore: null,
      rank: null,
      rating: null,
    },
    stages: [],
    monthlyAssessments: [],
    dailyReports: [],
    recommendations: [],
    feedbacks: [],
  }
}
