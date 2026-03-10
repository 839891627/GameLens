# 帧探·GameLens 部署指南

本文档说明如何将 GameLens 部署到云服务器。

## 📋 目录

- [部署架构](#部署架构)
- [服务器要求](#服务器要求)
- [部署步骤](#部署步骤)
- [持续运行](#持续运行)
- [数据更新](#数据更新)

---

## 🏗️ 部署架构

GameLens 是**纯前端应用**，部署非常简单：

```
云服务器
├── Nginx/Caddy (静态文件服务)
└── 项目文件
    ├── index.html
    ├── css/
    ├── js/
    └── data/
        ├── video_index.json
        └── video_frames/
```

**关键点：**
- ✅ 无需后端服务器
- ✅ 无需数据库
- ✅ 只需静态文件托管

---

## 💻 服务器要求

### 最低配置

| 资源 | 要求 |
|------|------|
| CPU | 1 核 |
| 内存 | 512 MB |
| 存储 | 5 GB+ (取决于视频帧数量) |
| 操作系统 | Linux (推荐 Ubuntu 20.04+) |
| 网络 | 公网 IP |

### 推荐配置

- **CPU**: 2 核
- **内存**: 1-2 GB
- **存储**: 10 GB+ SSD
- **带宽**: 1 Mbps+ (视频帧图片加载)

---

## 🚀 部署步骤

### Step 1: 准备服务器

#### 1.1 购买云服务器

推荐平台：
- 阿里云 ECS
- 腾讯云 CVM
- 华为云 ECS
- AWS EC2
- Vultr / DigitalOcean

#### 1.2 连接服务器

```bash
ssh root@your-server-ip
```

### Step 2: 安装必要软件

#### 2.1 安装 Nginx

```bash
# Ubuntu/Debian
apt update
apt install nginx -y

# CentOS/RHEL
yum install nginx -y
```

#### 2.2 验证 Nginx 安装

```bash
nginx -v
# 启动 Nginx
systemctl start nginx
systemctl enable nginx
```

访问 `http://your-server-ip` 应该看到 Nginx 欢迎页面。

### Step 3: 部署项目

#### 3.1 安装 Git

```bash
# Ubuntu/Debian
apt install git -y

# CentOS/RHEL
yum install git -y
```

#### 3.2 克隆项目（如果使用 Git）

```bash
cd /var/www
git clone https://github.com/your-username/gamelens.git
cd gamelens
```

#### 或者：直接上传文件

在本地执行：

```bash
# 打包项目文件（排除不需要的文件）
tar -czf gamelens.tar.gz \
  --exclude='downloads' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='venv' \
  .

# 上传到服务器
scp gamelens.tar.gz root@your-server-ip:/var/www/
```

在服务器上解压：

```bash
cd /var/www
mkdir -p gamelens
tar -xzf gamelens.tar.gz -C gamelens
```

#### 3.3 准备数据文件

**重要**：`data/video_index.json` 和 `data/video_frames/` 需要包含在内。

**方案1：在本地生成后上传**

```bash
# 本地生成数据
cd gamelens
python scripts/build_video_index.py

# 打包上传
tar -czf data.tar.gz data/
scp data.tar.gz root@your-server-ip:/var/www/gamelens/

# 服务器解压
ssh root@your-server-ip
cd /var/www/gamelens
tar -xzf data.tar.gz
rm data.tar.gz
```

**方案2：在服务器上生成**

```bash
# 安装 Python 3
apt install python3 python3-pip -y

# 安装依赖
cd /var/www/gamelens
pip3 install -r scripts/requirements.txt

# 生成数据
python3 scripts/build_video_index.py
```

### Step 4: 配置 Nginx

#### 4.1 创建 Nginx 配置文件

```bash
nano /etc/nginx/sites-available/gamelens
```

添加以下内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 或使用服务器 IP

    root /var/www/gamelens;
    index index.html;

    # 启用 gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # 缓存视频帧图片（1天）
    location ~* \.(jpg|jpeg|png|webp)$ {
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # 缓存静态资源
    location ~* \.(css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }

    # 禁用 access_log（可选，减少 I/O）
    access_log off;
}
```

#### 4.2 启用站点

```bash
# 创建软链接
ln -s /etc/nginx/sites-available/gamelens /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重载 Nginx
systemctl reload nginx
```

### Step 5: 配置域名（可选）

#### 5.1 购买域名

- 阿里云
- 腾讯云
- Cloudflare (免费)

#### 5.2 配置 DNS

添加 A 记录：

| 类型 | 名称 | 值 |
|------|------|-----|
| A | @ | your-server-ip |
| A | www | your-server-ip |

#### 5.3 配置 HTTPS（推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 获取证书并自动配置 Nginx
certbot --nginx -d your-domain.com -d www.your-domain.com

# 自动续期
certbot renew --dry-run
```

---

## 🔄 持续运行

### 使用 Systemd（如果需要 Python 服务）

如果需要定期更新数据，创建服务：

```bash
nano /etc/systemd/system/gamelens-update.service
```

```ini
[Unit]
Description=GameLens Video Index Updater
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/var/www/gamelens
ExecStart=/usr/bin/python3 scripts/build_video_index.py

[Install]
WantedBy=multi-user.target
```

创建定时器：

```bash
nano /etc/systemd/system/gamelens-update.timer
```

```ini
[Unit]
Description=GameLens Daily Update
Requires=gamelens-update.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

启用定时器：

```bash
systemctl daemon-reload
systemctl enable gamelens-update.timer
systemctl start gamelens-update.timer
```

---

## 📊 数据更新

### 更新视频列表

编辑 `data/videos.txt`，添加新的 B站视频链接：

```bash
nano /var/www/gamelens/data/videos.txt
```

### 重新生成索引

```bash
cd /var/www/gamelens
python3 scripts/build_video_index.py
```

### 自动化更新脚本

创建 `scripts/update.sh`：

```bash
#!/bin/bash
cd /var/www/gamelens
git pull origin main
python3 scripts/build_video_index.py
systemctl reload nginx
echo "Update completed at $(date)"
```

添加执行权限：

```bash
chmod +x scripts/update.sh
```

---

## 🔧 性能优化

### 1. 启用 HTTP/2

在 Nginx 配置中添加：

```nginx
listen 443 ssl http2;
```

### 2. 调整 worker 进程

编辑 `/etc/nginx/nginx.conf`：

```nginx
worker_processes auto;
worker_connections 1024;
```

### 3. 启用文件缓存

```nginx
open_file_cache max=1000 inactive=20s;
open_file_cache_valid 30s;
open_file_cache_min_uses 2;
```

---

## 📈 监控与日志

### 查看 Nginx 访问日志

```bash
tail -f /var/log/nginx/access.log
```

### 查看错误日志

```bash
tail -f /var/log/nginx/error.log
```

### 监控磁盘使用

```bash
df -h
du -sh /var/www/gamelens/data/video_frames
```

---

## 🔒 安全建议

1. **配置防火墙**

```bash
# 只开放 SSH (22) 和 HTTP (80/443)
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

2. **禁用 SSH 密码登录**

```bash
# 编辑 SSH 配置
nano /etc/ssh/sshd_config

# 修改为
PasswordAuthentication no

# 重启 SSH
systemctl restart sshd
```

3. **定期更新系统**

```bash
# Ubuntu/Debian
apt update && apt upgrade -y

# CentOS/RHEL
yum update -y
```

---

## ❓ 常见问题

### Q: 如何不使用 Nginx？

A: 可以使用其他静态文件服务器：
- **Caddy**（自动 HTTPS）
- **Python**: `python3 -m http.server 8000`
- **Node.js**: `npx serve`

### Q: 视频帧图片太多怎么办？

A:
1. 增加抽帧间隔（修改 `FRAME_INTERVAL` 环境变量）
2. 降低图片质量（修改 `scripts/build_video_index.py` 中的 JPEG 质量）
3. 使用 CDN（如 Cloudflare）

### Q: 如何支持多个游戏？

A: 为每个游戏创建独立的数据集，修改前端支持游戏切换。

---

## 📞 支持

如有问题，请：
1. 查看 [GitHub Issues](https://github.com/your-username/gamelens/issues)
2. 提交新的 Issue
3. 参考项目文档

---

**部署完成后，访问你的域名或 IP 地址即可使用 GameLens！**
