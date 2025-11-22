# 100end 빠른 배포 가이드

EC2 서버에 직접 접속해서 배포하는 빠른 가이드입니다.

## 준비 사항

### 1. EC2 서버 정보

다음 정보를 준비하세요:

- **서버 IP 주소**: `your-server-ip`
- **SSH 키 파일**: `your-key.pem` (경로)
- **사용자명**: 보통 `ubuntu` 또는 `ec2-user`
- **Etherscan API 키**: 이미 발급받은 키

### 2. EC2 서버 확인

```bash
# 로컬에서 서버 접속 테스트
ssh -i your-key.pem ubuntu@your-server-ip
```

---

## 빠른 배포 (5단계)

### 1단계: 서버 접속

```bash
ssh -i your-key.pem ubuntu@your-server-ip
```

### 2단계: 필수 소프트웨어 설치

```bash
# 시스템 업데이트
sudo apt-get update
sudo apt-get upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Git 설치
sudo apt-get install git -y

# 설치 확인
docker --version
docker-compose --version
git --version
```

### 3단계: 프로젝트 클론

```bash
# 홈 디렉토리로 이동
cd ~

# 100end 레포 클론
git clone https://github.com/paran-needless-to-say/100end.git
cd 100end

# 리스크 스코어링 API 클론 (같은 레벨에)
cd ~
git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring
cd 100end
```

### 4단계: 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
ETHERSCAN_API_KEY=your_etherscan_api_key_here
FLASK_ENV=production
PYTHONUNBUFFERED=1
RISK_SCORING_API_URL=http://risk-scoring:5001
EOF

# Etherscan API 키를 실제 키로 변경
nano .env  # 또는 원하는 에디터 사용
```

**중요**: `your_etherscan_api_key_here`를 실제 Etherscan API 키로 변경하세요!

### 5단계: 배포 실행

```bash
# 배포 스크립트 실행 권한 부여
chmod +x deploy.sh

# 배포 실행
./deploy.sh
```

배포가 완료되면 자동으로 health check를 실행합니다.

---

## 배포 확인

### 서비스 상태 확인

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f
```

### API 테스트

```bash
# 백엔드 API 확인
curl http://localhost:8888/api/dashboard/summary

# 리스크 스코어링 API 확인
curl http://localhost:5001/health

# 리스크 스코어링 분석 테스트
curl "http://localhost:8888/api/analysis/risk-scoring?chain_id=1&address=0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be&hop_count=2"
```

외부에서 접속:

```bash
# 서버 IP로 테스트
curl http://your-server-ip:8888/api/dashboard/summary
```

---

## 문제 해결

### Docker가 설치되지 않음

```bash
# Docker 재설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# 로그아웃 후 다시 로그인
exit
ssh -i your-key.pem ubuntu@your-server-ip
```

### 포트가 이미 사용 중

```bash
# 포트 사용 중인 프로세스 확인
sudo lsof -i :8888
sudo lsof -i :5001

# 프로세스 종료 (필요 시)
sudo kill -9 <PID>
```

### 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker-compose logs backend
docker-compose logs risk-scoring

# 컨테이너 재시작
docker-compose restart
```

### .env 파일 문제

```bash
# .env 파일 확인
cat .env

# .env 파일 재생성
cat > .env << EOF
ETHERSCAN_API_KEY=실제_키_입력
FLASK_ENV=production
PYTHONUNBUFFERED=1
RISK_SCORING_API_URL=http://risk-scoring:5001
EOF

# 서비스 재시작
docker-compose restart
```

---

## 서비스 관리 명령어

```bash
cd ~/100end

# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 서비스 재시작
docker-compose restart

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f backend
docker-compose logs -f risk-scoring

# 서비스 상태 확인
docker-compose ps

# 최신 코드로 업데이트
git pull origin main
docker-compose up -d --build
```

---

## 서버 정보 기록

보안을 위해 서버 정보는 저장소에 커밋하지 마세요. 대신 로컬에 별도 파일로 저장하세요:

```bash
# 로컬에 서버 정보 저장 (git에 커밋하지 않음!)
cat > ~/.100end-server-info << EOF
# 100end EC2 서버 정보
SERVER_IP=your-server-ip
SSH_KEY=~/path/to/your-key.pem
EC2_USER=ubuntu
EOF

# 권한 제한
chmod 600 ~/.100end-server-info
```

---

## 다음 단계

배포가 완료되면:

1. **보안 그룹 설정 확인**: 포트 8888, 5001이 열려있는지 확인
2. **Nginx 설정** (선택): 도메인 연결 및 SSL 인증서 설치
3. **모니터링 설정** (선택): 로그 수집 및 알림 설정

자세한 내용은 [DEPLOYMENT.md](./DEPLOYMENT.md)를 참조하세요.

---

## 도움이 필요하신가요?

- [DEPLOYMENT.md](./DEPLOYMENT.md): 상세 배포 가이드
- [API_USAGE.md](./API_USAGE.md): API 사용 방법
- [GitHub Issues](https://github.com/paran-needless-to-say/100end/issues)
