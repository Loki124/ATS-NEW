"""通用文件上传存储服务 (2026-09-16, 兵哥: 动态字段附件 / 组合字段图片)。

对外唯一入口 ``save_upload(file) -> dict``，返回 ``{id, name, url, size, content_type}``。
存储后端由 ``settings.STORAGE_PROVIDER`` 决定:

- ``local`` (默认): 落 ``MEDIA_ROOT`` (复用 Django default_storage + media 静态服务),
  ``id`` = 相对路径, ``url`` = ``MEDIA_URL + 相对路径``。dev / 无对象存储配置时走此路。
- ``cos``   (腾讯云 COS): 走 ``cos-python-sdk-v5``。缺 SDK 或缺失密钥配置时**自动回退 local**
  并打 warning，保证功能在 dev 永远可跑（prod 配齐 COS_SECRET_ID/KEY/BUCKET/REGION 即走对象存储）。
  Aliyun OSS 同构可后续替换。

附件值约定: 前端存 ``[{id, name, url}]`` (ATTACHMENT) 或 ``{subKey: <值>}`` (COMPOSITE 子字段为附件时同结构)。
"""
import logging
import os
import time
import uuid

from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

#: 允许上传的扩展名（图片 / 文档 / 压缩包）
ALLOWED_EXT = {
    '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.txt', '.csv', '.zip', '.rar',
}
#: 单文件上限 20MB
MAX_UPLOAD = 20 * 1024 * 1024


def _ext(file) -> str:
    return os.path.splitext(file.name or '')[1].lower()


def _validate(file) -> None:
    if not file:
        raise ValueError('未收到文件')
    if file.size > MAX_UPLOAD:
        raise ValueError(f'文件大小 {file.size // 1024}KB 超过 {MAX_UPLOAD // 1024}KB 上限')
    ext = _ext(file)
    if ext not in ALLOWED_EXT:
        raise ValueError(f'不支持的文件类型「{ext or "未知"}」，仅允许图片/文档/压缩包')


def save_upload(file) -> dict:
    """保存上传文件，返回 ``{id, name, url, size, content_type}``。

    Raises:
        ValueError: 校验失败（类型/大小）时，由调用方转 400。
    """
    _validate(file)
    provider = getattr(settings, 'STORAGE_PROVIDER', 'local')
    if provider == 'cos':
        return _save_cos(file)
    return _save_local(file)


def _save_local(file) -> dict:
    ext = _ext(file)
    rel = f'uploads/{time.strftime("%Y%m%d")}/{uuid.uuid4().hex}{ext}'
    saved = default_storage.save(rel, file)
    url = settings.MEDIA_URL + saved
    return {
        'id': saved,
        'name': file.name,
        'url': url,
        'size': file.size,
        'content_type': file.content_type or '',
    }


def _save_cos(file) -> dict:
    """腾讯云 COS 后端; 任何缺失(SDK/密钥)都回退 local 并告警。"""
    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        logger.warning('cos-python-sdk-v5 未安装, 回退本地存储')
        return _save_local(file)

    secret_id = getattr(settings, 'COS_SECRET_ID', '')
    secret_key = getattr(settings, 'COS_SECRET_KEY', '')
    bucket = getattr(settings, 'COS_BUCKET', '')
    region = getattr(settings, 'COS_REGION', '')
    if not (secret_id and secret_key and bucket and region):
        logger.warning('COS 配置缺失 (COS_SECRET_ID/KEY/BUCKET/REGION), 回退本地存储')
        return _save_local(file)

    ext = _ext(file)
    key = f'uploads/{time.strftime("%Y%m%d")}/{uuid.uuid4().hex}{ext}'
    client = CosS3Client(CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key))
    # file 为 Django UploadedFile (类文件对象), put_object Body 直接收 file-like。
    client.put_object(
        Bucket=bucket,
        Body=file,
        Key=key,
        ContentType=file.content_type or 'application/octet-stream',
    )
    domain = getattr(settings, 'COS_DOMAIN', '') or f'https://{bucket}.cos.{region}.myqcloud.com'
    url = f'{domain.rstrip("/")}/{key}'
    return {
        'id': key,
        'name': file.name,
        'url': url,
        'size': file.size,
        'content_type': file.content_type or '',
    }
