#!/bin/sh
# ATS-New MySQL 密码轮换脚本
#
# 用途：在 10.10.22.80 上轮换 MySQL 用户密码，并同步更新本地/服务器 .env
#
# 用法：
#   1. 在 10.10.22.80 服务器上跑：
#      bash scripts/rotate-mysql-password.sh rotate <user> <host>
#      例：bash scripts/rotate-mysql-password.sh rotate ATS_pro 10.10.22.80
#
#   2. 脚本会提示输入新密码（不 echo），生成新随机密码或接受输入
#
# 警告：脚本不内置任何凭据，所有密码通过命令行/环境变量传入

set -e

USER=${1:?"用法: $0 rotate <mysql_user> <mysql_host>\n例: $0 rotate ATS_pro 10.10.22.80"}
HOST=${2:?"用法: $0 rotate <mysql_user> <mysql_host>"}

# 必须有 mysql root 权限才能 ALTER USER
echo "=== ATS-New MySQL 密码轮换 ==="
echo "用户: $USER"
echo "主机: $HOST"
echo ""
echo "需要 root 凭据以执行 ALTER USER。"
echo ""

# 1. 输入 root 凭据
printf "MySQL root 密码: "
stty -echo
read ROOT_PWD
stty echo
echo ""

printf "新密码 (留空则生成 32 字符随机): "
stty -echo
read NEW_PWD
stty echo
echo ""

if [ -z "$NEW_PWD" ]; then
  # 生成 32 字符随机密码
  NEW_PWD=$(LC_ALL=C tr -dc 'A-Za-z0-9!@#$%^&*' < /dev/urandom | head -c 32)
  echo "✓ 已生成新密码: $NEW_PWD"
  echo ""
fi

# 2. 验证 root 凭据 + 执行轮换
echo "=== 在 $HOST 上执行 ALTER USER ==="
mysql -h "$HOST" -P 3306 -u root -p"$ROOT_PWD" <<EOF
ALTER USER '$USER'@'%' IDENTIFIED BY '$NEW_PWD';
FLUSH PRIVILEGES;
SELECT '密码已轮换' AS status;
EOF

if [ $? -ne 0 ]; then
  echo "❌ ALTER USER 失败"
  exit 1
fi

# 3. 验证新密码能连
echo ""
echo "=== 验证新密码 ==="
mysql -h "$HOST" -P 3306 -u "$USER" -p"$NEW_PWD" -e "SELECT USER(), CURRENT_USER();" 2>&1 | grep -v Warning

# 4. 输出可复制到 .env 的内容
echo ""
echo "=== 请更新以下文件的 DATABASE_URL 和 MYSQL_PASSWORD ==="
echo ""
echo "DATABASE_URL=\"mysql://$USER:$NEW_PWD@$HOST:3306/${MYSQL_DATABASE:-ats_pro}\""
echo "MYSQL_HOST=$HOST"
echo "MYSQL_USER=$USER"
echo "MYSQL_PASSWORD=$NEW_PWD"
echo ""
echo "需要更新的位置："
echo "  - 本地: ATS-New/backend/.env"
echo "  - 服务器: <deploy_path>/backend/.env（或 docker-compose 注入环境变量）"
echo ""
echo "=== 完成后：重启 backend ==="
echo "  pm2 restart ats-backend"
echo "  或: kill \$(pgrep -f 'src/app.js') && nohup node src/app.js > /var/log/ats.log 2>&1 &"
echo ""
echo "🎉 轮换完成"
