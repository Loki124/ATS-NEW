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
from typing import Dict, List

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

#: 2026-10-08 (#17 / S-07): 各扩展名允许的「文件头魔数」(content sniffing), 防伪造扩展名。
#: 旧版 Office (doc/xls/ppt, OLE2) 与新版 (docx/xlsx/pptx, ZIP) 及 zip 压缩包共用
#: OLE2 / PK 签名, 无法靠魔数区分, 故归为同一类接受。
#: 纯文本 (txt/csv) 不靠魔数, 单独按「可 utf-8 解码且无 NUL 字节」校验。
EXT_SIGS: Dict[str, List[bytes]] = {
    '.pdf': [b'%PDF'],
    '.png': [b'\x89PNG\r\n\x1a\n'],
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.gif': [b'GIF87a', b'GIF89a'],
    '.webp': [b'RIFF'],                 # 另需 head[8:12] == b'WEBP'
    '.bmp': [b'BM'],
    '.doc': [b'\xd0\xcf\x11\xe0'],
    '.xls': [b'\xd0\xcf\x11\xe0'],
    '.ppt': [b'\xd0\xcf\x11\xe0'],
    '.docx': [b'PK\x03\x04'],
    '.xlsx': [b'PK\x03\x04'],
    '.pptx': [b'PK\x03\x04'],
    '.zip': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
    '.rar': [b'Rar!\x1a\x07'],
    '.txt': [],                        # 纯文本类: 见 _magic_ok
    '.csv': [],
}
_TEXT_EXT = {'.txt', '.csv'}


def _ext(file) -> str:
    return os.path.splitext(file.name or '')[1].lower()


def _magic_ok(ext: str, head: bytes) -> bool:
    if ext in _TEXT_EXT:
        # 纯文本: 必须能按 utf-8 解码且无 NUL 字节 (防二进制伪装成文本触发解析器漏洞)
        if b'\x00' in head:
            return False
        try:
            head.decode('utf-8')
        except UnicodeDecodeError:
            return False
        return True
    sigs = EXT_SIGS.get(ext)
    if not sigs:
        return True  # 未知扩展 (正常不会发生, ALLOWED_EXT 已卡过)
    for sig in sigs:
        if head.startswith(sig):
            if ext == '.webp' and head[8:12] != b'WEBP':
                continue
            return True
    return False


def check_magic_bytes(ext: str, file) -> None:
    """content sniffing: 文件头必须与扩展名声明的类型一致, 否则拒绝 (防伪造扩展名上传恶意文件)。"""
    file.seek(0)
    head = file.read(512)
    file.seek(0)
    if not _magic_ok(ext, head):
        raise ValueError(f'文件内容与扩展名「{ext or "未知"}」不符, 疑似伪造类型')


def _validate(file) -> None:
    if not file:
        raise ValueError('未收到文件')
    if getattr(file, 'size', 0) <= 0:
        raise ValueError('文件内容为空')
    if file.size > MAX_UPLOAD:
        raise ValueError(f'文件大小 {file.size // 1024}KB 超过 {MAX_UPLOAD // 1024}KB 上限')
    ext = _ext(file)
    if ext not in ALLOWED_EXT:
        raise ValueError(f'不支持的文件类型「{ext or "未知"}」，仅允许图片/文档/压缩包')
    # 2026-10-08 (#17): 扩展名白名单只是第一道, 真正拦伪造靠魔数校验
    check_magic_bytes(ext, file)


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
    # 2026-10-08 (#17): 下载鉴权。开启 SECURE_MEDIA_DOWNLOAD 后, 返回经鉴权的
    # 下载端点 URL (由 MediaDownloadView 校验登录后流式吐文件), 而非直接暴露 MEDIA_URL。
    # 默认关闭, 保证 dev / 无对象存储场景行为与前端现有消费方式兼容。
    if getattr(settings, 'SECURE_MEDIA_DOWNLOAD', False):
        url = f'/api/v1/media/secure/{saved}'
    else:
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
