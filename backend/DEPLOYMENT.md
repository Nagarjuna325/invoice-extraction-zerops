# 🚀 Production Deployment Guide

Complete guide for deploying the Invoice Extraction System to production.

---

## 📋 Pre-Deployment Checklist

### **1. Environment Setup**
- [ ] Python 3.10+ installed
- [ ] PostgreSQL 12+ configured
- [ ] Tesseract OCR installed
- [ ] Git repository ready
- [ ] Domain name configured (optional)
- [ ] SSL certificate ready (recommended)

### **2. Security**
- [ ] Strong SECRET_KEY generated
- [ ] Database password secured
- [ ] DEBUG=False set
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Input validation active

### **3. Performance**
- [ ] Database indexed
- [ ] Connection pooling configured
- [ ] Worker count optimized
- [ ] File size limits set
- [ ] Monitoring enabled

---

## 🔧 Production Configuration

### **1. Update .env for Production**
```bash
# Production .env
DATABASE_URL=postgresql://invoice_user:STRONG_PASSWORD@localhost:5432/invoice_production
SECRET_KEY=GENERATE_STRONG_SECRET_KEY_HERE
DEBUG=False
LOG_LEVEL=INFO
APP_NAME=Invoice Extraction System
APP_VERSION=1.0.0

# CORS (adjust for your domain)
ALLOWED_ORIGINS=["https://yourdomain.com", "https://app.yourdomain.com"]

# File Limits
MAX_FILE_SIZE_MB=10
MAX_UPLOAD_WORKERS=4
```

### **2. Generate Secure Secret Key**
```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## 🐳 Deployment Options

### **Option 1: Traditional Server (Ubuntu/Debian)**

#### **Step 1: Server Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Tesseract
sudo apt install tesseract-ocr -y

# Install system dependencies
sudo apt install build-essential libpq-dev -y
```

#### **Step 2: Create User & Directory**
```bash
# Create app user
sudo useradd -m -s /bin/bash invoiceapp
sudo su - invoiceapp

# Create directory
mkdir invoice-extraction
cd invoice-extraction
```

#### **Step 3: Deploy Code**
```bash
# Clone repository
git clone <your-repo-url> .

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### **Step 4: Setup Database**
```bash
# Create database user
sudo -u postgres createuser invoiceapp
sudo -u postgres createdb invoice_production -O invoiceapp

# Set password
sudo -u postgres psql
ALTER USER invoiceapp WITH PASSWORD 'STRONG_PASSWORD';
\q

# Run migrations
psql -U invoiceapp -d invoice_production -f setup_database.sql
```

#### **Step 5: Configure Systemd Service**
```bash
sudo nano /etc/systemd/system/invoice-extraction.service
```
```ini
[Unit]
Description=Invoice Extraction API
After=network.target postgresql.service

[Service]
Type=notify
User=invoiceapp
Group=invoiceapp
WorkingDirectory=/home/invoiceapp/invoice-extraction
Environment="PATH=/home/invoiceapp/invoice-extraction/venv/bin"
ExecStart=/home/invoiceapp/invoice-extraction/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
# Enable and start service
sudo systemctl enable invoice-extraction
sudo systemctl start invoice-extraction
sudo systemctl status invoice-extraction
```

#### **Step 6: Setup Nginx Reverse Proxy**
```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/invoice-extraction
```
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout for long processing
        proxy_read_timeout 180s;
        proxy_connect_timeout 180s;
        proxy_send_timeout 180s;
    }
}
```
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/invoice-extraction /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### **Step 7: Setup SSL with Let's Encrypt** (Optional but Recommended)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
sudo systemctl reload nginx
```

---

### **Option 2: Docker Deployment**

#### **Dockerfile**
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### **docker-compose.yml**
```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: invoice_extraction
      POSTGRES_USER: invoiceapp
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://invoiceapp:${DB_PASSWORD}@db:5432/invoice_extraction
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
    depends_on:
      - db
    volumes:
      - ./uploads:/app/uploads

volumes:
  postgres_data:
```
```bash
# Deploy with Docker
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

---

### **Option 3: Cloud Platforms**

#### **A) Railway.app**
1. Connect GitHub repository
2. Add PostgreSQL addon
3. Set environment variables
4. Deploy (automatic)

#### **B) Render.com**
1. Create Web Service from repo
2. Add PostgreSQL database
3. Set environment variables
4. Deploy

#### **C) Heroku**
```bash
# Install Heroku CLI
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

#### **D) AWS EC2**
Follow Traditional Server steps on EC2 Ubuntu instance.

---

## 📊 Post-Deployment

### **1. Verify Installation**
```bash
# Check API health
curl http://yourdomain.com/

# Check API docs
curl http://yourdomain.com/api/docs

# Test upload
curl -X POST http://yourdomain.com/api/v1/invoices/upload \
  -F "file=@test_invoice.pdf"
```

### **2. Monitor Logs**
```bash
# Systemd logs
sudo journalctl -u invoice-extraction -f

# Application logs
tail -f logs/app.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### **3. Database Backups**
```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U invoiceapp invoice_production > backup_$DATE.sql
# Upload to S3 or other storage
```

### **4. Monitoring** (Optional)
- Prometheus + Grafana
- Datadog
- New Relic
- Sentry for error tracking

---

## 🔒 Security Best Practices

1. **Use HTTPS** - Always encrypt traffic
2. **Rate Limiting** - Prevent abuse
3. **Input Validation** - Already implemented
4. **Database Security** - Strong passwords, limited access
5. **Regular Updates** - Keep dependencies updated
6. **Monitoring** - Track unusual activity
7. **Backups** - Regular database backups
8. **Secrets Management** - Use environment variables, not hardcoded

---

## 📈 Scaling

### **Vertical Scaling**
- Increase server RAM (for ML models)
- Add more CPU cores
- Use SSD storage

### **Horizontal Scaling**
- Load balancer (Nginx, HAProxy)
- Multiple app servers
- Shared database
- Redis for caching (optional)

### **Optimization**
- Model quantization (reduce size)
- GPU acceleration (if available)
- Batch processing
- Queue system (Celery, RQ)

---

## 🆘 Troubleshooting

### **Service won't start**
```bash
sudo systemctl status invoice-extraction
sudo journalctl -u invoice-extraction -n 50
```

### **502 Bad Gateway**
- Check if app is running
- Check Nginx configuration
- Check firewall rules

### **Database connection issues**
```bash
# Test connection
psql -U invoiceapp -d invoice_production -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

### **High memory usage**
- Reduce worker count
- Implement request queuing
- Monitor with `htop`

---

## ✅ Production Checklist

- [ ] Application deployed and running
- [ ] Database configured and secured
- [ ] SSL certificate installed
- [ ] Nginx reverse proxy working
- [ ] Systemd service enabled
- [ ] Logs rotating properly
- [ ] Backups configured
- [ ] Monitoring enabled
- [ ] Documentation updated
- [ ] Team trained on system

---

**Deployment Status:** Ready for Production ✅  
**Support:** See README.md for contact information