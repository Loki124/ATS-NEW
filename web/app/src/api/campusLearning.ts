/**
 * 校招学习与社区（campus_learning）· API。
 *
 * 后端挂 /api/v1/campus-learning/，camelCase 自动转换（请求体也转，故前端传 isEnabled）。
 *
 * 端点（技术契约 §3.2）：
 *  - courses/            课程 CRUD，?type=&form=&enabled=
 *  - learn-progress/     学习进度 CRUD，?person=&course=；{id}/record/ 记学习记录（累加进度与时长）
 *  - learn-records/      学习记录 CRUD
 *  - exams/              考试 CRUD；{id}/ranking/ 考试排名（分数降序 + 通过判定 + 得分条百分比）
 *  - exam-scores/        考试成绩 CRUD（后端按 score >= pass_score 判定 passed，前端只展示）
 *  - activities/         活动 CRUD
 *  - activity-scores/    活动评分 CRUD（reward 文本形如「+3 分」）
 *  - forum-boards/       论坛板块 CRUD
 *  - forum-posts/        论坛帖 CRUD，?board=&kw=
 *  - stats/learn-board/  学习龙虎榜（每人 { id, name, class, minutes, done, avgProg, total }，按 minutes 降序）
 *
 * 响应契约：列表 GET 集合 → { count, results }（DRF 分页）或 { success, data } 信封；
 * 单对象 POST/PUT → 裸对象或信封。本模块统一在导出前解包，页面侧只拿数组 / 对象。
 */
import { api } from '../utils/request'

/** 列表解包：兼容 { success, data } 信封与 DRF 分页 { count, results }。 */
const listData = <T>(r: any): T[] => (r?.data?.data ?? r?.data?.results ?? []) as T[]
/** 对象解包：兼容 { success, data } 信封与裸对象。 */
const objData = <T>(r: any): T => (r?.data?.data ?? r?.data) as T

/* ============================ 类型定义 ============================ */

/** 课程（契约 §3.1 Course）。 */
export interface Course {
  id: string
  code: string
  name: string
  /** 直播 / 录播 / 面授 / 线上 */
  form: string
  /** 时长（分钟） */
  durationMin: number
  category: string
  /** 必修 / 选修 */
  type: string
  /** 是否需要结课考试 */
  examRequired: boolean
  enabled: boolean
  description: string
  /** 列表接口带出的完成情况（已完成人数 / 总人数），后端缺省时前端回落为 '—' */
  doneCount?: number
  totalCount?: number
}

/** 学习进度（LearnProgress）。 */
export interface LearnProgress {
  id: string
  person: string
  personName?: string
  course: string
  courseName?: string
  /** 进度百分比 0-100 */
  progress: number
  /** 累计学习分钟 */
  minutes: number
  doneAt: string | null
  lastAt: string
}

/** 学习记录（LearnRecord）。 */
export interface LearnRecord {
  id: string
  person: string
  personName?: string
  course: string
  courseName?: string
  date: string
  start: string
  minutes: number
  remark: string
}

/** 考试（Exam）。 */
export interface Exam {
  id: string
  name: string
  date: string
  /** 线上 / 线下 */
  form: string
  fullScore: number
  passScore: number
  course: string | null
  courseName?: string
  enabled: boolean
}

/** 考试成绩（ExamScore）：passed 由后端按 score >= exam.pass_score 判定。 */
export interface ExamScore {
  id: string
  exam: string
  examName?: string
  person: string
  personName?: string
  className?: string
  score: number
  passed: boolean
  remark: string
}

/** 考试排名行（GET exams/{id}/ranking/）。 */
export interface ExamRankingRow {
  rank: number
  person: string
  personName: string
  className?: string
  score: number
  passed: boolean
  /** 得分条百分比（0-100） */
  percent: number
}

/** 活动（Activity）。 */
export interface Activity {
  id: string
  name: string
  type: string
  date: string
  /** 未开始 / 进行中 / 已结束 */
  status: string
  /** 奖励，形如「+3 分」 */
  reward: string
  rule: string
  enabled: boolean
}

/** 活动评分（ActivityScore）。 */
export interface ActivityScore {
  id: string
  activity: string
  activityName?: string
  person: string
  personName?: string
  score: number
  reward: string
  rank: number | null
}

/** 论坛板块（ForumBoard）。 */
export interface ForumBoard {
  id: string
  name: string
  description: string
  sort: number
  enabled: boolean
}

/** 论坛帖（ForumPost）。 */
export interface ForumPost {
  id: string
  board: string
  boardName?: string
  title: string
  content: string
  author: string | null
  authorName?: string
  person: string | null
  personName?: string
  replyCount: number
  pinned: boolean
  createdAt?: string
}

/** 学习龙虎榜行（GET stats/learn-board/）。 */
export interface LearnBoardRow {
  id: string
  name: string
  /** 班级 */
  class: string
  /** 累计学习分钟 */
  minutes: number
  /** 完成课程数 */
  done: number
  /** 平均进度 */
  avgProg: number
  /** 课程总数 */
  total: number
}

/* ============================ 课程 ============================ */

/** 课程列表。 */
export const listCourses = (params?: { type?: string; form?: string; enabled?: boolean; search?: string }) =>
  api
    .get('/campus-learning/courses/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<Course>(r))

export const createCourse = (payload: Partial<Course> & { name: string }) =>
  api.post('/campus-learning/courses/', payload).then((r) => objData<Course>(r))

export const updateCourse = (id: string, payload: Partial<Course>) =>
  api.put(`/campus-learning/courses/${id}/`, payload).then((r) => objData<Course>(r))

export const deleteCourse = (id: string) => api.delete(`/campus-learning/courses/${id}/`).then((r) => r.data)

/** 恢复已删除课程（软删模型统一 restore 动作，端点口径同 campusControl 的 restoreDimension）。 */
export const restoreCourse = (id: string) => api.post(`/campus-learning/courses/${id}/restore/`).then((r) => r.data)

/* ============================ 学习进度 / 学习记录 ============================ */

/** 学习进度列表（我的课程视图的数据源）。 */
export const listLearnProgress = (params?: { person?: string; course?: string }) =>
  api
    .get('/campus-learning/learn-progress/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<LearnProgress>(r))

/** 记学习记录：写 LearnRecord 并累加 progress / minutes。 */
export const recordLearnProgress = (
  id: string,
  payload: { date?: string; start?: string; minutes: number; remark?: string },
) => api.post(`/campus-learning/learn-progress/${id}/record/`, payload).then((r) => objData<LearnProgress>(r))

/** 学习记录列表。 */
export const listLearnRecords = (params?: { person?: string; course?: string }) =>
  api
    .get('/campus-learning/learn-records/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<LearnRecord>(r))

export const createLearnRecord = (payload: Partial<LearnRecord> & { person: string; course: string }) =>
  api.post('/campus-learning/learn-records/', payload).then((r) => objData<LearnRecord>(r))

export const deleteLearnRecord = (id: string) => api.delete(`/campus-learning/learn-records/${id}/`).then((r) => r.data)

/* ============================ 考试 / 成绩 ============================ */

/** 考试列表。 */
export const listExams = (params?: { enabled?: boolean; search?: string }) =>
  api
    .get('/campus-learning/exams/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<Exam>(r))

export const createExam = (payload: Partial<Exam> & { name: string }) =>
  api.post('/campus-learning/exams/', payload).then((r) => objData<Exam>(r))

export const updateExam = (id: string, payload: Partial<Exam>) =>
  api.put(`/campus-learning/exams/${id}/`, payload).then((r) => objData<Exam>(r))

export const deleteExam = (id: string) => api.delete(`/campus-learning/exams/${id}/`).then((r) => r.data)

/** 恢复已删除考试。 */
export const restoreExam = (id: string) => api.post(`/campus-learning/exams/${id}/restore/`).then((r) => r.data)

/** 考试排名（分数降序 + 通过判定 + 得分条百分比）。 */
export const getExamRanking = (examId: string) =>
  api.get(`/campus-learning/exams/${examId}/ranking/`).then((r) => listData<ExamRankingRow>(r))

/** 成绩列表。 */
export const listExamScores = (params?: { exam?: string; person?: string }) =>
  api
    .get('/campus-learning/exam-scores/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<ExamScore>(r))

export const createExamScore = (payload: Partial<ExamScore> & { exam: string; person: string; score: number }) =>
  api.post('/campus-learning/exam-scores/', payload).then((r) => objData<ExamScore>(r))

export const updateExamScore = (id: string, payload: Partial<ExamScore>) =>
  api.put(`/campus-learning/exam-scores/${id}/`, payload).then((r) => objData<ExamScore>(r))

export const deleteExamScore = (id: string) => api.delete(`/campus-learning/exam-scores/${id}/`).then((r) => r.data)

/* ============================ 活动 ============================ */

/** 活动列表。 */
export const listActivities = (params?: { enabled?: boolean; search?: string }) =>
  api
    .get('/campus-learning/activities/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<Activity>(r))

export const createActivity = (payload: Partial<Activity> & { name: string }) =>
  api.post('/campus-learning/activities/', payload).then((r) => objData<Activity>(r))

export const updateActivity = (id: string, payload: Partial<Activity>) =>
  api.put(`/campus-learning/activities/${id}/`, payload).then((r) => objData<Activity>(r))

export const deleteActivity = (id: string) => api.delete(`/campus-learning/activities/${id}/`).then((r) => r.data)

/** 恢复已删除活动。 */
export const restoreActivity = (id: string) => api.post(`/campus-learning/activities/${id}/restore/`).then((r) => r.data)

/** 活动评分列表。 */
export const listActivityScores = (params?: { activity?: string; person?: string }) =>
  api
    .get('/campus-learning/activity-scores/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<ActivityScore>(r))

export const createActivityScore = (payload: Partial<ActivityScore> & { activity: string; person: string }) =>
  api.post('/campus-learning/activity-scores/', payload).then((r) => objData<ActivityScore>(r))

export const updateActivityScore = (id: string, payload: Partial<ActivityScore>) =>
  api.put(`/campus-learning/activity-scores/${id}/`, payload).then((r) => objData<ActivityScore>(r))

export const deleteActivityScore = (id: string) => api.delete(`/campus-learning/activity-scores/${id}/`).then((r) => r.data)

/* ============================ 论坛 ============================ */

/** 论坛板块列表。 */
export const listForumBoards = (params?: { enabled?: boolean }) =>
  api
    .get('/campus-learning/forum-boards/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<ForumBoard>(r))

export const createForumBoard = (payload: Partial<ForumBoard> & { name: string }) =>
  api.post('/campus-learning/forum-boards/', payload).then((r) => objData<ForumBoard>(r))

export const updateForumBoard = (id: string, payload: Partial<ForumBoard>) =>
  api.put(`/campus-learning/forum-boards/${id}/`, payload).then((r) => objData<ForumBoard>(r))

export const deleteForumBoard = (id: string) => api.delete(`/campus-learning/forum-boards/${id}/`).then((r) => r.data)

/** 论坛帖列表（?board= 板块过滤，?kw= 关键词搜索）。 */
export const listForumPosts = (params?: { board?: string; kw?: string }) =>
  api
    .get('/campus-learning/forum-posts/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<ForumPost>(r))

export const createForumPost = (payload: Partial<ForumPost> & { board: string; title: string; content: string }) =>
  api.post('/campus-learning/forum-posts/', payload).then((r) => objData<ForumPost>(r))

export const updateForumPost = (id: string, payload: Partial<ForumPost>) =>
  api.put(`/campus-learning/forum-posts/${id}/`, payload).then((r) => objData<ForumPost>(r))

export const deleteForumPost = (id: string) => api.delete(`/campus-learning/forum-posts/${id}/`).then((r) => r.data)

/** 恢复已删除帖子。 */
export const restoreForumPost = (id: string) => api.post(`/campus-learning/forum-posts/${id}/restore/`).then((r) => r.data)

/* ============================ 学习龙虎榜 ============================ */

/** 学习龙虎榜：按累计学习分钟降序，排除已离职。 */
export const getLearnBoard = () =>
  api.get('/campus-learning/stats/learn-board/').then((r) => listData<LearnBoardRow>(r))
