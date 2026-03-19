#!/bin/bash
set -ux

# This script runs ON the EC2 instance after SSH is confirmed working.
# Usage: scp this file to EC2, then run it.

echo "=== Loading config ==="
source /etc/copilot-agent.env

echo "=== Installing system packages ==="
sudo dnf install -y python3.11 python3.11-pip nginx git openssl
sudo dnf install -y ffmpeg || echo "WARNING: ffmpeg not available"

echo "=== Cloning repository ==="
cd /home/ec2-user
if [ ! -d "app" ]; then
  git clone "$REPO_URL" app
fi
cd app

echo "=== Setting up Python ==="
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "=== Creating data directories ==="
mkdir -p /home/ec2-user/app/data/tmp

echo "=== Setting up TLS ==="
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out /etc/nginx/ssl/selfsigned.crt \
  -subj "/CN=copilot-agent"

echo "=== Configuring Nginx ==="
sudo tee /etc/nginx/conf.d/copilot.conf > /dev/null <<'NGINXEOF'
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

sudo rm -f /etc/nginx/conf.d/default.conf
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl restart nginx

echo "=== Creating systemd services ==="
sudo tee /etc/systemd/system/copilot-api.service > /dev/null <<'SVCEOF'
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

sudo tee /etc/systemd/system/copilot-ui.service > /dev/null <<'SVCEOF'
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

sudo systemctl daemon-reload
sudo systemctl enable copilot-api copilot-ui
sudo systemctl start copilot-api
sleep 5
sudo systemctl start copilot-ui

echo "=== Setup complete! ==="
echo "Check services: sudo systemctl status copilot-api copilot-ui"
