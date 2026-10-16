#!/usr/bin/env bash
# Run on the server: bash deploy.sh <github-repo-url>
set -euo pipefail
REPO="${1:?usage: deploy.sh <github-repo-url>}"
APP=/var/www/multiagent

apt-get update && apt-get install -y python3-venv python3-pip nginx git curl
command -v node >/dev/null || { curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs; }

if [ -d "$APP/.git" ]; then git -C "$APP" pull; else git clone "$REPO" "$APP"; fi
cd "$APP"

python3 -m venv venv
./venv/bin/pip install -r backend/requirements.txt

[ -f backend/.env ] || { cp backend/.env.example backend/.env; echo ">> Edit $APP/backend/.env (SECRET_KEY, ALLOWED_HOSTS, OPENAI_API_KEY) then re-run"; exit 1; }

cd backend
../venv/bin/python manage.py migrate --noinput
../venv/bin/python manage.py collectstatic --noinput
cd ../frontend
npm ci && npm run build
cd ..

cp deploy/multiagent.service /etc/systemd/system/
cp deploy/nginx.conf /etc/nginx/sites-available/multiagent
ln -sf /etc/nginx/sites-available/multiagent /etc/nginx/sites-enabled/multiagent
systemctl daemon-reload
systemctl enable --now multiagent
systemctl restart multiagent
nginx -t && systemctl reload nginx
echo "Live: http://$(curl -s ifconfig.me):8080"
