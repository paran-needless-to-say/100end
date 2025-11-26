# Docker 배포 가이드

이 문서는 100end 백엔드 애플리케이션을 Docker를 사용하여 배포하는 방법을 설명합니다.

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [환경 변수 설정](#환경-변수-설정)
3. [배포 방법](#배포-방법)
4. [문제 해결](#문제-해결)

## 사전 요구사항

### 필수 소프트웨어

- Docker 20.10 이상
- Docker Compose 2.0 이상 (docker-compose.yml 사용 시)

### 설치 확인

```bash
docker --version
docker compose version
```

### 외부 서비스

- **MySQL 데이터베이스**: AWS RDS 또는 별도 MySQL 서버
- **API 키**:
  - Etherscan API Key (필수)
  - Alchemy API Key (권장)
  - Dune Analytics API Key (선택)

## 환경 변수 설정

### 1. .env 파일 생성

```bash
cp .env.example .env
```

### 2. .env 파일 편집

`.env` 파일을 열고 실제 값으로 업데이트하세요:

```bash
nano .env
```

**필수 설정 항목:**

```env
# Etherscan API (필수)
ETHERSCAN_API_KEY=your_actual_api_key_here

# Database Configuration (필수)
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

# Flask Configuration (필수)
SECRET_KEY=generate_a_strong_secret_key_here
```

**선택 설정 항목:**

```env
# Alchemy API (권장)
ALCHEMY_API_KEY=https://eth-mainnet.g.alchemy.com/v2/your_api_key

# Dune Analytics API (선택)
DUNE_API_KEY=your_dune_api_key
```

### 3. 환경 변수 확인

스크립트를 실행하면 자동으로 필수 환경 변수를 검증합니다.

## 배포 방법

### 방법 1: Docker Compose 사용 (권장)

Docker Compose를 사용하면 백엔드와 risk-scoring 서비스를 함께 실행할 수 있습니다.

#### 자동 배포 스크립트

```bash
./scripts/docker-deploy.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- 환경 변수 검증
- 기존 컨테이너 중지 및 제거
- Docker 이미지 빌드
- 서비스 시작
- 헬스 체크

#### 수동 배포

```bash
# 1. 기존 컨테이너 중지
docker compose down

# 2. 이미지 빌드
docker compose build

# 3. 서비스 시작
docker compose up -d

# 4. 로그 확인
docker compose logs -f
```

### 방법 2: 단일 컨테이너 실행

백엔드만 Docker로 실행하고 risk-scoring은 외부에서 실행하는 경우:

```bash
./scripts/docker-run-simple.sh
```

또는 수동으로:

```bash
# 1. 이미지 빌드
docker build -t 100end-backend:latest .

# 2. 컨테이너 실행
docker run -d \
  --name 100end-backend \
  --restart unless-stopped \
  -p 8888:8888 \
  --env-file .env \
  100end-backend:latest

# 3. 로그 확인
docker logs -f 100end-backend
```

## 서비스 확인

### API 엔드포인트 테스트

```bash
# 백엔드 헬스 체크
curl http://localhost:8888/api/dashboard/summary

# Risk-scoring 헬스 체크 (docker-compose 사용 시)
curl http://localhost:5001/health
```

### 컨테이너 상태 확인

```bash
# Docker Compose 사용 시
docker compose ps

# 단일 컨테이너 사용 시
docker ps | grep 100end-backend
```

## 로그 관리

### 로그 보기

```bash
# Docker Compose - 모든 서비스
docker compose logs -f

# Docker Compose - 특정 서비스
docker compose logs -f backend

# 단일 컨테이너
docker logs -f 100end-backend
```

### 로그 설정

로그는 JSON 파일로 저장되며 다음과 같이 설정됩니다:
- 최대 파일 크기: 10MB
- 최대 파일 개수: 3개

## 컨테이너 관리

### 서비스 중지

```bash
# Docker Compose
docker compose stop

# 단일 컨테이너
docker stop 100end-backend
```

### 서비스 재시작

```bash
# Docker Compose
docker compose restart

# 단일 컨테이너
docker restart 100end-backend
```

### 서비스 제거

```bash
# Docker Compose (컨테이너 + 네트워크 제거)
docker compose down

# Docker Compose (이미지도 함께 제거)
docker compose down --rmi all

# 단일 컨테이너
docker rm -f 100end-backend
```

## 문제 해결

### 컨테이너가 시작되지 않는 경우

1. **로그 확인:**
   ```bash
   docker logs 100end-backend
   ```

2. **환경 변수 확인:**
   ```bash
   docker exec 100end-backend env | grep -E "(DB_|ETHERSCAN|ALCHEMY)"
   ```

3. **컨테이너 내부 접속:**
   ```bash
   docker exec -it 100end-backend bash
   ```

### 데이터베이스 연결 오류

1. **DB 호스트 확인:**
   - Docker 내부에서 `localhost`는 컨테이너 자신을 가리킵니다
   - 외부 DB는 실제 IP 또는 호스트명을 사용하세요
   - AWS RDS의 경우 엔드포인트 주소를 사용하세요

2. **네트워크 확인:**
   ```bash
   # 컨테이너에서 DB 접속 테스트
   docker exec 100end-backend curl -v telnet://DB_HOST:3306
   ```

3. **보안 그룹 확인 (AWS RDS):**
   - RDS 보안 그룹에서 Docker 호스트 IP 허용 확인

### 헬스 체크 실패

1. **헬스 체크 엔드포인트 확인:**
   ```bash
   docker exec 100end-backend curl -f http://localhost:8888/api/dashboard/summary
   ```

2. **시작 시간 조정:**
   - 애플리케이션 시작이 느린 경우 `docker-compose.yml`에서 `start_period` 증가

### 메모리/CPU 사용량 높음

1. **리소스 모니터링:**
   ```bash
   docker stats 100end-backend
   ```

2. **Gunicorn worker 조정:**
   - Dockerfile의 `--workers` 옵션 조정 (현재: 4)
   - 권장: `(2 × CPU 코어 수) + 1`

## 프로덕션 배포 권장사항

### 보안

1. **시크릿 관리:**
   - `.env` 파일을 Git에 커밋하지 마세요
   - AWS Secrets Manager 또는 HashiCorp Vault 사용 고려

2. **네트워크 보안:**
   - 방화벽 설정 (포트 8888, 5001만 허용)
   - HTTPS 사용 (Nginx 리버스 프록시 권장)

3. **이미지 보안:**
   - 정기적인 베이스 이미지 업데이트
   - 취약점 스캔: `docker scan 100end-backend:latest`

### 성능

1. **리소스 제한:**
   ```yaml
   # docker-compose.yml에 추가
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         memory: 512M
   ```

2. **데이터베이스 연결 풀:**
   - SQLAlchemy 연결 풀 설정 확인

### 모니터링

1. **로그 수집:**
   - ELK Stack, CloudWatch, Datadog 등 사용

2. **메트릭 수집:**
   - Prometheus + Grafana 연동 고려

3. **알림 설정:**
   - 컨테이너 다운 시 알림 설정

## 환경별 배포

### 개발 환경

```bash
# .env 파일에서
FLASK_ENV=development

# Docker Compose 실행
docker compose up
```

### 스테이징/프로덕션 환경

```bash
# .env 파일에서
FLASK_ENV=production

# 백그라운드 실행
docker compose up -d

# 자동 재시작 활성화 (기본 설정됨)
# restart: unless-stopped
```

## 추가 리소스

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Flask 프로덕션 배포 가이드](https://flask.palletsprojects.com/en/latest/deploying/)
- [Gunicorn 설정 가이드](https://docs.gunicorn.org/en/stable/settings.html)

## 지원

문제가 발생하면 다음을 확인하세요:
1. 로그 파일 검토
2. 환경 변수 설정 확인
3. 외부 서비스 (DB, API) 연결 확인
4. GitHub Issues에 문의
