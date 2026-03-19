#!/bin/bash
set -ux

echo "=== Starting Copilot Agent setup ==="

# -----------------------------
# 1. Install system dependencies
# -----------------------------
dnf install -y python3.11 python3.11-pip nginx git openssl || true

# ffmpeg (best effort)
dnf install -y ffmpeg || echo "WARNING: ffmpeg not installed, media processing will not work"

# -----------------------------
# 2. Clone repository
# -----------------------------
cd /home/ec2-user
if [ ! -d "app" ]; then
  git clone -b copilot-agent __REPO_URL__ app || echo "ERROR: Git clone failed"
fi
chown -R ec2-user:ec2-user app

# -----------------------------
# 3. Python environment
# -----------------------------
cd /home/ec2-user/app
sudo -u ec2-user python3.11 -m venv .venv
sudo -u ec2-user /home/ec2-user/app/.venv/bin/pip install --upgrade pip
sudo -u ec2-user /home/ec2-user/app/.venv/bin/pip install -r requirements.txt || echo "ERROR: pip install failed"

# Create data directories
mkdir -p /home/ec2-user/app/data/tmp
chown -R ec2-user:ec2-user /home/ec2-user/app/data

# -----------------------------
# 4. Environment config
# -----------------------------
cat > /etc/copilot-agent.env <<EOF
SECRETS_ARN=__SECRETS_ARN__
DATA_DIR=/home/ec2-user/app/data
API_URL=http://localhost:8000
EOF

# -----------------------------
# 5. Nginx + TLS
# -----------------------------
mkdir -p /etc/nginx/ssl

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out /etc/nginx/ssl/selfsigned.crt \
  -subj "/CN=copilot-agent"

cat > /etc/nginx/conf.d/copilot.conf <<'NGINXEOF'
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ui {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /_stcore {
        proxy_pass http://127.0.0.1:8501/_stcore;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /static {
        proxy_pass http://127.0.0.1:8501/static;
    }
}

server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
NGINXEOF

rm -f /etc/nginx/conf.d/default.conf
nginx -t && systemctl enable nginx && systemctl start nginx

# -----------------------------
# 6. systemd services
# -----------------------------
cat > /etc/systemd/system/copilot-api.service <<'SVCEOF'
[Unit]
Description=Copilot Agent FastAPI
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/app
EnvironmentFile=/etc/copilot-agent.env
ExecStart=/home/ec2-user/app/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/systemd/system/copilot-ui.service <<'SVCEOF'
[Unit]
Description=Copilot Agent Streamlit UI
After=copilot-api.service

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/app
EnvironmentFile=/etc/copilot-agent.env
ExecStart=/home/ec2-user/app/.venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable copilot-api copilot-ui
systemctl start copilot-api
sleep 5
systemctl start copilot-ui

# Add SSH on port 443 (corporate firewalls often block port 22)
echo "Port 443" >> /etc/ssh/sshd_config
systemctl restart sshd

echo "=== Copilot Agent setup complete ==="
