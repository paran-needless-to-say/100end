# 리스크 스코어링 API 호출 테스트 결과

## 테스트 환경

### 로컬 환경 테스트

- **환경 변수**: `RISK_SCORING_API_URL=http://localhost:5001`
- **리스크 스코어링 API**: 실행 중 ✅

### Docker 환경 설정

- **docker-compose.prod.yml**: `RISK_SCORING_API_URL=http://risk-scoring:5001` 설정됨 ✅
- **기본값**: `http://risk-scoring:5001` (Docker 환경용) ✅

## 테스트 결과

### ✅ 테스트 통과

1. **환경 변수 읽기**: 정상 작동
2. **URL 구성**: 올바르게 구성됨
3. **Health Check**: 연결 성공 (200 OK)
4. **API 호출**: 성공
   - Risk Score: 15
   - Risk Level: low

## 코드 확인

### 환경 변수 읽기

```python
# backend/src/api/risk_scoring.py
RISK_SCORING_API_URL = os.getenv("RISK_SCORING_API_URL", "http://risk-scoring:5001")
```

### Docker Compose 설정

```yaml
# docker-compose.prod.yml
backend:
  environment:
    - RISK_SCORING_API_URL=http://risk-scoring:5001
```

## 결론

✅ **백엔드에서 리스크 스코어링 API를 올바르게 호출할 수 있습니다!**

- 로컬 환경: `http://localhost:5001` 사용 (환경 변수로 설정)
- Docker 환경: `http://risk-scoring:5001` 자동 사용 (Docker Compose 환경 변수)
