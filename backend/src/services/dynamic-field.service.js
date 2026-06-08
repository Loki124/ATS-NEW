/**
 * G42 - 动态字段元数据 + 校验 service
 */

import { prisma } from '../app.js';

export async function listFieldsForResource(resource) {
  const list = await prisma.fieldDefinition.findMany({
    where: { resource, status: 'ACTIVE' },
  });
  // 服务端做一次排序以保稳定 (Prisma orderBy 也加了, 但 mock 没传 orderBy 时由服务兜底)
  return list.sort((a, b) => (a.orderIndex || 0) - (b.orderIndex || 0));
}

export async function getFieldByKey(resource, fieldKey) {
  return prisma.fieldDefinition.findUnique({
    where: { resource_fieldKey: { resource, fieldKey } },
    include: { options: { orderBy: { orderIndex: 'asc' } } },
  });
}

export async function getFieldWithOptions(id) {
  return prisma.fieldDefinition.findUnique({
    where: { id },
    include: { options: { orderBy: { orderIndex: 'asc' } } },
  });
}

export async function upsertField({ id, resource, fieldKey, label, fieldType, isRequired, isVisible, placeholder, helpText, defaultValue, validation, orderIndex, groupName, options }) {
  const data = {
    resource, fieldKey, label, fieldType,
    isRequired: !!isRequired, isVisible: isVisible !== false,
    placeholder, helpText, defaultValue,
    validation: typeof validation === 'string' ? validation : JSON.stringify(validation || {}),
    orderIndex: orderIndex || 0, groupName,
  };
  const field = id
    ? await prisma.fieldDefinition.update({ where: { id }, data })
    : await prisma.fieldDefinition.upsert({
        where: { resource_fieldKey: { resource, fieldKey } },
        create: data, update: data,
      });

  if (Array.isArray(options)) {
    await prisma.fieldOption.deleteMany({ where: { fieldId: field.id } });
    for (let i = 0; i < options.length; i++) {
      const o = options[i];
      await prisma.fieldOption.create({
        data: { fieldId: field.id, value: o.value, label: o.label, orderIndex: i, isActive: true },
      });
    }
  }
  return field;
}

export async function deleteField(id) {
  return prisma.fieldDefinition.update({ where: { id }, data: { status: 'INACTIVE' } });
}

export async function reorderFields(orderedIds) {
  for (let i = 0; i < orderedIds.length; i++) {
    await prisma.fieldDefinition.update({
      where: { id: orderedIds[i] },
      data: { orderIndex: i },
    });
  }
}

export function validateFieldValue(field, value) {
  if (field.isRequired && (value == null || value === '')) return false;
  if (value == null || value === '') return true;

  switch (field.fieldType) {
    case 'TEXT': return typeof value === 'string';
    case 'NUMBER': return !isNaN(Number(value));
    case 'BOOLEAN': return typeof value === 'boolean' || value === 'true' || value === 'false';
    case 'DATE': return !isNaN(Date.parse(value));
    case 'SELECT': return Array.isArray(field.options) && field.options.some((o) => o.value === value);
    case 'MULTISELECT': return Array.isArray(value);
    default: return true;
  }
}
