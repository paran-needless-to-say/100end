# Docker 빠른 시작 가이드

이 가이드는 Docker를 사용하여 100end 백엔드를 **5분 안에** 실행하는 방법을 설명합니다.

## 🚀 빠른 시작 (3단계)

### 1️⃣ 환경 변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집
nano .env
```

**최소 필수 설정:**

```env
ETHERSCAN_API_KEY=your_etherscan_api_key
DB_HOST=your_database_host
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=your_database_name
SECRET_KEY=your_secret_key
```

### 2️⃣ Docker 이미지 빌드 및 실행

**방법 A: 자동 스크립트 사용 (권장)**

```bash
# Docker Compose로 모든 서비스 실행
./scripts/docker-deploy.sh
```

**방법 B: Docker Compose 수동 실행**

```bash
docker compose up -d
```

**방법 C: 단일 컨테이너만 실행**

```bash
./scripts/docker-run-simple.sh
```

### 3️⃣ 확인

```bash
# API 테스트
curl http://localhost:8888/api/dashboard/summary

# 로그 확인
docker logs -f 100end-backend
```

---

## 📋 전체 명령어 요약

### Docker Compose 사용

```bash
# 시작
docker compose up -d

# 로그 보기
docker compose logs -f

# 중지
docker compose stop

# 재시작
docker compose restart

# 완전 제거
docker compose down
```

### 단일 컨테이너 사용

```bash
# 시작
docker run -d --name 100end-backend -p 8888:8888 --env-file .env 100end-backend:latest

# 로그 보기
docker logs -f 100end-backend

# 중지
docker stop 100end-backend

# 재시작
docker restart 100end-backend

# 제거
docker rm -f 100end-backend
```

---

## 🔧 문제 해결

### "Container failed to start"

```bash
# 로그 확인
docker logs 100end-backend

# 일반적인 원인:
# 1. .env 파일 누락 또는 잘못된 설정
# 2. 데이터베이스 연결 실패
# 3. API 키 오류
```

### 데이터베이스 연결 오류

```bash
# .env 파일의 DB 설정 확인
cat .env | grep DB_

# 데이터베이스 연결 테스트
docker exec 100end-backend curl -v telnet://YOUR_DB_HOST:3306
```

### 환경 변수가 반영되지 않음

```bash
# 컨테이너 재빌드
docker compose down
docker compose build --no-cache
docker compose up -d

# 또는 단일 컨테이너
docker rm -f 100end-backend
docker build --no-cache -t 100end-backend:latest .
docker run -d --name 100end-backend -p 8888:8888 --env-file .env 100end-backend:latest
```

---

## 📦 서비스 구성

Docker Compose를 사용하면 다음 서비스가 실행됩니다:

| 서비스 | 포트 | 설명 |
|--------|------|------|
| backend | 8888 | 메인 Flask 백엔드 API |
| risk-scoring | 5001 | 리스크 스코어링 마이크로서비스 |

---

## 🌐 API 엔드포인트

서비스가 실행되면 다음 엔드포인트를 사용할 수 있습니다:

### Dashboard
- `GET http://localhost:8888/api/dashboard/summary`
- `GET http://localhost:8888/api/dashboard/monitoring`

### Analysis
- `POST http://localhost:8888/api/analysis/transaction-flow`
- `POST http://localhost:8888/api/analysis/fund-flow`

### Live Detection
- `GET http://localhost:8888/api/live-detection/*`

### Reports
- `GET http://localhost:8888/api/reports/*`

---

## ⚙️ 고급 설정

### 리소스 제한

`docker-compose.yml` 파일을 편집하여 리소스를 제한할 수 있습니다:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Gunicorn Workers 조정

`Dockerfile`에서 worker 수를 조정:

```dockerfile
# 현재: --workers 4
# 권장: (2 × CPU 코어 수) + 1
CMD ["gunicorn", "--workers", "8", ...]
```

### 개발 모드로 실행

```bash
# .env 파일 수정
FLASK_ENV=development

# 재시작
docker compose restart
```

---

## 📚 더 알아보기

- [전체 배포 가이드](./DOCKER_DEPLOYMENT.md)
- [프로젝트 문서](../README.md)

---

## ✅ 체크리스트

배포 전 확인사항:

- [ ] Docker 및 Docker Compose 설치 확인
- [ ] `.env` 파일 생성 및 설정 완료
- [ ] 데이터베이스 접근 가능 확인
- [ ] API 키 발급 완료 (Etherscan, Alchemy 등)
- [ ] 방화벽 포트 개방 (8888, 5001)
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인

---

**문제가 발생하면 [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)의 상세 가이드를 참고하세요.**
