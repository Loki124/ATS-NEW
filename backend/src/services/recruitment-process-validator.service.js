/**
 * 招聘流程创建/更新 payload 校验 - Plan L Task 7
 *
 *  - name: 2-50 字符
 *  - description: ≤ 100 字符 (可选)
 *
 * 抛 AppError(400) 当校验失败
 */

import { AppError } from '../middleware/error.middleware.js';

export function validateProcessPayload(name, description) {
  if (name !== undefined && name !== null) {
    const n = String(name).trim();
    if (n.length < 2 || n.length > 50) {
      throw new AppError(`流程名称长度需在 2-50 字符之间 (当前: ${n.length})`, 400);
    }
  }
  if (description !== undefined && description !== null && String(description).length > 0) {
    const d = String(description);
    if (d.length > 100) {
      throw new AppError(`流程描述长度不可超过 100 字符 (当前: ${d.length})`, 400);
    }
  }
}
