"""从简历文件抽取纯文本（轻量、本地，供 Career Core 等文本型引擎消费）。

仅依赖 pdfplumber（懒加载）；不支持扫描件 OCR —— Career Core 本身也只吃文本。
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Tuple

logger = logging.getLogger(__name__)


def extract_text(file_obj: Any) -> str:
    """用 pdfplumber 抽取 PDF 文本；缺失库或无文本层时抛清晰错误。"""
    data = _read_bytes(file_obj)
    try:
        import pdfplumber  # 懒加载，避免无谓依赖
    except ImportError as e:
        raise RuntimeError(
            "缺少 pdfplumber，无法抽取简历文本；请 pip install pdfplumber"
        ) from e

    tmp_path = _dump_temp(data)
    try:
        chunks = []
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
        text = "\n".join(chunks)
    finally:
        _safe_unlink(tmp_path)

    if not text.strip():
        raise RuntimeError("简历无可读文本层（可能是扫描件；Career Core 暂不支持 OCR）")
    return text


def to_path(file_obj: Any) -> Tuple[str, bool]:
    """返回磁盘路径：(path, is_temp)。调用方用毕自行清理临时文件。"""
    name = getattr(file_obj, "name", None)
    if name and os.path.exists(name):
        return name, False
    data = _read_bytes(file_obj)
    path = _dump_temp(data)
    return path, True


def _dump_temp(data: bytes) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(data)
    finally:
        tmp.close()
    return tmp.name


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _read_bytes(file_obj: Any) -> bytes:
    if hasattr(file_obj, "read"):
        data = file_obj.read()
        if hasattr(file_obj, "seek"):
            try:
                file_obj.seek(0)
            except (OSError, ValueError):  # 简历文件 seek(0) 失败不影响主流程 (parser 会从当前位置继续读取)
                pass
        if isinstance(data, str):
            return data.encode("utf-8")
        return bytes(data)
    if isinstance(file_obj, (bytes, bytearray)):
        return bytes(file_obj)
    raise ValueError("无法读取简历文件对象")
