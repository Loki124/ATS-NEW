import { body, param, query } from 'express-validator';

export const validateCodeQuery = [
  query('code').isString().isLength({ min: 6, max: 16 }),
];

export const createExpertConfigValidators = [
  body('teamId').isUUID(),
  body('expertId').isUUID(),
  body('isPrimary').optional().isBoolean(),
];

export const createRuleValidators = [
  body('name').isString().isLength({ min: 1, max: 64 }),
  body('ruleType').isIn(['MEMBER_RESTRICTION', 'REWARD']),
  body('positionLevel').optional().isString(),
  body('triggerStage').optional().isIn(['ONBOARDED', 'PROBATION_PASSED']),
  body('amount').optional().isFloat({ min: 0 }),
  body('conditions').isObject(),
];

export const createRecordValidators = [
  body('candidateId').isUUID(),
  body('positionId').isUUID(),
  body('resumeId').optional().isUUID(),
  body('expertId').optional().isUUID(),
  body('referralType').isIn(['REFERRER_HELP', 'CANDIDATE_USED_CODE']),
];
