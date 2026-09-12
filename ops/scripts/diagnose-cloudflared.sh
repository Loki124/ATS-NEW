#!/usr/bin/env bash
# ============================================================================
# diagnose-cloudflared.sh
# Cloudflare Tunnel "Error 1033 / 530" 只读诊断脚本
#
# Error 1033 含义: 该 hostname 已配置为 Cloudflare Tunnel 路由,
#                  但 Cloudflare 边缘找不到活跃的 connector (cloudflared).
#                  与 nginx / docker / Django 无关 —— 是部署机到 CF 边缘这一段.
#
# 约束: 只读 —— 不重启服务、不改配置、不动数据
# 用法: sudo bash diagnose-cloudflared.sh
# ============================================================================
set -uo pipefail

C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_BLD=$'\033[1m'; C_RST=$'\033[0m'
hr(){   printf '\n%s===== %s =====%s\n' "$C_BLD" "$*" "$C_RST"; }
info(){ printf '  %s\n' "$*"; }
ok(){   printf '  %s[OK]%s %s\n'   "$C_GRN" "$C_RST" "$*"; }
bad(){  printf '  %s[NG]%s %s\n'   "$C_RED" "$C_RST" "$*"; }
warn(){ printf '  %s[!!]%s %s\n'   "$C_YEL" "$C_RST" "$*"; }

# ---------------------------------------------------------------- §0 环境
hr "§0 主机与时间"
info "host : $(hostname)"
info "date : $(date '+%F %T %Z')  (对比 CF 错误页 Ray ID 上的 UTC 时间)"
info "user : $(whoami)"
command -v cloudflared >/dev/null 2>&1 \
  && ok "cloudflared 已安装: $(cloudflared --version 2>&1 | head -1)" \
  || bad "cloudflared 命令不存在"

# ---------------------------------------------------------------- §1 进程数量(关键)
hr "§1 cloudflared 进程 (重点: 数量必须为 1)"
mapfile -t PROCS < <(pgrep -af cloudflared 2>/dev/null)
if [ "${#PROCS[@]}" -eq 0 ]; then
  bad "没有任何 cloudflared 进程在跑 —— 这就是 1033 的直接原因"
elif [ "${#PROCS[@]}" -eq 1 ]; then
  ok "恰好 1 个实例"
  info "${PROCS[0]}"
else
  bad "发现 ${#PROCS[@]} 个实例! 多个进程抢同一 tunnel 会互相顶掉, 表现为间歇 1033"
  for p in "${PROCS[@]}"; do info "  - $p"; done
fi

# ---------------------------------------------------------------- §2 systemd
hr "§2 systemd 服务状态"
for svc in cloudflared cloudflared.service cloudflared-tunnel; do
  if systemctl list-unit-files 2>/dev/null | grep -q "^${svc}"; then
    st=$(systemctl is-active "$svc" 2>/dev/null)
    en=$(systemctl is-enabled "$svc" 2>/dev/null)
    if [ "$st" = "active" ]; then ok "$svc: active / $en"; else bad "$svc: $st / $en"; fi
    warn "Restart= 配置: $(systemctl show "$svc" -p Restart -p RestartSec --value 2>/dev/null | tr '\n' ' ')"
  fi
done
systemctl list-unit-files 2>/dev/null | grep -i cloudflared || warn "未找到任何 cloudflared systemd 单元"

# ---------------------------------------------------------------- §3 日志
hr "§3 cloudflared 最近日志 (找 Registered / Failed / retry / shutdown)"
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u 'cloudflared*' -n 60 --no-pager -o short-iso 2>/dev/null || warn "journalctl 无 cloudflared 日志"
else
  for f in /var/log/cloudflared.log /var/log/cloudflared.err.log; do
    [ -f "$f" ] && { info "--- $f ---"; tail -40 "$f"; }
  done
fi

hr "§3b 隧道注册/重连关键字"
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u 'cloudflared*' --since '24 hours ago' --no-pager 2>/dev/null \
    | grep -iE 'registered|connection|retry|reconnect|quit|shutdown|failed|error|unable' \
    | tail -25 || info "(无匹配)"
fi

# ---------------------------------------------------------------- §4 tunnel UUID
hr "§4 本机 tunnel 身份 (与 CF DNS 记录的 CNAME 目标比对)"
if [ -d /etc/cloudflared ]; then
  info "/etc/cloudflared 内容:"; ls -la /etc/cloudflared | sed 's/^/    /'
  ids=$(grep -hoE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' /etc/cloudflared/*.json 2>/dev/null | sort -u)
  [ -n "$ids" ] && { info "本机凭证里的 tunnel UUID:"; echo "$ids" | sed 's/^/    /'; } \
                || warn "未从凭证文件解析出 UUID"
  [ -f /etc/cloudflared/config.yml ] && { info "--- config.yml ---"; sed 's/^/    /' /etc/cloudflared/config.yml; }
else
  warn "/etc/cloudflared 不存在"
fi
info "提示: Zero Trust Dashboard → Networks → Tunnels 里看到的 UUID 必须与上面一致;"
info "      若不一致, 说明 tunnel 被重建过而 DNS/CNAME 仍指向旧 UUID —— 会 100% 稳定 1033."

# ---------------------------------------------------------------- §5 回源端口
hr "§5 tunnel 回源目标端口是否存活"
check_port(){
  local p=$1 name=$2
  if (exec 3<>/dev/tcp/127.0.0.1/"$p") 2>/dev/null; then
    exec 3<&- 2>/dev/null; ok "$name 127.0.0.1:$p 可连接"
  else
    bad "$name 127.0.0.1:$p 连不上 (注意: 这只影响 502/504, 不影响 1033)"
  fi
}
check_port 9908 "nginx  (panel/ats 主入口)"
check_port 9000 "webhook receiver"
check_port 8000 "django 直连"

# ---------------------------------------------------------------- §6 OOM / 内存
hr "§6 内存与 OOM (cloudflared 常被 OOM killer 杀掉)"
free -h 2>/dev/null | sed 's/^/    /'
if command -v journalctl >/dev/null 2>&1; then
  oom=$(journalctl --since '3 days ago' --no-pager 2>/dev/null | grep -iE 'out of memory|oom-kill|killed process' | tail -10)
  [ -n "$oom" ] && { bad "发现 OOM 记录:"; echo "$oom" | sed 's/^/    /'; } || ok "近 3 天无 OOM 记录"
fi
dmesg 2>/dev/null | grep -iE 'oom|killed process' | tail -10 | sed 's/^/    /'

# ---------------------------------------------------------------- §7 出站连通性
hr "§7 到 Cloudflare 边缘的出站连通性 (国内机器高发故障点)"
for ep in region1.v2.argotunnel.com region2.v2.argotunnel.com api.cloudflare.com; do
  printf '  %-32s TCP/443: ' "$ep"
  if (exec 3<>/dev/tcp/"$ep"/443) 2>/dev/null; then exec 3<&- 2>/dev/null; echo "OK"; else echo "FAIL"; fi
done
printf '  %-32s UDP/7844(QUIC): ' "region1.v2.argotunnel.com"
if (exec 3<>/dev/udp/region1.v2.argotunnel.com/7844) 2>/dev/null; then
  exec 3<&- 2>/dev/null; echo "socket OK (UDP 无握手, 仅表示未被本机/firewall 立即拒绝)"
else
  echo "FAIL"
fi
warn "若 UDP/7844 实际不通而 TCP/443 通, cloudflared 会持续重连 → 间歇 1033."
warn "缓解: 在 config.yml 加 'protocol: http2' 强制走 TCP/443, 避开 QUIC 被 QoS."

# ---------------------------------------------------------------- §8 结论
hr "§8 判定指引"
cat <<'EOS'
  1033 三类根因, 按上面证据对号入座:

  A. §1 进程数 = 0 / §2 非 active
     → cloudflared 没跑。执行:
       sudo systemctl enable --now cloudflared
       sudo systemctl restart cloudflared

  B. §1 进程数 > 1
     → 多个实例抢同一 tunnel。只保留 systemd 那一个, kill 掉其余, 并确认
       没有 docker 容器里也跑了一份 cloudflared。

  C. §4 UUID 与 Dashboard 不一致
     → tunnel 被重建过。二选一:
       (1) Dashboard → DNS 记录, 把 CNAME 目标改成新 tunnel 的 <uuid>.cfargotunnel.com
       (2) 或让 cloudflared 改用旧 tunnel 的凭证文件重启

  D. §7 显示 QUIC 不通 / §3b 日志里反复 "Failed to connect" 又 "Registered"
     → 国内网络对 UDP 7844 的 QoS。加 protocol: http2 并重启:
       echo 'protocol: http2' | sudo tee -a /etc/cloudflared/config.yml
       sudo systemctl restart cloudflared

  加固建议 (防复发):
    - systemd 加 Restart=always / RestartSec=10
    - 部署机内存吃紧时优先保 cloudflared (OOMScoreAdjust=-1000)
    - 给 tunnel 配第二个 connector (load balancing) 可消除单点
EOS
printf '\n%s诊断结束 (只读, 未做任何修改)%s\n' "$C_GRN" "$C_RST"
