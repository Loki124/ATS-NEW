import { customAlphabet } from 'nanoid';
import { createActor } from 'xstate';
import { referralCodeMachine } from '../machines/referralCode.machine.js';

const nanoid = customAlphabet(
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
  6
);

const MAX_RETRIES = 10;

export function generateCode() {
  return nanoid();
}

export async function createCodeForUser(prisma, userId) {
  const existing = await prisma.referralCode.findUnique({ where: { userId } });
  if (existing) return existing;

  let code;
  for (let i = 0; i < MAX_RETRIES; i++) {
    code = generateCode();
    const conflict = await prisma.referralCode.findUnique({ where: { code } });
    if (!conflict) break;
    if (i === MAX_RETRIES - 1) {
      code = `${code}${Date.now().toString(36).slice(-4)}`;
    }
  }

  return prisma.referralCode.create({
    data: { userId, code, status: 'ACTIVE' },
  });
}

export async function invalidateCode(prisma, codeId, reason) {
  const code = await prisma.referralCode.findUnique({ where: { id: codeId } });
  if (!code) throw new Error('内推码不存在');

  const actor = createActor(referralCodeMachine).start();
  actor.send({ type: 'INVALIDATE', reason });
  const snap = actor.getSnapshot();

  if (snap.value !== 'INVALID') {
    throw new Error(`invalid reason 无效: ${reason}`);
  }

  return prisma.referralCode.update({
    where: { id: codeId },
    data: { status: 'INVALID', invalidReason: reason },
  });
}

export async function validateCode(prisma, code) {
  const rc = await prisma.referralCode.findUnique({ where: { code } });
  if (!rc) return { valid: false, reason: 'NOT_FOUND' };
  if (rc.status !== 'ACTIVE') {
    return { valid: false, reason: rc.invalidReason ?? 'INVALID' };
  }
  return { valid: true, code: rc };
}

export async function refreshCodesForEvent(prisma, event) {
  if (event.type !== 'USER_LEAVER') return [];
  if (!event.userId) throw new Error('USER_LEAVER 事件必须提供 userId');

  const code = await prisma.referralCode.findUnique({ where: { userId: event.userId } });
  if (!code || code.status === 'INVALID') return [];

  await invalidateCode(prisma, code.id, 'LEAVER');
  return [code];
}
