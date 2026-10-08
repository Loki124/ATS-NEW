#!/usr/bin/env python3
# =============================================================================
# ATS-NEW 本地运维看板（单文件，零依赖，系统 python3 即可运行）
# -----------------------------------------------------------------------------
# 作用：在浏览器里查看 dev 服务（BE/FE/Celery/MySQL/Redis）的实时状态，并一键启停/重启。
# 原理：本服务作为用户会话里的真实进程运行（在你的终端里启动），因此具备
#       launchctl 权限，可通过 bootstrap/bootout/kickstart 控制 launchd 代理。
#       注意：本脚本不能由 WorkBuddy 的 Bash 启动（App Sandbox 会拦 launchctl）。
# 启动：python3 scripts/ops_dashboard.py
# 访问：http://localhost:8099
# 端口：默认 8099，可用环境变量 OPS_PORT 或命令行参数 --port 覆盖。
# =============================================================================
import os
import sys
import re
import json
import time
import socket
import collections
import subprocess
import http.server
import socketserver
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LAUNCH_DIR = os.path.expanduser("~/Library/LaunchAgents")
LOG_DIR = os.path.join(PROJECT_DIR, ".run-logs")
OPS_LOG_PATH = os.path.join(LOG_DIR, "ops-last.log")
UID = os.getuid()

# ---------------------------------------------------------------------------
# 通用命令执行（看板自身健壮性：失败必须兜底而非崩溃）
# ---------------------------------------------------------------------------
def _run(cmd, timeout=20, cwd=None, env=None):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=cwd, env=env)
    except Exception as e:  # noqa: BLE001 - 看板自身健壮性，失败需兜底而非崩溃
        class _R:
            stdout = ""
            stderr = str(e)
            returncode = -1
        return _R()

# 服务定义：key -> (launchd label, 展示名, 端口或 None, 健康 URL 或 None)
SERVICES = {
    "be": {
        "label": "com.ats.dev.be",
        "name": "Django 后端",
        "port": 8000,
        "health_url": "http://127.0.0.1:8000/health/",
        "plist": "com.ats.dev.be.plist",
    },
    "fe": {
        "label": "com.ats.dev.fe",
        "name": "Vite 前端",
        "port": 5212,
        "health_url": "http://localhost:5212/",
        "plist": "com.ats.dev.fe.plist",
    },
    "celery": {
        "label": "com.ats.dev.celery",
        "name": "Celery Worker",
        "port": None,
        "health_url": None,
        "plist": "com.ats.dev.celery.plist",
    },
    "mysql": {
        "label": "homebrew.mxcl.mysql",
        "name": "MySQL 数据库",
        "port": 3306,
        "health_url": None,
        "tcp": ("127.0.0.1", 3306),
        "plist": "homebrew.mxcl.mysql.plist",
    },
    "redis": {
        "label": "homebrew.mxcl.redis",
        "name": "Redis 缓存",
        "port": 6379,
        "health_url": None,
        "tcp": ("127.0.0.1", 6379),
        "plist": "homebrew.mxcl.redis.plist",
    },
}

# 应用服务（拉取代码后只需重启这三个，不必动数据库/缓存）
DEV_KEYS = ("be", "fe", "celery")

# 时间序列环形缓冲：每次状态轮询采样一次，用于趋势 sparkline
HISTORY = collections.defaultdict(lambda: collections.deque(maxlen=120))   # 每服务指标历史
SYS_HISTORY = collections.deque(maxlen=120)                                # 系统指标历史

PAGE_SIZE = 4096


def _vm_page_size():
    out = _run(["vm_stat"]).stdout or ""
    m = re.search(r"page size of\s+(\d+)\s+bytes", out)
    return int(m.group(1)) if m else 4096


PAGE_SIZE = _vm_page_size()


def parse_etime(etime):
    """解析 ps etime：[[dd-]hh:]mm:ss -> 秒。失败返回 None。"""
    et = (etime or "").strip()
    days = 0
    if "-" in et:
        d, et = et.split("-", 1)
        try:
            days = int(d)
        except ValueError:
            days = 0
    parts = et.split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            h, m, s = 0, int(parts[0]), int(parts[1])
        else:
            h, m, s = 0, 0, int(parts[0])
        return days * 86400 + h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        return None


def proc_tree(pid):
    """返回 pid 及其全部后代进程 pid 列表（用于汇总整服务的资源占用）。"""
    if not pid:
        return []
    seen = {str(pid)}
    pids = [str(pid)]
    frontier = [str(pid)]
    for _ in range(6):
        nxt = []
        for p in frontier:
            r = _run(["pgrep", "-P", p])
            for c in r.stdout.split():
                if c not in seen:
                    seen.add(c)
                    nxt.append(c)
                    pids.append(c)
        if not nxt:
            break
        frontier = nxt
    return pids


def proc_stats(pid):
    """汇总某服务进程树的 CPU/内存/进程数/运行时间。沙箱或无 ps 时返回 None。"""
    pids = proc_tree(pid)
    if not pids:
        return None
    rss = 0.0
    cpu = 0.0
    n = 0
    uptime = None
    for i, p in enumerate(pids):
        r = _run(["ps", "-o", "%cpu=,rss=,etime=", "-p", p])
        line = (r.stdout or "").strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            c = float(parts[0])
            m = float(parts[1])
        except ValueError:
            continue
        cpu = max(cpu, c)
        rss += m
        n += 1
        if i == 0 and len(parts) >= 3:
            uptime = parse_etime(parts[2])
    if n == 0:
        return None
    return {"cpu": round(cpu, 1), "mem_mb": round(rss / 1024.0, 1),
            "procs": n, "uptime": uptime}


ERR_RE = re.compile(r"traceback|exception|error|fatal|\b50\d\b", re.I)
REQ_RE = re.compile(r'"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+\S+\s+HTTP')


def _log_paths(key):
    return [
        os.path.join(LOG_DIR, f"{key}-wrapper.log"),
        os.path.join(LOG_DIR, f"{key}-stderr.log"),
        os.path.join(LOG_DIR, f"{key}-stdout.log"),
    ]


def _scan_logs(key, window=None, count_re=None):
    """扫描服务日志。window=None 时无时间过滤；count_re 命中则计数。
    返回 (错误行数, 命中 count_re 的行数)。"""
    now = time.time()
    err_cnt = 0
    hit_cnt = 0
    for p in _log_paths(key):
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", errors="replace") as f:
                lines = f.read().splitlines()[-3000:]
        except Exception:  # noqa: BLE001
            continue
        for ln in lines:
            recent = True
            ts = None
            m = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", ln)
            if m:
                try:
                    ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
                    recent = (now - ts) <= (window or 0)
                except Exception:  # noqa: BLE001
                    recent = True
            if window and not recent:
                continue
            if ERR_RE.search(ln):
                err_cnt += 1
            if count_re and count_re.search(ln):
                hit_cnt += 1
    return err_cnt, hit_cnt


def error_count(key, window=300):
    """统计服务近 window 秒内的错误关键字行数。"""
    err, _ = _scan_logs(key, window=window, count_re=None)
    return err


def request_count(key, window=60):
    """统计服务近 window 秒内的 HTTP 请求数（runserver 会逐请求打印访问行）。"""
    _, hit = _scan_logs(key, window=window, count_re=REQ_RE)
    return hit


def system_metrics():
    """采集系统级指标：负载 / 内存 / 磁盘。"""
    out = {}
    lo = _run(["sysctl", "-n", "vm.loadavg"]).stdout or ""
    m = re.search(r"([\d.]+)\s+([\d.]+)\s+([\d.]+)", lo)
    if m:
        out["load1"] = float(m.group(1))
        out["load5"] = float(m.group(2))
        out["load15"] = float(m.group(3))
    else:
        out["load1"] = out["load5"] = out["load15"] = None
    vm = _run(["vm_stat"]).stdout or ""

    def _pg(name):
        mm = re.search(r"Pages\s+" + re.escape(name) + r":\s+(\d+)", vm)
        return int(mm.group(1)) if mm else 0

    free = _pg("free")
    active = _pg("active")
    inactive = _pg("inactive")
    spec = _pg("speculative")
    wired = _pg("wired down")
    used_pages = active + inactive + spec + wired
    total_pages = used_pages + free
    mem_used = used_pages * PAGE_SIZE
    mem_total = total_pages * PAGE_SIZE
    out["mem_used_pct"] = round(mem_used / mem_total * 100, 1) if mem_total else None
    out["mem_used_gb"] = round(mem_used / 1024 ** 3, 1)
    out["mem_total_gb"] = round(mem_total / 1024 ** 3, 1)
    d = _run(["df", "-h", "/"]).stdout or ""
    lines = [l for l in d.splitlines() if l]
    pct = re.search(r"(\d+)%", lines[-1]) if lines else None
    out["disk_used_pct"] = int(pct.group(1)) if pct else None
    out["cores"] = os.cpu_count() or 1
    return out


PORT = int(os.environ.get("OPS_PORT", "8099"))
if "--port" in sys.argv:
    try:
        PORT = int(sys.argv[sys.argv.index("--port") + 1])
    except (IndexError, ValueError):
        pass


def launchctl_list():
    out = _run(["launchctl", "list"]).stdout or ""
    rows = {}
    for line in out.splitlines():
        parts = line.split()
        if not parts or len(parts) < 3:
            continue
        label = parts[-1]
        pid_field = parts[0].strip()
        if pid_field != "-":
            rows[label] = pid_field
    return rows


def tcp_port_open(host, port, timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:  # noqa: BLE001 - 探活失败即视为端口不通
        return False


def http_health(url):
    if not url:
        return None
    r = _run(["curl", "--noproxy", "*", "-s", "-o", "/dev/null",
              "-w", "%{http_code}", "--max-time", "3", url])
    code = (r.stdout or "").strip()
    return code or None


def tail_log(key, n=40):
    lines = []
    for p in _log_paths(key):
        if os.path.exists(p):
            try:
                with open(p, "r", errors="replace") as f:
                    lines.extend(f.read().splitlines()[-n:])
            except Exception:  # noqa: BLE001
                pass
    return lines[-n:] if lines else ["（暂无日志）"]


def service_status(key, push=True):
    svc = SERVICES[key]
    loaded = launchctl_list()
    pid = loaded.get(svc["label"])
    running = pid is not None
    if svc.get("health_url"):
        code = http_health(svc["health_url"])
        health_ok = code == "200"
        health_txt = f"HTTP {code}" if code else "无响应"
    elif svc.get("tcp"):
        host, port = svc["tcp"]
        health_ok = tcp_port_open(host, port)
        health_txt = "端口开放" if health_ok else "端口不通"
    else:
        # celery 无监听端口：以 worker 进程是否存活判定
        health_ok = running
        health_txt = "worker 进程存活" if running else "无 worker 进程"
    proc = proc_stats(pid) if running else None
    err = error_count(key)
    req = request_count(key) if running else 0
    up = 1 if (running and health_ok) else 0
    if push:
        HISTORY[key].append({
            "ts": int(time.time()),
            "cpu": (proc or {}).get("cpu"),
            "mem_mb": (proc or {}).get("mem_mb"),
            "err": err,
            "req": req,
            "up": up,
        })
    return {
        "key": key,
        "name": svc["name"],
        "label": svc["label"],
        "port": svc["port"],
        "has_http": bool(svc.get("health_url")),
        "loaded": svc["label"] in loaded,
        "running": running,
        "pid": pid,
        "health_ok": health_ok,
        "health_txt": health_txt,
        "proc": proc,
        "errors_5m": err,
        "req_pm": req,
        "log": tail_log(key),
    }


def build_system(push=True):
    m = system_metrics()
    if push:
        SYS_HISTORY.append({
            "ts": int(time.time()),
            "load1": m.get("load1"),
            "mem_used_pct": m.get("mem_used_pct"),
            "disk_used_pct": m.get("disk_used_pct"),
        })
    return m


def do_action(key, action):
    """对单个服务执行 start/stop/restart。start 幂等：运行中不重复拉起。"""
    svc = SERVICES[key]
    label = svc["label"]
    plist = os.path.join(LAUNCH_DIR, svc["plist"])

    def _bootstrap():
        if not os.path.exists(plist):
            # plist 缺失则回退到安装脚本重建全部
            _run(["bash", os.path.join(SCRIPT_DIR, "install_dev_launchd.sh")])
            return f"plist 缺失，已重跑安装脚本重建 {svc['name']}"
        _run(["launchctl", "bootout", f"gui/{UID}/{label}"])
        _run(["launchctl", "bootstrap", f"gui/{UID}", plist])
        return f"已请求{'重启' if action == 'restart' else '启动'} {svc['name']}"

    if action == "stop":
        _run(["launchctl", "bootout", f"gui/{UID}/{label}"])
        return f"已请求停止 {svc['name']}"
    if action == "start":
        loaded = launchctl_list()
        if label in loaded and loaded[label]:
            return f"{svc['name']} 已在运行（PID {loaded[label]}），无需启动"
        if label in loaded:
            # 已加载但进程不在 → kickstart 直接拉起
            _run(["launchctl", "kickstart", "-k", f"gui/{UID}/{label}"])
            return f"已请求启动 {svc['name']}"
        return _bootstrap()
    # restart：先卸后装（幂等），RunAtLoad 会自动拉起
    return _bootstrap()


def do_all(action):
    if action == "start":
        missing = [k for k in SERVICES
                   if not os.path.exists(os.path.join(LAUNCH_DIR, SERVICES[k]["plist"]))]
        if missing:
            _run(["bash", os.path.join(SCRIPT_DIR, "install_dev_launchd.sh")])
            return "检测到 plist 缺失，已重跑安装脚本启动全部服务"
        for k in SERVICES:
            do_action(k, "start")
        return "已请求启动全部服务"
    if action == "stop":
        for k in SERVICES:
            do_action(k, "stop")
        return "已请求停止全部服务"
    if action == "restart":
        for k in SERVICES:
            do_action(k, "restart")
        return "已请求重启全部服务"
    return "未知操作"


def _write_op_log(title, text):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(OPS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n=== {title} @ {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n{text}\n")
    except Exception:  # noqa: BLE001
        pass


def read_op_log(n=200):
    if not os.path.exists(OPS_LOG_PATH):
        return ["（暂无操作记录）"]
    try:
        with open(OPS_LOG_PATH, "r", errors="replace") as f:
            return f.read().splitlines()[-n:]
    except Exception:  # noqa: BLE001
        return ["（日志读取失败）"]


def do_migrate():
    """执行 Django 全量数据库迁移（用项目 venv 的 python + dev settings）。"""
    venv_py = os.path.join(PROJECT_DIR, "apps", "django", ".venv", "bin", "python")
    if not os.path.exists(venv_py):
        venv_py = "python3"
    django_dir = os.path.join(PROJECT_DIR, "apps", "django")
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="config.settings.dev",
               PYTHONUNBUFFERED="1")
    r = _run([venv_py, "manage.py", "migrate"], timeout=180, cwd=django_dir, env=env)
    out = (r.stdout or "") + (r.stderr or "")
    _write_op_log("数据库迁移 migrate", out)
    return out.strip() or "（无输出）"


def do_pull_restart():
    """git 拉取最新代码（仅 fast-forward，避免破坏本地未提交改动），随后重启应用服务。
    只重启 be/fe/celery 三个应用服务，不必动 MySQL/Redis。"""
    r = _run(["git", "-C", PROJECT_DIR, "pull", "--ff-only"], timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    restarted = []
    for k in DEV_KEYS:
        do_action(k, "restart")
        restarted.append(SERVICES[k]["name"])
    summary = f"git pull --ff-only 输出：\n{out}\n\n已重启：{', '.join(restarted)}"
    _write_op_log("拉取代码并重启", summary)
    return summary


# ---------------------------------------------------------------------------
# HTTP 处理
# ---------------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, DASHBOARD_HTML, "text/html; charset=utf-8")
        elif parsed.path == "/api/status":
            services = [service_status(k) for k in SERVICES]
            sys_m = build_system()
            spark = {k: list(HISTORY[k]) for k in SERVICES}
            payload = {
                "services": services,
                "system": sys_m,
                "spark": spark,
                "sys_history": list(SYS_HISTORY),
                "ts": int(time.time()),
            }
            self._send(200, json.dumps(payload, ensure_ascii=False))
        elif parsed.path == "/api/op-log":
            self._send(200, json.dumps({"log": read_op_log()}, ensure_ascii=False))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:  # noqa: BLE001
            payload = {}
        if parsed.path == "/api/action":
            key = payload.get("key", "all")
            action = payload.get("action", "")
            if key == "all":
                msg = do_all(action)
            elif key in SERVICES and action in ("start", "stop", "restart"):
                msg = do_action(key, action)
            elif action in ("migrate", "pull_restart"):
                msg = do_migrate() if action == "migrate" else do_pull_restart()
            else:
                msg = "参数错误"
            self._send(200, json.dumps({"ok": True, "msg": (msg or "")[:500]}, ensure_ascii=False))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, fmt, *args):
        pass  # 安静


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="color-scheme" content="dark" />
<title>ATS-NEW 运维监控看板</title>
<style>
  :root{
    --bg:#0b0f17; --panel:#111827; --panel2:#0f172a; --border:#1f2937;
    --text:#e5e7eb; --muted:#94a3b8; --faint:#64748b;
    --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444;
    --blue:#60a5fa; --amber:#fbbf24; --violet:#a78bfa; --green2:#34d399;
    --brand:#f43f5e;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
    background:radial-gradient(1200px 600px at 80% -10%,#15203a 0%,var(--bg) 55%);
    color:var(--text);min-height:100vh;padding:20px;max-width:1280px;margin:0 auto}
  /* 顶栏 */
  header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;
    padding:14px 18px;border:1px solid var(--border);border-radius:16px;
    background:linear-gradient(180deg,rgba(244,63,94,.10),rgba(17,24,39,.6));
    backdrop-filter:blur(6px);margin-bottom:18px}
  .title{display:flex;align-items:center;gap:12px}
  .title .logo{width:10px;height:34px;border-radius:4px;background:linear-gradient(180deg,var(--brand),#fb7185);box-shadow:0 0 16px rgba(244,63,94,.5)}
  h1{font-size:20px;margin:0;font-weight:700;letter-spacing:.3px}
  h1 small{display:block;color:var(--muted);font-weight:400;font-size:12px;margin-top:2px}
  .clock{font-size:12px;color:var(--muted);margin-top:3px}
  .global{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  button{cursor:pointer;border:none;border-radius:9px;padding:9px 15px;font-size:13px;font-weight:600;color:#fff;
    transition:.15s;font-family:inherit}
  button:disabled{opacity:.5;cursor:not-allowed}
  .btn-start{background:#16a34a} .btn-stop{background:#dc2626}
  .btn-restart{background:#2563eb} .btn-refresh{background:#334155}
  .btn-migrate{background:var(--warn);color:#1f2937} .btn-pull{background:#7c3aed}
  button:hover:not(:disabled){filter:brightness(1.12)}
  .live{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
  .live i{width:8px;height:8px;border-radius:50%;background:var(--ok);box-shadow:0 0 8px var(--ok);animation:pulse 1.6s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  /* KPI 条 */
  .section-h{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;
    margin:22px 4px 10px;display:flex;align-items:center;gap:8px}
  .section-h::before{content:"";width:3px;height:14px;border-radius:2px;background:var(--brand)}
  .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:14px}
  .kpi{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:14px 16px;
    display:flex;flex-direction:column;gap:6px;position:relative;overflow:hidden}
  .kpi::after{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent,var(--border))}
  .kpi-label{font-size:12px;color:var(--muted)}
  .kpi-val{font-size:26px;font-weight:800;line-height:1;color:var(--accent,var(--text))}
  .kpi-val .u{font-size:13px;color:var(--faint);font-weight:600;margin-left:3px}
  .kpi-sub{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px;min-height:18px}
  .pill{font-size:11px;padding:2px 8px;border-radius:999px;font-weight:700}
  .pill.ok{background:rgba(34,197,94,.15);color:var(--ok)}
  .pill.bad{background:rgba(239,68,68,.15);color:var(--bad)}
  .na{color:var(--faint);font-size:12px}
  .spark{display:block}
  /* 系统资源 */
  .sys-grid{display:flex;gap:14px;flex-wrap:wrap}
  .gauge-card{flex:1;min-width:220px;background:var(--panel);border:1px solid var(--border);border-radius:14px;
    padding:16px;display:flex;align-items:center;gap:16px}
  .gauge-meta{flex:1;min-width:0}
  .g-name{font-size:13px;color:var(--muted)}
  .g-val{font-size:22px;font-weight:800;margin:2px 0}
  .g-val .u{font-size:12px;color:var(--faint);font-weight:600;margin-left:4px}
  .g-sub{font-size:11px;color:var(--faint)}
  /* 服务网格 */
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:16px;
    box-shadow:0 1px 2px rgba(0,0,0,.3);position:relative;overflow:hidden}
  .card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--edge,var(--border))}
  .card.ok{--edge:var(--ok)} .card.bad{--edge:var(--bad)} .card.off{--edge:var(--faint)}
  .card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
  .card-title{font-size:16px;font-weight:700;display:flex;align-items:center;gap:9px;min-width:0}
  .dot{width:10px;height:10px;border-radius:50%;flex:none;box-shadow:0 0 8px currentColor}
  .port{font-size:12px;color:var(--faint);font-weight:500;margin-left:6px}
  .badge{font-size:12px;padding:4px 11px;border-radius:999px;font-weight:700;white-space:nowrap}
  .badge.ok{background:rgba(34,197,94,.16);color:var(--ok)}
  .badge.bad{background:rgba(239,68,68,.16);color:var(--bad)}
  .badge.off{background:rgba(100,116,139,.18);color:var(--muted)}
  .health{font-size:12px;color:var(--muted);margin:8px 0 10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .dots{display:inline-flex;gap:2px;vertical-align:middle}
  .dots i{width:5px;height:10px;border-radius:1px;display:inline-block}
  .dots i.on{background:var(--ok)} .dots i.off{background:#334155}
  .metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
  .m{background:var(--panel2);border:1px solid var(--border);border-radius:9px;padding:8px 9px}
  .m-k{font-size:11px;color:var(--faint);margin-bottom:3px}
  .m-v{font-size:14px;font-weight:700}
  .sparks{display:flex;gap:10px;margin-bottom:10px}
  .spark-box{flex:1;background:var(--panel2);border:1px solid var(--border);border-radius:9px;padding:8px 10px}
  .spark-l{font-size:11px;color:var(--faint);margin-bottom:2px}
  .actions{display:flex;gap:8px}
  .actions .b{flex:1;padding:7px 0;font-size:13px;border-radius:8px}
  .b.start{background:#16a34a} .b.restart{background:#2563eb} .b.stop{background:#dc2626}
  .log-toggle{font-size:12px;color:var(--blue);cursor:pointer;user-select:none;margin-top:10px;display:inline-block}
  .log{background:#060911;color:#cbd5e1;border:1px solid var(--border);border-radius:9px;padding:10px;
    font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;line-height:1.5;
    max-height:170px;overflow:auto;white-space:pre-wrap;word-break:break-all;margin-top:8px}
  /* 运维日志 */
  .ops-panel{margin-top:8px;background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:14px 16px}
  .ops-head{font-size:13px;color:var(--muted);cursor:pointer;user-select:none;display:flex;align-items:center;gap:8px}
  .ops-head .chev{transition:.2s}
  .ops-panel.open .ops-head .chev{transform:rotate(90deg)}
  .ops-log{margin-top:10px;background:#060911;color:#cbd5e1;border:1px solid var(--border);border-radius:9px;
    padding:10px;font-family:ui-monospace,Menlo,monospace;font-size:11px;line-height:1.55;
    max-height:240px;overflow:auto;white-space:pre-wrap;word-break:break-all;display:none}
  .ops-panel.open .ops-log{display:block}
  footer{margin-top:26px;color:var(--faint);font-size:12px;text-align:center}
  .toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:#0b0f17;color:#fff;
    border:1px solid var(--border);padding:10px 18px;border-radius:10px;font-size:13px;opacity:0;
    transition:.25s;pointer-events:none;max-width:80vw;z-index:50}
  .toast.show{opacity:1}
  @media (max-width:560px){
    .kpi-val{font-size:22px} .metrics{grid-template-columns:repeat(2,1fr)}
    .gauge-card{min-width:100%}
  }
</style>
</head>
<body>
<header>
  <div class="title">
    <div class="logo"></div>
    <div>
      <h1>ATS-NEW 运维监控看板<small>本地 Dev 服务 · 实时巡检</small></h1>
      <div class="clock" id="clock">连接中…</div>
    </div>
  </div>
  <div class="global">
    <span class="live"><i></i> 自动刷新 5s</span>
    <button class="btn-refresh" onclick="load()">↻ 刷新</button>
    <button class="btn-start" onclick="act('all','start')">▸ 启动全部</button>
    <button class="btn-restart" onclick="act('all','restart')">⟳ 全部重启</button>
    <button class="btn-stop" onclick="act('all','stop')">■ 停止全部</button>
  </div>
  <div class="global" style="width:100%;margin-top:4px">
    <button class="btn-migrate" onclick="op('migrate')">🗄 数据库迁移</button>
    <button class="btn-pull" onclick="op('pull_restart')">⬇ 拉取代码并重启</button>
  </div>
</header>

<div class="section-h">核心指标</div>
<div class="kpi-grid" id="kpi"></div>

<div class="section-h">系统资源</div>
<div class="sys-grid" id="sys"></div>

<div class="section-h">服务健康</div>
<div class="grid" id="grid"></div>

<div class="section-h">运维操作日志</div>
<div class="ops-panel" id="ops">
  <div class="ops-head" onclick="toggleOps()"><span class="chev">▸</span> 迁移 / 拉取重启 输出</div>
  <pre class="ops-log" id="opslog"></pre>
</div>

<footer>本看板运行在你的本地终端进程中，通过 launchctl 控制 dev 服务。仅用于本地开发运维，不对外暴露。</footer>
<div class="toast" id="toast"></div>

<script>
const ORDER=["be","fe","celery","mysql","redis"];
let STATE={cores:1};

function esc(t){return (t==null?'':String(t)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function fmtUptime(s){
  if(s==null) return '—';
  s=Math.floor(s);
  const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60),sec=s%60;
  if(d>0) return d+'天'+h+'时';
  if(h>0) return h+'时'+m+'分';
  if(m>0) return m+'分'+sec+'秒';
  return sec+'秒';
}
function statusOf(s){
  if(s.running&&s.health_ok) return {cls:'ok',txt:'运行中',dot:'#22c55e'};
  if(!s.loaded&&!s.running) return {cls:'off',txt:'已停止',dot:'#64748b'};
  return {cls:'bad',txt:'异常',dot:'#ef4444'};
}
function thrColor(pct){ if(pct==null) return '#94a3b8'; if(pct>=85) return '#ef4444'; if(pct>=60) return '#f59e0b'; return '#22c55e'; }

function sparkline(vals, opts){
  opts=opts||{};
  const w=opts.w||120,h=opts.h||30,color=opts.color||'#60a5fa',max=opts.max,fill=opts.fill!==false;
  const data=(vals||[]).filter(v=>v!=null && !isNaN(v));
  if(data.length<2) return '<span class="na">—</span>';
  let mx=(max!=null)?max:Math.max.apply(null,data);
  const mn=Math.min.apply(null,data);
  if(mx===mn) mx=mn+1;
  const n=data.length;
  const pts=data.map((v,i)=>{
    const x=w*i/(n-1);
    const y=h-((v-mn)/(mx-mn))*(h-4)-2;
    return x.toFixed(1)+','+y.toFixed(1);
  });
  const line=pts.join(' ');
  const area='0,'+h+' '+line+' '+w+','+h;
  return '<svg class="spark" width="'+w+'" height="'+h+'" viewBox="0 0 '+w+' '+h+'">'+
    (fill?'<polygon points="'+area+'" fill="'+color+'" opacity="0.12"/>':'')+
    '<polyline points="'+line+'" fill="none" stroke="'+color+'" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>';
}
function gauge(pct,color,text){
  const v=(pct==null||isNaN(pct))?0:Math.max(0,Math.min(100,pct));
  const r=26,c=2*Math.PI*r,off=c*(1-v/100);
  const t=(text!=null)?text:Math.round(v)+'%';
  return '<svg width="72" height="72" viewBox="0 0 72 72">'+
    '<circle cx="36" cy="36" r="'+r+'" fill="none" stroke="#1f2937" stroke-width="7"/>'+
    '<circle cx="36" cy="36" r="'+r+'" fill="none" stroke="'+color+'" stroke-width="7" stroke-linecap="round" '+
    'stroke-dasharray="'+c.toFixed(1)+'" stroke-dashoffset="'+off.toFixed(1)+'" transform="rotate(-90 36 36)"/>'+
    '<text x="36" y="40" text-anchor="middle" fill="#e5e7eb" font-size="13" font-weight="700">'+t+'</text></svg>';
}

function kpi(label,val,sub,accent){
  return '<div class="kpi" style="--accent:'+(accent||'var(--text)')+'">'+
    '<div class="kpi-label">'+label+'</div>'+
    '<div class="kpi-val">'+val+'</div>'+
    '<div class="kpi-sub">'+sub+'</div></div>';
}
function renderKPI(d){
  const sv=d.services||[];
  const running=sv.filter(s=>s.running&&s.health_ok).length;
  const badN=sv.filter(s=>statusOf(s).cls==='bad').length;
  const errs=sv.reduce((a,s)=>a+(s.errors_5m||0),0);
  const acc=sv.filter(s=>s.has_http).reduce((a,s)=>a+(s.req_pm||0),0);
  const sys=d.system||{}, sh=d.sys_history||[];
  const loadSpark=sh.map(e=>e.load1).filter(v=>v!=null);
  const memSpark=sh.map(e=>e.mem_used_pct).filter(v=>v!=null);
  const diskSpark=sh.map(e=>e.disk_used_pct).filter(v=>v!=null);
  const loadPct=sys.load1!=null?Math.min(100,sys.load1/(STATE.cores||1)*100):null;
  const cards=[
    kpi('服务健康', running+'<span class="u">/'+sv.length+'</span>',
        badN>0?'<span class="pill bad">'+badN+' 异常</span>':'<span class="pill ok">全部正常</span>', '#22c55e'),
    kpi('系统负载 1m', sys.load1!=null?sys.load1.toFixed(2):'—',
        sparkline(loadSpark,{w:96,h:24,color:'#fbbf24'}), thrColor(loadPct)),
    kpi('内存占用', sys.mem_used_pct!=null?sys.mem_used_pct+'%':'—',
        sparkline(memSpark,{w:96,h:24,color:'#60a5fa'}), thrColor(sys.mem_used_pct)),
    kpi('磁盘占用', sys.disk_used_pct!=null?sys.disk_used_pct+'%':'—',
        sparkline(diskSpark,{w:96,h:24,color:'#a78bfa'}), thrColor(sys.disk_used_pct)),
    kpi('近5分钟错误', ''+errs, errs>0?'<span class="pill bad">需关注</span>':'<span class="pill ok">无</span>',
        errs>0?'#ef4444':'#22c55e'),
    kpi('访问速率', acc+'<span class="u">/分</span>', '<span class="na">HTTP 服务</span>', '#34d399'),
  ];
  document.getElementById('kpi').innerHTML=cards.join('');
}

function renderSystem(d){
  const sys=d.system||{}, cores=STATE.cores||1;
  const loadPct=sys.load1!=null?Math.min(100,sys.load1/cores*100):null;
  const el=document.getElementById('sys');
  el.innerHTML=
    '<div class="gauge-card">'+gauge(loadPct,thrColor(loadPct),sys.load1!=null?sys.load1.toFixed(2):'—')+
      '<div class="gauge-meta"><div class="g-name">系统负载</div>'+
      '<div class="g-val">'+(sys.load1!=null?sys.load1.toFixed(2):'—')+'<span class="u">1m</span></div>'+
      '<div class="g-sub">'+cores+' 核 · 5m '+(sys.load5!=null?sys.load5.toFixed(2):'—')+' · 15m '+(sys.load15!=null?sys.load15.toFixed(2):'—')+'</div></div></div>'+
    '<div class="gauge-card">'+gauge(sys.mem_used_pct,thrColor(sys.mem_used_pct))+
      '<div class="gauge-meta"><div class="g-name">内存占用</div>'+
      '<div class="g-val">'+(sys.mem_used_gb!=null?sys.mem_used_gb+'GB':'—')+'<span class="u">/ '+(sys.mem_total_gb!=null?sys.mem_total_gb+'GB':'—')+'</span></div>'+
      '<div class="g-sub">使用率 '+(sys.mem_used_pct!=null?sys.mem_used_pct+'%':'—')+'</div></div></div>'+
    '<div class="gauge-card">'+gauge(sys.disk_used_pct,thrColor(sys.disk_used_pct))+
      '<div class="gauge-meta"><div class="g-name">磁盘占用</div>'+
      '<div class="g-val">'+(sys.disk_used_pct!=null?sys.disk_used_pct+'%':'—')+'</div>'+
      '<div class="g-sub">根分区 /</div></div></div>';
}

function healthDots(arr){
  if(!arr||arr.length===0) return '';
  return '<span class="dots">'+arr.slice(-24).map(v=>'<i class="'+(v?'on':'off')+'"></i>').join('')+'</span>';
}
function card(s,h){
  const st=statusOf(s), p=s.proc||{};
  const cpuSpark=sparkline((h||[]).map(e=>e.cpu),{w:150,h:30,color:'#fbbf24',max:100});
  const memSpark=sparkline((h||[]).map(e=>e.mem_mb),{w:150,h:30,color:'#60a5fa'});
  const dots=healthDots((h||[]).map(e=>e.up));
  const portTxt=s.port?(':'+s.port):'无端口';
  const metrics=[
    ['PID', s.pid?(''+s.pid):'—'],
    ['运行', fmtUptime(p.uptime)],
    ['CPU', p.cpu!=null?(p.cpu+'%'):'—'],
    ['内存', p.mem_mb!=null?(p.mem_mb+' MB'):'—'],
    ['进程', p.procs!=null?(''+p.procs):'—'],
    ['错误(5m)', ''+(s.errors_5m||0)],
  ];
  if(s.has_http) metrics.push(['请求/分', ''+(s.req_pm||0)]);
  const mhtml=metrics.map(m=>'<div class="m"><div class="m-k">'+m[0]+'</div><div class="m-v">'+m[1]+'</div></div>').join('');
  return `<div class="card ${st.cls}">
    <div class="card-top"><div class="card-title"><span class="dot" style="background:${st.dot};color:${st.dot}"></span>${esc(s.name)}
      <span class="port">${portTxt}</span></div><span class="badge ${st.cls}">${st.txt}</span></div>
    <div class="health">${esc(s.health_txt||'—')} ${dots}</div>
    <div class="metrics">${mhtml}</div>
    <div class="sparks"><div class="spark-box"><div class="spark-l">CPU 趋势</div>${cpuSpark}</div>
      <div class="spark-box"><div class="spark-l">内存 趋势</div>${memSpark}</div></div>
    <div class="actions"><button class="b start" onclick="act('${s.key}','start')">启动</button>
      <button class="b restart" onclick="act('${s.key}','restart')">重启</button>
      <button class="b stop" onclick="act('${s.key}','stop')">停止</button></div>
    <div class="log-toggle" onclick="toggleLog(this)">▸ 查看日志</div>
    <pre class="log" style="display:none">${(s.log||[]).map(l=>esc(l)).join('\\n')}</pre></div>`;
}
function renderGrid(d){
  const map={};(d.services||[]).forEach(s=>map[s.key]=s);
  const hist=d.spark||{};
  document.getElementById('grid').innerHTML=ORDER.filter(k=>map[k]).map(k=>card(map[k],hist[k]||[])).join('');
}

async function load(){
  try{
    const r=await fetch('/api/status');const d=await r.json();
    if(d.system&&d.system.cores) STATE.cores=d.system.cores;
    renderKPI(d);renderSystem(d);renderGrid(d);
    const c=document.getElementById('clock');
    if(c) c.textContent='最后刷新 '+new Date().toLocaleTimeString('zh-CN');
  }catch(e){
    const g=document.getElementById('grid');
    if(g) g.innerHTML='<div class="card bad"><div class="card-top"><div class="card-title">连接异常</div></div>'+
      '<div class="health">看板接口无响应，请确认看板进程仍在运行（launchctl list | grep ops.dashboard）。</div></div>';
  }
}
async function act(key,action){
  try{
    const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,action})});
    const d=await r.json();toast(d.msg||'已执行');
  }catch(e){toast('操作失败：'+e);}
  setTimeout(load,900);
}
async function op(action){
  try{
    const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:'project',action})});
    const d=await r.json();toast(d.msg?d.msg.slice(0,80):'已执行');
    setTimeout(loadOps,700);
  }catch(e){toast('操作失败：'+e);}
}
async function loadOps(){
  try{const r=await fetch('/api/op-log');const d=await r.json();
    document.getElementById('opslog').textContent=(d.log||[]).join('\\n');}catch(e){}
}
function toggleOps(){document.getElementById('ops').classList.toggle('open');if(document.getElementById('ops').classList.contains('open'))loadOps();}
function toggleLog(el){const n=el.nextElementSibling;n.style.display=(n.style.display==='none'?'block':'none');el.textContent=(n.style.display==='none'?'▸ 查看日志':'▾ 收起日志');}
let toastTimer;
function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),2600);}
load();setInterval(load,5000);
</script>
</body>
</html>"""


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"ATS-NEW 运维看板已启动： http://localhost:{PORT}")
        print("在浏览器打开上面的地址即可查看并一键启停 dev 服务。")
        print("按 Ctrl+C 停止看板。")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n看板已停止。")


if __name__ == "__main__":
    main()
