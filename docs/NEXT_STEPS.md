# EC2 인스턴스 발견 후 다음 단계

AWS 콘솔에서 실행 중인 EC2 인스턴스를 발견했다면, 다음 단계를 따라 배포하세요.

## 1단계: 서버 정보 확인

### 퍼블릭 IP 주소 확인

1. **AWS 콘솔에서 인스턴스 클릭**
   - 인스턴스 ID: `i-05126306c48bfd8b3` (또는 다른 ID)
   - 이름: `Trace-X`

2. **하단 탭에서 확인**
   - "네트워킹" 또는 "세부 정보" 탭 클릭
   - **"퍼블릭 IPv4 주소"** 확인
   - 예: `54.123.45.67` 또는 `ec2-54-123-45-67.ap-northeast-2.compute.amazonaws.com`

3. **또는 테이블에서 확인**
   - 인스턴스 테이블에 "퍼블릭 IPv4 주소" 열이 있다면 바로 확인

**예시:**
```
퍼블릭 IPv4 주소: 13.125.45.123
```

### SSH 키 파일 확인

인스턴스 생성 시 다운로드한 `.pem` 키 파일이 필요합니다.

**키 파일 위치 확인:**
- 보통 `~/Downloads/` 또는 `~/Desktop/`에 저장됨
- 파일명 예: `my-key.pem`, `trace-x-key.pem`, `100end-key.pem` 등

**키 파일이 없다면:**
1. AWS 콘솔 → EC2 → 키 페어 확인
2. 또는 새 키 페어 생성 (인스턴스 재생성 필요할 수 있음)

---

## 2단계: SSH 접속

### 로컬 터미널에서 실행

**1. 키 파일 권한 설정** (반드시 필요!)
```bash
chmod 400 ~/Downloads/your-key.pem
```

**2. SSH 접속**

**Ubuntu 인스턴스인 경우:**
```bash
ssh -i ~/Downloads/your-key.pem ubuntu@퍼블릭-IP-주소
```

**Amazon Linux 인스턴스인 경우:**
```bash
ssh -i ~/Downloads/your-key.pem ec2-user@퍼블릭-IP-주소
```

**예시:**
```bash
# 키 파일: ~/Downloads/trace-x-key.pem
# IP 주소: 13.125.45.123
ssh -i ~/Downloads/trace-x-key.pem ubuntu@13.125.45.123
```

### 접속 성공 확인

접속이 성공하면 다음과 같이 표시됩니다:
```
Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.4.0-1105-aws x86_64)
...
ubuntu@ip-172-31-xx-xx:~$
```

이제 EC2 서버에 접속된 상태입니다!

---

## 3단계: 배포 진행

서버에 접속했다면, 빠른 배포 가이드를 따라 진행하세요:

```bash
# 100end 레포 클론
cd ~
git clone https://github.com/paran-needless-to-say/100end.git
cd 100end

# 빠른 배포 가이드 확인
cat QUICK_DEPLOY.md

# 또는 바로 배포 시작
# (아래 "빠른 배포" 섹션 참조)
```

---

## 빠른 배포 (접속 후 바로 실행)

### 1. 필수 소프트웨어 설치

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

### 2. 프로젝트 클론

```bash
# 홈 디렉토리로 이동
cd ~

# 100end 레포 클론
git clone https://github.com/paran-needless-to-say/100end.git
cd 100end

# 리스크 스코어링 API 클론
cd ~
git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring
cd 100end
```

### 3. 환경 변수 설정

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

### 4. 배포 실행

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
# 서버 IP로 테스트 (로컬에서 실행)
curl http://퍼블릭-IP-주소:8888/api/dashboard/summary
```

---

## 문제 해결

### SSH 접속 실패

**"Permission denied (publickey)"**
```bash
# 키 파일 권한 확인 및 수정
chmod 400 ~/Downloads/your-key.pem
```

**"Connection refused" 또는 "Connection timed out"**
- AWS 콘솔 → EC2 → 보안 그룹 확인
- 인바운드 규칙에 SSH (포트 22)가 본인 IP에 대해 열려있는지 확인

### Docker 설치 실패

```bash
# Docker 재설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# 로그아웃 후 다시 로그인
exit
ssh -i ~/Downloads/your-key.pem ubuntu@퍼블릭-IP-주소
```

---

## 다음 단계

배포가 완료되면:
1. **보안 그룹 설정 확인**: 포트 8888, 5001이 열려있는지 확인
2. **외부에서 접속 테스트**: `http://퍼블릭-IP:8888` 접속 확인
3. **Nginx 설정** (선택): 도메인 연결 및 SSL 인증서 설치

자세한 내용은 [QUICK_DEPLOY.md](./QUICK_DEPLOY.md)를 참조하세요.

