# Swagger UI 접근 문제 해결

## 문제 상황

`petstore.swagger.io`에서 EC2 서버의 API를 호출하려고 할 때 Mixed-content 에러 발생:

- HTTPS 페이지(`petstore.swagger.io`)에서 HTTP 리소스(`http://3.38.112.25:5001`) 로드 시도
- 브라우저 보안 정책으로 인해 차단됨

---

## 해결 방법

### 방법 1: EC2 서버의 Swagger UI에 직접 접근 (권장)

**EC2 서버의 Swagger UI URL:**

```
http://3.38.112.25:5001/api-docs
```

**주의사항:**

- EC2 보안 그룹에서 포트 5001이 열려있어야 합니다
- 브라우저 주소창에 직접 입력해야 합니다

**사용 방법:**

1. 브라우저 주소창에 `http://3.38.112.25:5001/api-docs` 입력
2. Swagger UI 페이지가 열림
3. "Try it out" 버튼으로 API 테스트

---

### 방법 2: 로컬 Swagger UI 사용

로컬에서 Swagger UI를 실행하고 EC2 API를 테스트:

```bash
# Docker로 Swagger UI 실행
docker run -d -p 8080:8080 \
  -e SWAGGER_JSON=/api-docs.json \
  swaggerapi/swagger-ui

# 또는 npx 사용
npx swagger-ui-watcher http://3.38.112.25:5001/apispec.json
```

하지만 Mixed-content 문제는 여전히 발생할 수 있습니다.

---

### 방법 3: curl로 직접 테스트 (가장 확실함)

Swagger UI 없이 직접 API 호출:

```bash
# Health Check
curl http://3.38.112.25:5001/health

# 주소 분석 API
curl -X POST http://3.38.112.25:5001/api/analyze/address \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "chain_id": 1,
    "transactions": [
      {
        "tx_hash": "0xtest123",
        "chain_id": 1,
        "timestamp": "2025-01-15T10:00:00Z",
        "block_height": 21039493,
        "target_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "counterparty_address": "0xtest456",
        "label": "cex",
        "is_sanctioned": false,
        "is_known_scam": false,
        "is_mixer": false,
        "is_bridge": false,
        "amount_usd": 100.0,
        "asset_contract": "0xETH"
      }
    ],
    "analysis_type": "basic"
  }'
```

---

### 방법 4: HTTPS 설정 (프로덕션 권장)

HTTPS를 사용하면 Mixed-content 문제가 해결됩니다:

1. **Nginx 리버스 프록시 설정**
2. **SSL 인증서 설치** (Let's Encrypt 등)
3. **HTTPS로 Swagger UI 접근**

하지만 이는 프로덕션 환경에서 권장되는 방법입니다.

---

## 확인 사항

### 1. EC2 서버가 실행 중인지 확인

```bash
# EC2 서버에 SSH 접속 후
curl http://localhost:5001/health

# 또는 외부에서
curl http://3.38.112.25:5001/health
```

### 2. EC2 보안 그룹 확인

EC2 콘솔에서:

- 인바운드 규칙에 포트 5001 추가
- 소스: `0.0.0.0/0` (모든 IP 허용) 또는 특정 IP만 허용

### 3. Swagger UI 엔드포인트 확인

정확한 URL:

- ❌ `http://3.38.112.25:5001/` (루트)
- ✅ `http://3.38.112.25:5001/api-docs` (Swagger UI)
- ✅ `http://3.38.112.25:5001/apispec.json` (API 스펙 JSON)

---

## 권장 방법

**가장 간단한 방법:**

1. 브라우저 주소창에 `http://3.38.112.25:5001/api-docs` 입력
2. Swagger UI 페이지에서 직접 테스트

**가장 확실한 방법:**

- curl로 직접 API 호출 테스트

---

## EC2 서버 접근 확인

EC2 서버에서 다음을 확인하세요:

```bash
# Health Check
curl http://localhost:5001/health

# Swagger UI 접근 확인 (서버 내부에서)
curl http://localhost:5001/api-docs
```

응답이 정상이면 외부 접근 설정만 확인하면 됩니다.
