#!/bin/bash

# 100end EC2 배포 스크립트
# 이 스크립트는 EC2 서버에 SSH로 접속하여 배포를 진행합니다.

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "100end EC2 배포 스크립트"
echo "=========================================="
echo ""

# 사용자 입력 받기
read -p "EC2 서버 IP 주소를 입력하세요: " SERVER_IP
read -p "SSH 키 파일 경로 (.pem): " SSH_KEY
read -p "EC2 사용자명 (기본값: ubuntu): " EC2_USER
EC2_USER=${EC2_USER:-ubuntu}

# SSH 키 파일 확인
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ SSH 키 파일을 찾을 수 없습니다: $SSH_KEY${NC}"
    exit 1
fi

# SSH 키 권한 확인
chmod 400 "$SSH_KEY" 2>/dev/null || true

# .env 파일 확인
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다.${NC}"
    read -p "Etherscan API 키를 입력하세요: " ETHERSCAN_API_KEY
    
    cat > .env << EOF
ETHERSCAN_API_KEY=$ETHERSCAN_API_KEY
FLASK_ENV=production
PYTHONUNBUFFERED=1
RISK_SCORING_API_URL=http://risk-scoring:5001
EOF
    echo -e "${GREEN}✅ .env 파일 생성 완료${NC}"
fi

echo ""
echo "=========================================="
echo "배포 시작..."
echo "=========================================="
echo ""

# 1. 서버에 필요한 파일 전송
echo "📦 파일 전송 중..."
scp -i "$SSH_KEY" -r Dockerfile docker-compose.yml deploy.sh .env "$EC2_USER@$SERVER_IP:~/100end/" 2>/dev/null || {
    echo "원격 디렉토리 생성 중..."
    ssh -i "$SSH_KEY" "$EC2_USER@$SERVER_IP" "mkdir -p ~/100end"
    scp -i "$SSH_KEY" Dockerfile docker-compose.yml deploy.sh .env "$EC2_USER@$SERVER_IP:~/100end/"
}

# 2. 서버에서 배포 실행
echo ""
echo "🚀 서버에서 배포 실행 중..."
ssh -i "$SSH_KEY" "$EC2_USER@$SERVER_IP" << 'ENDSSH'
cd ~/100end

# Git이 설치되어 있는지 확인
if ! command -v git &> /dev/null; then
    echo "Git 설치 중..."
    sudo apt-get update
    sudo apt-get install -y git
fi

# 100end 레포 클론 또는 업데이트
if [ ! -d ".git" ]; then
    echo "100end 레포 클론 중..."
    git clone https://github.com/paran-needless-to-say/100end.git temp
    mv temp/* temp/.* . 2>/dev/null || true
    rmdir temp 2>/dev/null || true
else
    echo "100end 레포 업데이트 중..."
    git pull origin main
fi

# 리스크 스코어링 API 클론
if [ ! -d "../risk-scoring" ]; then
    echo "리스크 스코어링 API 클론 중..."
    cd ~
    git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring
    cd ~/100end
fi

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    newgrp docker
fi

# Docker Compose 설치 확인
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose 설치 중..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# .env 파일이 전송되지 않았다면 생성
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. 수동으로 생성해주세요."
fi

# 배포 스크립트 실행 권한 부여
chmod +x deploy.sh

# 배포 실행
echo ""
echo "배포 스크립트 실행 중..."
./deploy.sh

ENDSSH

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 배포 완료!${NC}"
echo "=========================================="
echo ""
echo "서버 정보:"
echo "  IP: $SERVER_IP"
echo "  Backend API: http://$SERVER_IP:8888"
echo "  Risk Scoring API: http://$SERVER_IP:5001"
echo ""
echo "테스트:"
echo "  curl http://$SERVER_IP:8888/api/dashboard/summary"
echo "  curl http://$SERVER_IP:5001/health"
echo ""

