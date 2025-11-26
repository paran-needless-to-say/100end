# 100end EC2 배포 가이드

이 문서는 100end 백엔드를 EC2에 배포하는 방법을 단계별로 안내합니다.

## 목차

- [시스템 요구사항](#시스템-요구사항)
- [1. 서버 준비](#1-서버-준비)
- [2. 필수 소프트웨어 설치](#2-필수-소프트웨어-설치)
- [3. 프로젝트 설정](#3-프로젝트-설정)
- [4. 환경 변수 설정](#4-환경-변수-설정)
- [5. 리스크 스코어링 API 준비](#5-리스크-스코어링-api-준비)
- [6. Docker로 배포](#6-docker로-배포)
- [7. Nginx 리버스 프록시 설정](#7-nginx-리버스-프록시-설정-선택)
- [8. SSL 인증서 설정](#8-ssl-인증서-설정-선택)
- [9. 모니터링 및 로그 관리](#9-모니터링-및-로그-관리)
- [10. 문제 해결](#10-문제-해결)

---

## 시스템 요구사항

### 최소 사양

- **CPU**: 2 core 이상
- **RAM**: 4GB 이상 (8GB 권장)
- **디스크**: 20GB 이상 여유 공간
- **OS**: Ubuntu 20.04 LTS 이상 또는 Amazon Linux 2

### 필수 소프트웨어

- Docker 20.10 이상
- Docker Compose 2.0 이상
- Git

---

## 1. 서버 준비

### EC2 인스턴스 생성 (AWS)

1. **인스턴스 타입 선택**

   - t3.medium 이상 권장 (프로덕션)
   - t3.small (테스트/개발)

2. **보안 그룹 설정**

   - 인바운드 규칙 추가:
     - HTTP (80): 0.0.0.0/0 (또는 특정 IP만)
     - HTTPS (443): 0.0.0.0/0 (SSL 사용 시)
     - Backend API (8888): 0.0.0.0/0 또는 특정 IP만
     - Risk Scoring API (5001): 127.0.0.1만 (내부 통신용)
     - SSH (22): 본인 IP만 (보안)

3. **키 페어 생성 및 다운로드**
   - `.pem` 파일 저장 및 권한 설정:
     ```bash
     chmod 400 your-key.pem
     ```

### 서버 접속

```bash
ssh -i your-key.pem ubuntu@your-server-ip
```

---

## 2. 필수 소프트웨어 설치

### Docker 설치

```bash
# 시스템 업데이트
sudo apt-get update
sudo apt-get upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 로그아웃 후 다시 로그인하거나 아래 명령어 실행
newgrp docker

# Docker 확인
docker --version
```

### Docker Compose 설치

```bash
# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 실행 권한 부여
sudo chmod +x /usr/local/bin/docker-compose

# 확인
docker-compose --version
```

### Git 설치 (이미 설치되어 있을 수 있음)

```bash
sudo apt-get install git -y
git --version
```

### Nginx 설치 (리버스 프록시 사용 시)

```bash
sudo apt-get install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

---

## 3. 프로젝트 설정

### 프로젝트 클론

```bash
# 홈 디렉토리로 이동
cd ~

# 100end 레포 클론
git clone https://github.com/paran-needless-to-say/100end.git
cd 100end

# 최신 코드 확인
git pull origin main
```

### 프로젝트 구조 확인

```bash
ls -la
# 다음 파일들이 있어야 합니다:
# - main.py
# - pyproject.toml
# - Dockerfile
# - docker-compose.yml
# - src/
```

---

## 4. 환경 변수 설정

### .env 파일 생성

프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다:

```bash
cd ~/100end
cat > .env << EOF
# Etherscan API 키 (필수)
ETHERSCAN_API_KEY=your_etherscan_api_key_here

# Flask 환경
FLASK_ENV=production

# Python 출력 버퍼링 비활성화
PYTHONUNBUFFERED=1

# 리스크 스코어링 API URL (Docker 네트워크 내부)
RISK_SCORING_API_URL=http://risk-scoring:5001
EOF
```

**중요**: `your_etherscan_api_key_here`를 실제 Etherscan API 키로 변경하세요.

### Etherscan API 키 발급

1. [Etherscan.io](https://etherscan.io)에 가입
2. [API Keys 페이지](https://etherscan.io/apis)에서 API 키 생성
3. `.env` 파일에 키 추가

**참고**: 프로덕션에서는 Pro 플랜 사용을 권장합니다 (무료 플랜: 5 req/sec 제한).

---

## 5. 리스크 스코어링 API 준비

100end 백엔드는 리스크 스코어링 API를 호출합니다. 두 가지 방법이 있습니다:

### 방법 1: 같은 서버에서 Docker Compose로 실행 (권장)

이 방법은 `docker-compose.yml` 파일에 리스크 스코어링 API를 포함하도록 설정되어 있습니다.

리스크 스코어링 API 레포를 클론합니다:

```bash
cd ~
git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring
cd risk-scoring

# requirements.txt 확인 (이미 있다면 생략)
# requirements.txt가 있는지 확인
ls -la requirements.txt
```

그 다음, 100end 레포의 `docker-compose.yml`이 리스크 스코어링 API를 올바르게 참조하도록 확인합니다.

### 방법 2: 별도 서버에서 실행

리스크 스코어링 API를 별도 서버에서 실행하는 경우:

1. 리스크 스코어링 API 서버에서:

   ```bash
   cd ~
   git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring
   cd risk-scoring
   source venv/bin/activate
   pip install -r requirements.txt
   python run_server.py
   ```

2. 100end 서버의 `.env` 파일 수정:
   ```bash
   RISK_SCORING_API_URL=http://<리스크-스코어링-서버-IP>:5001
   ```

---

## 6. Docker로 배포

### 리스크 스코어링 API 준비 (같은 서버에서 실행 시)

`docker-compose.yml`은 리스크 스코어링 API를 같은 디렉토리에 `risk-scoring/` 폴더로 가정합니다.

```bash
# 홈 디렉토리로 이동
cd ~

# 리스크 스코어링 API 클론 (아직 안 했다면)
git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring

# 100end 레포로 이동
cd 100end

# docker-compose.yml에서 risk-scoring 경로 확인
# 필요시 수정: ./risk-scoring -> ~/risk-scoring 또는 절대 경로
```

### Docker Compose로 배포

```bash
cd ~/100end

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 서비스 상태 확인

```bash
# 실행 중인 컨테이너 확인
docker-compose ps

# 각 서비스 상태 확인
docker-compose ps backend
docker-compose ps risk-scoring

# Health check
curl http://localhost:8888/api/dashboard/summary
curl http://localhost:5001/health
```

### 서비스 중지

```bash
cd ~/100end
docker-compose down

# 볼륨까지 삭제하려면
docker-compose down -v
```

### 서비스 재시작

```bash
# 특정 서비스만 재시작
docker-compose restart backend

# 모든 서비스 재시작
docker-compose restart
```

### 서비스 업데이트

```bash
# 최신 코드 가져오기
cd ~/100end
git pull origin main

# 컨테이너 재빌드 및 재시작
docker-compose up -d --build
```

---

## 7. Nginx 리버스 프록시 설정 (선택)

Nginx를 사용하여 단일 도메인으로 API를 제공하고 SSL을 적용할 수 있습니다.

### Nginx 설정 파일 생성

```bash
sudo nano /etc/nginx/sites-available/100end
```

다음 내용을 추가합니다 (도메인명과 서버 IP를 실제 값으로 변경):

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # 백엔드 API 프록시
    location /api/ {
        proxy_pass http://localhost:8888;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS 헤더 추가
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;

        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }

    # 루트 경로는 백엔드로 리다이렉트 (선택)
    location / {
        return 301 /api/dashboard/summary;
    }
}
```

### 설정 파일 활성화

```bash
# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/100end /etc/nginx/sites-enabled/

# 기본 설정 제거 (충돌 방지)
sudo rm /etc/nginx/sites-enabled/default

# 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
```

### 방화벽 설정

```bash
# UFW 방화벽 활성화 (Ubuntu)
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw allow 8888/tcp  # 백엔드 API 직접 접근용
sudo ufw enable

# 방화벽 상태 확인
sudo ufw status
```

---

## 8. SSL 인증서 설정 (선택)

Let's Encrypt를 사용하여 무료 SSL 인증서를 발급받을 수 있습니다.

### Certbot 설치

```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx -y
```

### SSL 인증서 발급

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot이 자동으로 Nginx 설정을 업데이트하고 SSL을 활성화합니다.

### 자동 갱신 설정

Let's Encrypt 인증서는 90일마다 갱신되어야 합니다. Certbot은 자동 갱신을 위해 cron 작업을 설정합니다:

```bash
# 자동 갱신 테스트
sudo certbot renew --dry-run
```

---

## 9. 모니터링 및 로그 관리

### 로그 확인

```bash
# 모든 서비스 로그 확인
cd ~/100end
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f backend
docker-compose logs -f risk-scoring

# 최근 100줄만 확인
docker-compose logs --tail=100

# 특정 시간 이후 로그만 확인
docker-compose logs --since 1h
```

### 리소스 사용량 확인

```bash
# 컨테이너 리소스 사용량 확인
docker stats

# 디스크 사용량 확인
docker system df
```

### Health Check

각 서비스는 health check 엔드포인트를 제공합니다:

```bash
# 리스크 스코어링 API
curl http://localhost:5001/health

# 백엔드 API
curl http://localhost:8888/api/dashboard/summary
```

### 자동 재시작 설정

`docker-compose.yml`은 컨테이너가 종료되면 자동으로 재시작하도록 설정되어 있습니다 (`restart: unless-stopped`).

---

## 10. 문제 해결

### 포트가 이미 사용 중

```bash
# 포트 사용 중인 프로세스 확인
sudo lsof -i :8888
sudo lsof -i :5001

# 프로세스 종료
sudo kill -9 <PID>
```

### 컨테이너가 시작되지 않음

```bash
# 컨테이너 로그 확인
cd ~/100end
docker-compose logs backend
docker-compose logs risk-scoring

# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 재빌드
docker-compose build --no-cache backend
docker-compose up -d backend
```

### 환경 변수가 적용되지 않음

```bash
# .env 파일 확인
cat .env

# 환경 변수가 올바르게 로드되는지 확인
docker-compose config

# 서비스 재시작
docker-compose restart
```

### Etherscan API 오류

```
Scoring analysis failed: Etherscan API error...
```

**해결 방법**:

1. `.env` 파일에 `ETHERSCAN_API_KEY`가 올바르게 설정되어 있는지 확인
2. API 키가 유효한지 확인 (Etherscan 웹사이트에서 테스트)
3. API 레이트 리밋 초과 여부 확인 (무료 플랜: 5 req/sec)
4. 프로덕션에서는 Pro 플랜 사용 권장

### 리스크 스코어링 API 연결 오류

```
Risk scoring API call failed: Connection refused
```

**해결 방법**:

1. 리스크 스코어링 API가 실행 중인지 확인:

   ```bash
   docker-compose ps risk-scoring
   curl http://localhost:5001/health
   ```

2. `RISK_SCORING_API_URL` 환경 변수가 올바른지 확인 (Docker 네트워크 내부: `http://risk-scoring:5001`)

3. 같은 네트워크에 있는지 확인 (`docker-compose.yml`의 `networks` 설정)

### 디스크 공간 부족

```bash
# 사용하지 않는 Docker 이미지/컨테이너 삭제
docker system prune -a

# 볼륨까지 삭제하려면 (주의: 데이터 삭제됨)
docker system prune -a --volumes
```

### 메모리 부족

```bash
# 컨테이너 메모리 사용량 확인
docker stats

# 메모리 제한이 있는 경우 docker-compose.yml에 limits 추가
# 예시:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

---

## 배포 체크리스트

배포 후 다음 사항을 확인하세요:

- [ ] 모든 서비스가 정상 실행 중인가? (`docker-compose ps`)
- [ ] Health check 엔드포인트가 정상 응답하는가?
- [ ] 백엔드 API가 정상 응답하는가? (`curl http://localhost:8888/api/dashboard/summary`)
- [ ] 리스크 스코어링 API가 정상 응답하는가? (`curl http://localhost:5001/health`)
- [ ] 환경 변수가 올바르게 설정되었는가? (`.env` 파일 확인)
- [ ] 로그에 에러가 없는가? (`docker-compose logs`)
- [ ] Nginx 설정이 올바른가? (`nginx -t`)
- [ ] SSL 인증서가 설치되어 있는가? (HTTPS 사용 시)
- [ ] 방화벽 규칙이 올바른가?

---

## 추가 리소스

- [100end API 사용 가이드](./API_USAGE.md)
- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [Nginx 공식 문서](https://nginx.org/en/docs/)
- [Let's Encrypt 문서](https://letsencrypt.org/docs/)

---

## 지원

문제가 발생하거나 질문이 있으시면:

1. [GitHub Issues](https://github.com/paran-needless-to-say/100end/issues)에 이슈 등록
2. 팀에 문의

---

**마지막 업데이트**: 2025-01-27
