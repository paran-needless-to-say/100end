#!/bin/bash

# 100end 프로덕션 배포 스크립트

set -e  # 에러 발생 시 스크립트 중단

echo "=========================================="
echo "100end 프로덕션 배포 스크립트"
echo "=========================================="
echo ""

# .env 파일 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다!"
    echo ""
    echo "다음 명령어로 .env 파일을 생성하세요:"
    echo "  cat > .env << EOF"
    echo "  ETHERSCAN_API_KEY=your_api_key_here"
    echo "  FLASK_ENV=production"
    echo "  PYTHONUNBUFFERED=1"
    echo "  RISK_SCORING_API_URL=http://risk-scoring:5001"
    echo "  EOF"
    echo ""
    exit 1
fi

# .env 파일에서 ETHERSCAN_API_KEY 확인
if ! grep -q "ETHERSCAN_API_KEY=" .env || grep -q "ETHERSCAN_API_KEY=your" .env; then
    echo "⚠️  경고: ETHERSCAN_API_KEY가 설정되지 않았거나 기본값입니다!"
    echo "   .env 파일을 확인하고 실제 API 키를 입력하세요."
    echo ""
    read -p "계속하시겠습니까? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Docker 및 Docker Compose 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다!"
    echo "   https://docs.docker.com/get-docker/ 에서 설치하세요."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되지 않았습니다!"
    echo "   https://docs.docker.com/compose/install/ 에서 설치하세요."
    exit 1
fi

echo "✅ 환경 확인 완료"
echo ""

# 리스크 스코어링 API 확인
if [ ! -d "../risk-scoring" ] && [ ! -d "./risk-scoring" ]; then
    echo "⚠️  경고: 리스크 스코어링 API 디렉토리를 찾을 수 없습니다!"
    echo "   같은 디렉토리 레벨에 risk-scoring 폴더가 있어야 합니다."
    echo ""
    echo "   다음 명령어로 클론하세요:"
    echo "   cd ~"
    echo "   git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring"
    echo ""
    read -p "계속하시겠습니까? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 기존 컨테이너 중지 (있는 경우)
if docker-compose ps -q | grep -q .; then
    echo "📦 기존 컨테이너 중지 중..."
    docker-compose down
    echo ""
fi

# 최신 코드 가져오기 (git이 있는 경우)
if command -v git &> /dev/null && [ -d .git ]; then
    echo "📥 최신 코드 가져오기..."
    git pull origin main || echo "⚠️  git pull 실패 (계속 진행)"
    echo ""
fi

# 이미지 빌드 및 컨테이너 시작
echo "🔨 이미지 빌드 중..."
docker-compose build

echo ""
echo "🚀 서비스 시작 중..."
docker-compose up -d

echo ""
echo "⏳ 서비스 시작 대기 중... (약 10초)"
sleep 10

# Health check
echo ""
echo "🏥 Health check 중..."
echo ""

# Backend API
if curl -f -s http://localhost:8888/api/dashboard/summary > /dev/null 2>&1; then
    echo "✅ Backend API (포트 8888): 정상"
else
    echo "⚠️  Backend API (포트 8888): 응답 없음 (일부 엔드포인트는 404가 정상)"
fi

# Risk Scoring API
if curl -f -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Risk Scoring API (포트 5001): 정상"
else
    echo "❌ Risk Scoring API (포트 5001): 응답 없음"
    echo "   리스크 스코어링 API가 정상적으로 시작되지 않았을 수 있습니다."
    echo "   docker-compose logs risk-scoring 으로 로그를 확인하세요."
fi

echo ""
echo "=========================================="
echo "✅ 배포 완료!"
echo "=========================================="
echo ""
echo "서비스 URL:"
echo "  Backend API:     http://localhost:8888"
echo "  Risk Scoring:    http://localhost:5001"
echo ""
echo "유용한 명령어:"
echo "  로그 확인:       docker-compose logs -f"
echo "  서비스 상태:     docker-compose ps"
echo "  서비스 중지:     docker-compose down"
echo "  서비스 재시작:   docker-compose restart"
echo ""
echo "로그 확인 중... (Ctrl+C로 중단)"
echo ""

# 로그 출력 (선택적)
read -p "로그를 확인하시겠습니까? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose logs -f
fi

