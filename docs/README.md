# 100end Backend

Blockchain transaction analysis system for tracking fund flows and cross-chain transactions with risk scoring integration.

## 주요 기능

- Multi-hop 거래 분석
- 리스크 스코어링 API 통합
- Etherscan API를 통한 거래 데이터 수집
- 그래프 패턴 탐지
- Multi-chain 지원 (Ethereum, BSC, Polygon)

## 빠른 시작

### 로컬 개발

```bash
# 의존성 설치
pip3 install -e .

# 환경 변수 설정
export ETHERSCAN_API_KEY=your_api_key_here

# 서버 실행
python3 main.py
```

서버는 `http://localhost:8888`에서 실행됩니다.

### EC2 배포

**빠른 배포 가이드**: [QUICK_DEPLOY.md](./QUICK_DEPLOY.md) (5단계로 빠르게 배포)  
**상세 배포 가이드**: [DEPLOYMENT.md](./DEPLOYMENT.md) (전체 배포 과정 상세 설명)

**간단한 배포:**

```bash
# .env 파일 생성
cat > .env << EOF
ETHERSCAN_API_KEY=your_api_key_here
FLASK_ENV=production
PYTHONUNBUFFERED=1
RISK_SCORING_API_URL=http://risk-scoring:5001
EOF

# 배포 스크립트 실행
./deploy.sh
```

**EC2 서버 접속 후 배포:**

1. 서버 접속: `ssh -i your-key.pem ubuntu@your-server-ip`
2. 빠른 배포 가이드 따라하기: [QUICK_DEPLOY.md](./QUICK_DEPLOY.md)

## API 엔드포인트

### 리스크 스코어링 분석

```
GET  /api/analysis/risk-scoring
POST /api/analysis/risk-scoring
```

자세한 API 사용 방법은 [API_USAGE.md](./API_USAGE.md)를 참조하세요.

### 기타 엔드포인트

- `/api/dashboard/monitoring` - 모니터링 데이터
- `/api/analysis/fund-flow` - 자금 흐름 분석
- `/api/analysis/bridge` - 브리지 거래 분석

전체 API 엔드포인트: https://n4mchun.notion.site/100end-api-endpoints

## 문서

- [EC2 배포 가이드](./DEPLOYMENT.md): EC2에 배포하는 방법
- [API 사용 방법](./API_USAGE.md): 리스크 스코어링 API 사용 가이드
- [리스크 스코어링 API 레포](https://github.com/paran-needless-to-say/aml-risk-engine2)

## 환경 변수

| 변수명                 | 필수 | 기본값                  | 설명                                |
| ---------------------- | ---- | ----------------------- | ----------------------------------- |
| `ETHERSCAN_API_KEY`    | ✅   | -                       | Etherscan API 키                    |
| `FLASK_ENV`            | ❌   | `development`           | Flask 환경 (production/development) |
| `RISK_SCORING_API_URL` | ❌   | `http://localhost:5001` | 리스크 스코어링 API URL             |

## 프로젝트 구조

```
100end/
├── src/
│   ├── api/
│   │   ├── analysis.py        # 거래 분석 엔드포인트
│   │   ├── risk_scoring.py    # 리스크 스코어링 연동
│   │   ├── dashboard.py       # 대시보드 API
│   │   └── live_detection.py
│   ├── app.py                 # Flask 앱 설정
│   └── ...
├── main.py                    # 서버 시작점
├── Dockerfile                 # Docker 이미지
├── docker-compose.yml         # Docker Compose 설정
├── deploy.sh                  # 배포 스크립트
├── DEPLOYMENT.md              # 배포 가이드
└── API_USAGE.md               # API 사용 가이드
```

## 라이선스

MIT License

## 문의 및 지원

- **이슈**: [GitHub Issues](https://github.com/paran-needless-to-say/100end/issues)
- **팀 문의**: 백엔드 팀 또는 예림님
