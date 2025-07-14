# 部署指南

## 部署方式概览

Invoice OCR MCP支持多种部署方式：

1. **本地开发部署** - 适合开发和测试
2. **Docker容器部署** - 推荐的生产环境部署方式
3. **Kubernetes集群部署** - 适合大规模生产环境
4. **云服务部署** - 支持主流云平台

## 1. 本地开发部署

### 环境要求

- Python 3.8+
- 至少4GB内存
- GPU支持（可选，用于加速推理）
- ModelScope账号和API Token

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-org/invoice-ocr-mcp.git
cd invoice-ocr-mcp

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp env.example .env
# 编辑.env文件，添加你的ModelScope API Token

# 5. 下载模型
python scripts/download_models.py

# 6. 启动服务
python src/invoice_ocr_mcp/server.py
```

### 验证部署

```bash
# 测试MCP连接
python examples/client_example.py
```

## 2. Docker容器部署

### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/your-org/invoice-ocr-mcp.git
cd invoice-ocr-mcp

# 2. 配置环境变量
cp env.example .env
# 编辑.env文件

# 3. 构建并启动
docker-compose up -d

# 4. 查看日志
docker-compose logs -f invoice-ocr-mcp
```

### 生产环境配置

```bash
# 使用生产环境配置启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### GPU支持

```bash
# 启动GPU版本
docker-compose --profile gpu up -d
```

## 3. Kubernetes部署

### 前置条件

- Kubernetes 1.20+
- kubectl已配置
- Helm 3.0+（可选）

### 部署清单

创建 `k8s/` 目录并添加以下文件：

#### namespace.yaml
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: invoice-ocr
```

#### configmap.yaml
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: invoice-ocr-config
  namespace: invoice-ocr
data:
  # 从configs/目录复制配置文件
```

#### secret.yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: invoice-ocr-secrets
  namespace: invoice-ocr
type: Opaque
data:
  modelscope-token: <base64-encoded-token>
```

#### deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: invoice-ocr-mcp
  namespace: invoice-ocr
spec:
  replicas: 3
  selector:
    matchLabels:
      app: invoice-ocr-mcp
  template:
    metadata:
      labels:
        app: invoice-ocr-mcp
    spec:
      containers:
      - name: invoice-ocr-mcp
        image: your-registry/invoice-ocr-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODELSCOPE_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: invoice-ocr-secrets
              key: modelscope-token
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: config
          mountPath: /app/configs
        - name: cache
          mountPath: /app/cache
      volumes:
      - name: config
        configMap:
          name: invoice-ocr-config
      - name: cache
        emptyDir: {}
```

#### service.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: invoice-ocr-service
  namespace: invoice-ocr
spec:
  selector:
    app: invoice-ocr-mcp
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### ingress.yaml
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: invoice-ocr-ingress
  namespace: invoice-ocr
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: invoice-ocr.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: invoice-ocr-service
            port:
              number: 80
```

### 部署命令

```bash
# 应用所有配置
kubectl apply -f k8s/

# 查看部署状态
kubectl get pods -n invoice-ocr

# 查看服务
kubectl get services -n invoice-ocr
```

## 4. 云服务部署

### 阿里云容器服务ACK

```bash
# 1. 创建ACK集群
aliyun cs CreateCluster --region cn-hangzhou

# 2. 配置kubectl
aliyun cs GET kubeconfig --region cn-hangzhou --cluster-id <cluster-id>

# 3. 部署应用
kubectl apply -f k8s/
```

### AWS EKS

```bash
# 1. 创建EKS集群
eksctl create cluster --name invoice-ocr --region us-west-2

# 2. 部署应用
kubectl apply -f k8s/
```

### Azure AKS

```bash
# 1. 创建AKS集群
az aks create --resource-group myResourceGroup --name invoice-ocr

# 2. 获取凭据
az aks get-credentials --resource-group myResourceGroup --name invoice-ocr

# 3. 部署应用
kubectl apply -f k8s/
```

## 5. 配置说明

### 环境变量配置

主要配置项：

```bash
# ModelScope配置
MODELSCOPE_API_TOKEN=your_token_here
MODELSCOPE_CACHE_DIR=./cache/modelscope

# 服务器配置
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# 性能配置
MAX_CONCURRENT_REQUESTS=10
MAX_BATCH_SIZE=50
```

### 配置文件

#### configs/models.yaml
```yaml
models:
  text_detection:
    name: "damo/cv_resnet18_ocr-detection-line-level_damo"
    cache_dir: "./cache/models/text_detection"
    
  text_recognition:
    name: "damo/cv_convnextTiny_ocr-recognition-general_damo"
    cache_dir: "./cache/models/text_recognition"
    
  invoice_classification:
    name: "damo/cv_resnest50_ocr-invoice-classification"
    cache_dir: "./cache/models/classification"
```

#### configs/server.yaml
```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  
performance:
  max_concurrent_requests: 10
  max_batch_size: 50
  timeout: 30
  
cache:
  enabled: true
  expire_time: 86400
  redis_url: "redis://localhost:6379/0"
```

## 6. 监控和日志

### 日志配置

```yaml
# configs/logging.yaml
version: 1
formatters:
  standard:
    format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/app.log
    maxBytes: 104857600  # 100MB
    backupCount: 10
    formatter: standard
    
loggers:
  invoice_ocr_mcp:
    level: INFO
    handlers: [file]
    propagate: false
```

### Prometheus监控

启用Prometheus监控：

```bash
# 启动监控堆栈
docker-compose --profile monitoring up -d
```

访问监控界面：
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin123)

## 7. 性能优化

### GPU加速

启用GPU支持：

```bash
# Docker部署
docker-compose --profile gpu up -d

# Kubernetes部署
# 在deployment.yaml中添加GPU资源请求
resources:
  limits:
    nvidia.com/gpu: 1
```

### 缓存优化

配置Redis缓存：

```bash
# 启动Redis
docker-compose --profile cache up -d
```

### 负载均衡

使用Nginx反向代理：

```bash
# 启动代理
docker-compose --profile proxy up -d
```

## 8. 安全配置

### SSL/TLS

配置HTTPS：

```bash
# 生成自签名证书（仅用于测试）
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes

# 更新环境变量
ENABLE_HTTPS=true
SSL_CERT_PATH=./ssl/cert.pem
SSL_KEY_PATH=./ssl/key.pem
```

### API认证

启用API密钥认证：

```bash
# 设置API密钥
API_KEY=your_secure_api_key_here
```

## 9. 故障排除

### 常见问题

1. **模型加载失败**
   ```bash
   # 检查ModelScope连接
   python scripts/test_modelscope.py
   
   # 清理缓存重新下载
   rm -rf cache/modelscope
   python scripts/download_models.py
   ```

2. **内存不足**
   ```bash
   # 减少并发数
   MAX_CONCURRENT_REQUESTS=5
   
   # 启用GPU加速
   USE_GPU=true
   ```

3. **网络连接问题**
   ```bash
   # 检查防火墙设置
   # 确保端口8000已开放
   ```

### 日志分析

```bash
# 查看错误日志
tail -f logs/app.log | grep ERROR

# 分析性能
grep "processing_time" logs/app.log | tail -100
```

## 10. 升级指南

### 版本升级

```bash
# Docker升级
docker-compose pull
docker-compose up -d

# Kubernetes升级
kubectl set image deployment/invoice-ocr-mcp invoice-ocr-mcp=your-registry/invoice-ocr-mcp:new-version -n invoice-ocr
```

### 数据迁移

在升级前备份重要数据：

```bash
# 备份配置和数据
tar -czf backup-$(date +%Y%m%d).tar.gz configs/ data/ cache/
```

## 支持

如有部署问题，请：

1. 查看[故障排除文档](troubleshooting.md)
2. 提交[GitHub Issue](https://github.com/your-org/invoice-ocr-mcp/issues)
3. 联系技术支持：support@example.com 