#!/bin/bash
# ============================================================
# AgentOS 一键部署脚本
# 域名: coworkai.xin
# 服务器: ubuntu@152.32.131.4
# 
# ⚠️ 不会影响已有网站 /home/ubuntu/lessleep
# ⚠️ AgentOS 独立部署在 /home/ubuntu/agentos
# ============================================================

set -e  # 出错立即停止

echo "=========================================="
echo "  AgentOS 部署脚本"
echo "=========================================="

# -------------------------------------------------------
# 第 1 步：系统依赖
# -------------------------------------------------------
echo ""
echo "[1/7] 安装系统依赖..."
sudo apt update
sudo apt install -y python3-venv python3-pip git

# 安装 Node.js 18+ (如果没有)
if ! command -v node &> /dev/null || [ $(node -v | cut -d. -f1 | tr -d 'v') -lt 18 ]; then
    echo "安装 Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

echo "Python: $(python3 --version)"
echo "Node: $(node --version)"
echo "npm: $(npm --version)"

# -------------------------------------------------------
# 第 2 步：克隆项目
# -------------------------------------------------------
echo ""
echo "[2/7] 克隆项目..."
cd /home/ubuntu

if [ -d "agentos" ]; then
    echo "目录已存在，拉取最新代码..."
    cd agentos
    git pull origin main
else
    git clone https://github.com/zqsoren/coworkai.git agentos
    cd agentos
fi

echo "项目路径: $(pwd)"

# -------------------------------------------------------
# 第 3 步：Python 虚拟环境 + 后端依赖
# -------------------------------------------------------
echo ""
echo "[3/7] 安装后端依赖..."
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install \
    fastapi \
    uvicorn \
    bcrypt \
    pyjwt \
    pydantic \
    langchain \
    langchain-core \
    langchain-openai \
    langchain-google-genai \
    langchain-anthropic \
    httpx \
    python-multipart \
    toml

echo "后端依赖安装完成"

# -------------------------------------------------------
# 第 4 步：前端构建
# -------------------------------------------------------
echo ""
echo "[4/7] 构建前端..."
cd frontend
npm install
npm run build
cd ..

if [ -d "frontend/dist" ]; then
    echo "前端构建成功: frontend/dist/"
else
    echo "❌ 前端构建失败！请检查错误"
    exit 1
fi

# -------------------------------------------------------
# 第 5 步：生成 JWT 密钥
# -------------------------------------------------------
echo ""
echo "[5/7] 配置环境..."

# 生成随机 JWT 密钥（仅首次）
if ! grep -q "JWT_SECRET" ~/.bashrc 2>/dev/null; then
    JWT_KEY=$(openssl rand -hex 32)
    echo "export JWT_SECRET='${JWT_KEY}'" >> ~/.bashrc
    export JWT_SECRET="${JWT_KEY}"
    echo "JWT 密钥已生成并写入 ~/.bashrc"
else
    echo "JWT 密钥已存在，跳过"
    source ~/.bashrc
fi

# 创建初始 data 目录 和 config 目录
mkdir -p data
mkdir -p config

# 创建空的 llm_providers.json (如果不存在)
if [ ! -f "config/llm_providers.json" ]; then
    cp data/_template/llm_providers.json config/llm_providers.json
    echo "已从模板复制 llm_providers.json"
fi

# -------------------------------------------------------
# 第 6 步：设置 systemd 守护进程
# -------------------------------------------------------
echo ""
echo "[6/7] 配置 systemd 服务..."

sudo tee /etc/systemd/system/agentos.service > /dev/null << EOF
[Unit]
Description=AgentOS Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/agentos
Environment="PATH=/home/ubuntu/agentos/.venv/bin:/usr/bin"
Environment="JWT_SECRET=${JWT_SECRET}"
ExecStart=/home/ubuntu/agentos/.venv/bin/python backend/server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable agentos
sudo systemctl restart agentos

echo "等待 3 秒检查服务状态..."
sleep 3

if sudo systemctl is-active --quiet agentos; then
    echo "✅ AgentOS 后端运行中"
else
    echo "❌ 启动失败，查看日志："
    sudo journalctl -u agentos -n 20 --no-pager
    exit 1
fi

# -------------------------------------------------------
# 第 7 步：配置 Nginx（不影响现有网站！）
# -------------------------------------------------------
echo ""
echo "[7/7] 配置 Nginx..."

# 备份当前 Nginx 配置（安全起见）
sudo cp -r /etc/nginx/sites-available /etc/nginx/sites-available.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true

# 只新增一个 server 块，不修改任何现有配置
sudo tee /etc/nginx/sites-available/coworkai > /dev/null << 'NGINX_EOF'
server {
    listen 80;
    server_name coworkai.xin www.coworkai.xin;

    # 前端静态文件
    root /home/ubuntu/agentos/frontend/dist;
    index index.html;

    # SPA 路由 — 所有非文件请求回退到 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理到后端 (端口 8000)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持（群聊实时推送）
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;  # 5 分钟超时（LLM 可能慢）
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
NGINX_EOF

# 启用站点（如果尚未启用）
if [ ! -L /etc/nginx/sites-enabled/coworkai ]; then
    sudo ln -s /etc/nginx/sites-available/coworkai /etc/nginx/sites-enabled/coworkai
fi

# 测试配置
echo "测试 Nginx 配置..."
if sudo nginx -t 2>&1; then
    sudo systemctl reload nginx
    echo "✅ Nginx 重载成功"
else
    echo "❌ Nginx 配置有误，请检查！"
    echo "你的原有网站不受影响（未修改任何已有配置）"
    exit 1
fi

# -------------------------------------------------------
# 完成
# -------------------------------------------------------
echo ""
echo "=========================================="
echo "  ✅ 部署完成！"
echo "=========================================="
echo ""
echo "  网站地址: http://coworkai.xin"
echo "  后端状态: sudo systemctl status agentos"
echo "  后端日志: sudo journalctl -u agentos -f"
echo ""
echo "  ⚡ 可选：配置 HTTPS（免费SSL）"
echo "  sudo apt install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d coworkai.xin -d www.coworkai.xin"
echo ""
echo "  原有网站 /home/ubuntu/lessleep 未做任何修改 ✅"
echo "=========================================="
