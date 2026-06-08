// G8 - 字段级 ACL 中间件 (在 route handler 之前注入, res.json 时自动应用)

import { PrismaClient } from '@prisma/client';
import { applyFieldAcl } from '../services/field-masking.service.js';

// 独立 PrismaClient 实例 - 避免 import app.js 触发 app.listen
const prisma = new PrismaClient();

export function fieldAcl(resource, options = {}) {
  return async (req, res, next) => {
    try {
      // SUPER_ADMIN 跳过
      if (req.user?.roleType === 'SUPER_ADMIN') return next();

      // 加载规则 (允许测试覆盖)
      const rules = options.rules ?? await prisma.fieldAclRule.findMany({
        where: { resource, isActive: true },
        orderBy: { priority: 'desc' },
      });

      // 角色过滤
      const userRoleCodes = req.user?.roles || [];
      const applicableRules = rules.filter(r =>
        !r.roleCode || userRoleCodes.includes(r.roleCode)
      );

      req.fieldAclRules = applicableRules;

      // 包装 res.json
      const originalJson = res.json.bind(res);
      res.json = (body) => {
        if (body?.data) {
          body.data = applyFieldAcl(body.data, applicableRules);
        }
        return originalJson(body);
      };

      // 异步审计 (失败不阻塞响应) - 允许测试注入 auditFn
      const auditFn = options.auditFn ?? ((data) => {
        prisma.fieldAclAudit.create({ data }).catch(() => {});
      });
      setImmediate(() => {
        const maskedFields = applicableRules.filter(r => r.action !== 'VIEW');
        if (maskedFields.length > 0) {
          maskedFields.forEach(r => {
            auditFn({
              userId: req.user.id,
              userName: req.user.name || '',
              resource,
              field: r.field,
              action: r.action,
              result: r.action,
              ip: req.ip,
              ua: req.get?.('user-agent')?.slice(0, 255),
            });
          });
        }
      });

      next();
    } catch (err) {
      next(err);
    }
  };
}
