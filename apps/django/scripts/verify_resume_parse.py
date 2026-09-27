#!/usr/bin/env python3
# verify_resume_parse.py — 一键验证「上传简历 → 解析」链路（SmartResume 修复后验收用）
#
# 用途: 登录 → 上传 PDF → 轮询 parse-status 直到 done/failed，打印解析结果。
# 验证 SmartResume 本地模型免 apikey 修复在生产/本地是否真正打通。
#
# 纯标准库实现（urllib），无需 pip install requests。
#
# 用法:
#   python3 verify_resume_parse.py --pdf resume.pdf \
#       --username admin --password '******' \
#       --url https://ats.lokisong.cloud:9908
#
#   凭据也可走环境变量: ATS_USER / ATS_PASS
#   本地后端: 加 --url http://localhost:8000
#
# 退出码: 0=全部 job done 且有解析结果; 1=有 job failed / 超时 / 上传/登录失败
import argparse
import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.request

API_PREFIX = "/api/v1"
LOGIN_PATH = f"{API_PREFIX}/auth/login/"
UPLOAD_PATH = f"{API_PREFIX}/candidates/add-candidate/upload-and-parse/"
STATUS_PATH = f"{API_PREFIX}/candidates/add-candidate/parse-status/{{job_id}}/"


def _guess_ct(fn):
    ext = os.path.splitext(fn)[1].lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")


def _http(method, url, token=None, json_body=None, multipart=None, timeout=30):
    """multipart = (body_bytes, content_type)"""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if multipart is not None:
        data, ct = multipart
        headers["Content-Type"] = ct
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw[:500]}
        return e.code, body
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def login(base, username, password):
    status, body = _http("POST", base + LOGIN_PATH,
                         json_body={"username": username, "password": password})
    if status != 200 or not body.get("success"):
        raise SystemExit(f"[LOGIN FAILED] HTTP {status}: {json.dumps(body, ensure_ascii=False)}")
    token = (body.get("data") or {}).get("access")
    if not token:
        raise SystemExit(f"[LOGIN FAILED] 响应缺少 data.access: {json.dumps(body, ensure_ascii=False)}")
    return token


def build_multipart(file_paths, field="files"):
    boundary = "----verifyboundary" + uuid.uuid4().hex
    crlf = b"\r\n"
    body = b""
    for fp in file_paths:
        fn = os.path.basename(fp)
        with open(fp, "rb") as f:
            data = f.read()
        body += b"--" + boundary.encode() + crlf
        body += (f'Content-Disposition: form-data; name="{field}"; filename="{fn}"').encode() + crlf
        body += (f"Content-Type: {_guess_ct(fn)}").encode() + crlf + crlf
        body += data + crlf
    body += b"--" + boundary.encode() + b"--" + crlf
    return body, f"multipart/form-data; boundary={boundary}"


def upload(base, token, pdfs):
    mp = build_multipart(pdfs)
    status, body = _http("POST", base + UPLOAD_PATH, token=token, multipart=mp)
    if status != 202:
        raise SystemExit(f"[UPLOAD FAILED] HTTP {status}: {json.dumps(body, ensure_ascii=False)}")
    job_ids = body.get("job_ids") or []
    if not job_ids:
        raise SystemExit(f"[UPLOAD FAILED] 响应无 job_ids: {json.dumps(body, ensure_ascii=False)}")
    return job_ids


def poll(base, token, job_id, timeout, interval):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        status, body = _http("GET", base + STATUS_PATH.format(job_id=job_id), token=token)
        if status != 200:
            print(f"  [job {job_id}] 状态查询 HTTP {status}: {json.dumps(body, ensure_ascii=False)}")
            time.sleep(interval)
            continue
        st = body.get("status")
        prog = body.get("progress")
        print(f"  [job {job_id}] status={st} progress={prog}")
        last = body
        if st in ("done", "failed"):
            return body
        time.sleep(interval)
    print(f"  [job {job_id}] 超时（{timeout}s 内未到终态）")
    return last


def _summarize(parsed):
    if not parsed:
        return "(无 parsed 数据)"
    keys = ["name", "phone", "email", "gender", "age", "education", "school",
            "major", "workYears", "currentCompany", "currentTitle",
            "name", "phone", "email"]
    # parsed 可能是嵌套 dict，抽取常见一级字段
    flat = {}
    for k in ("name", "phone", "email", "gender", "age", "education", "school",
              "major", "workYears", "currentCompany", "currentTitle"):
        if isinstance(parsed, dict) and k in parsed and parsed[k]:
            flat[k] = parsed[k]
    return json.dumps(flat, ensure_ascii=False) if flat else "(parsed 为空或无关键字段)"


def main():
    ap = argparse.ArgumentParser(description="一键验证简历解析链路")
    ap.add_argument("--url", default="https://ats.lokisong.cloud:9908",
                    help="ATS 后端 base URL（默认生产；本地用 http://localhost:8000）")
    ap.add_argument("--username", default=os.environ.get("ATS_USER"), required=False)
    ap.add_argument("--password", default=os.environ.get("ATS_PASS"), required=False)
    ap.add_argument("--pdf", nargs="+", required=True, help="一个或多个简历文件（pdf/doc/docx/txt）")
    ap.add_argument("--timeout", type=int, default=120, help="单 job 轮询超时秒数（默认 120）")
    ap.add_argument("--interval", type=float, default=2.0, help="轮询间隔秒数（默认 2.0）")
    args = ap.parse_args()

    if not args.username or not args.password:
        ap.error("必须提供 --username/--password 或通过环境变量 ATS_USER/ATS_PASS 提供凭据")

    for fp in args.pdf:
        if not os.path.isfile(fp):
            raise SystemExit(f"[ERROR] 文件不存在: {fp}")

    base = args.url.rstrip("/")
    print(f"==> 后端: {base}")
    token = login(base, args.username, args.password)
    print("[OK] 登录成功")

    job_ids = upload(base, token, args.pdf)
    print(f"[OK] 上传成功，job_ids={job_ids}")

    all_done = True
    for jid in job_ids:
        print(f"==> 轮询 job {jid} ...")
        res = poll(base, token, jid, args.timeout, args.interval)
        st = (res or {}).get("status")
        err = (res or {}).get("error")
        if st == "failed":
            all_done = False
            print(f"  [FAIL] job {jid} 解析失败: error={err}")
        elif st == "done":
            print(f"  [DONE] job {jid} 解析完成")
            print(f"        解析摘要: {_summarize((res or {}).get('parsed'))}")
        else:
            all_done = False
            print(f"  [TIMEOUT/UNKNOWN] job {jid} status={st} error={err}")

    print("\n==> 结论:", "全部解析完成 ✅" if all_done else "存在失败/未完成的 job ❌")
    sys.exit(0 if all_done else 1)


if __name__ == "__main__":
    main()
