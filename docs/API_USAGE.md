# 100end 리스크 스코어링 API 사용 방법

백엔드 팀을 위한 리스크 스코어링 API 통합 사용 가이드입니다.

---

## API 엔드포인트

### 리스크 스코어링 분석

```
GET  /api/analysis/risk-scoring
POST /api/analysis/risk-scoring
```

---

## 요청 방법

### GET 요청

```bash
GET /api/analysis/risk-scoring?chain_id=1&address=0x...&hop_count=3
```

**Query Parameters:**

| 파라미터                      | 타입    | 필수 | 기본값  | 설명                    |
| ----------------------------- | ------- | ---- | ------- | ----------------------- |
| `chain_id`                    | integer | ✅   | -       | 체인 ID (1 = Ethereum)  |
| `address`                     | string  | ✅   | -       | 분석할 주소 (0x로 시작) |
| `hop_count`                   | integer | ❌   | 3       | 최대 홉 수 (1~5 권장)   |
| `max_addresses_per_direction` | integer | ❌   | 10      | 방향당 최대 주소 수     |
| `analysis_type`               | string  | ❌   | "basic" | "basic" 또는 "advanced" |

**예시:**

```bash
curl "http://localhost:8888/api/analysis/risk-scoring?chain_id=1&address=0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be&hop_count=3&analysis_type=basic"
```

### POST 요청

```bash
POST /api/analysis/risk-scoring
Content-Type: application/json
```

**Request Body:**

```json
{
  "chain_id": 1,
  "address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
  "max_hops": 3,
  "max_addresses_per_direction": 10,
  "analysis_type": "basic"
}
```

**예시:**

```bash
curl -X POST http://localhost:8888/api/analysis/risk-scoring \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": 1,
    "address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
    "max_hops": 3,
    "analysis_type": "basic"
  }'
```

---

## 응답 형식

### 성공 응답 (200 OK)

```json
{
  "data": {
    "address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
    "chain": "ethereum",
    "final_score": 85,
    "risk_level": "high",
    "risk_tags": ["sanction_exposure", "large_amount"],
    "fired_rules": [
      {
        "rule_id": "C-001",
        "score": 30,
        "description": "Sanctioned address exposure"
      },
      {
        "rule_id": "E-101",
        "score": 25,
        "description": "Large transaction amount"
      }
    ],
    "explanation": "High risk due to sanctioned address exposure and large transaction amounts.",
    "completed_at": "2025-01-15T10:30:00Z",
    "timestamp": "2025-01-15T10:30:00Z",
    "chain_id": 1,
    "value": 500000.0
  }
}
```

### 응답 필드 설명

| 필드                        | 타입    | 설명                                              |
| --------------------------- | ------- | ------------------------------------------------- |
| `address`                   | string  | 분석한 주소                                       |
| `chain`                     | string  | 체인 이름 (예: "ethereum")                        |
| `final_score`               | integer | 최종 리스크 점수 (0~100)                          |
| `risk_level`                | string  | 리스크 레벨 ("low", "medium", "high", "critical") |
| `risk_tags`                 | array   | 리스크 태그 목록                                  |
| `fired_rules`               | array   | 발동된 룰 목록                                    |
| `fired_rules[].rule_id`     | string  | 룰 ID (예: "C-001")                               |
| `fired_rules[].score`       | integer | 해당 룰의 점수                                    |
| `fired_rules[].description` | string  | 룰 설명                                           |
| `explanation`               | string  | 리스크 평가 설명                                  |
| `completed_at`              | string  | 분석 완료 시간 (ISO8601)                          |
| `timestamp`                 | string  | 타임스탬프 (ISO8601)                              |
| `chain_id`                  | integer | 체인 ID                                           |
| `value`                     | number  | 거래 금액 (USD)                                   |

### 에러 응답 (400 Bad Request)

```json
{
  "error": "chain_id is required"
}
```

### 에러 응답 (500 Internal Server Error)

```json
{
  "error": "Risk scoring failed: Risk scoring API call failed: Connection refused"
}
```

---

## 리스크 점수 및 레벨

### 점수 범위

| 점수 범위 | 리스크 레벨 | 설명             |
| --------- | ----------- | ---------------- |
| 0-20      | low         | 낮은 리스크      |
| 21-40     | medium      | 중간 리스크      |
| 41-60     | medium-high | 중간-높은 리스크 |
| 61-80     | high        | 높은 리스크      |
| 81-100    | critical    | 매우 높은 리스크 |

---

## 사용 예시

### 예시 1: 기본 분석 (Basic)

```bash
curl "http://localhost:8888/api/analysis/risk-scoring?chain_id=1&address=0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be&hop_count=2&analysis_type=basic"
```

### 예시 2: 고급 분석 (Advanced)

```bash
curl -X POST http://localhost:8888/api/analysis/risk-scoring \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": 1,
    "address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
    "max_hops": 3,
    "analysis_type": "advanced"
  }'
```

### 예시 3: Python 코드

```python
import requests

# API 엔드포인트
url = "http://localhost:8888/api/analysis/risk-scoring"

# 요청 데이터
data = {
    "chain_id": 1,
    "address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
    "max_hops": 3,
    "analysis_type": "basic"
}

# POST 요청
response = requests.post(url, json=data)

if response.status_code == 200:
    result = response.json()
    risk_score = result["data"]["final_score"]
    risk_level = result["data"]["risk_level"]
    print(f"Risk Score: {risk_score}, Risk Level: {risk_level}")
else:
    print(f"Error: {response.json()}")
```

### 예시 4: JavaScript (Fetch API)

```javascript
// API 엔드포인트
const url = "http://localhost:8888/api/analysis/risk-scoring";

// 요청 데이터
const data = {
  chain_id: 1,
  address: "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
  max_hops: 3,
  analysis_type: "basic",
};

// POST 요청
fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(data),
})
  .then((response) => response.json())
  .then((result) => {
    const riskScore = result.data.final_score;
    const riskLevel = result.data.risk_level;
    console.log(`Risk Score: ${riskScore}, Risk Level: ${riskLevel}`);
  })
  .catch((error) => console.error("Error:", error));
```

---

## 파라미터 상세 설명

### `chain_id`

지원되는 체인 ID:

- `1`: Ethereum
- `56`: BSC (Binance Smart Chain)
- `137`: Polygon
- 기타 체인 (리스크 스코어링 API 지원 범위에 따라)

### `address`

분석할 주소 (0x로 시작하는 16진수 문자열)

- 예: `0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be`

### `hop_count` / `max_hops`

거래 그래프의 최대 홉 수

- **1 hop**: 직접 거래만 분석
- **2 hops**: 직접 거래 + 1단계 상대방과의 거래
- **3 hops**: 직접 거래 + 2단계 상대방과의 거래 (권장)
- **4+ hops**: 더 깊은 분석 (시간이 오래 걸릴 수 있음)

**권장값**: 2~3

### `max_addresses_per_direction`

각 방향(송금/수금)당 최대 분석 주소 수

- 기본값: 10
- 범위: 1~50 (너무 크면 응답 시간이 길어짐)

**권장값**: 10~20

### `analysis_type`

분석 타입:

- **`basic`**: 기본 룰 기반 스코어링 (빠름)
- **`advanced`**: 룰 기반 + 그래프 패턴 탐지 (느리지만 정확)

**권장값**: 일반적으로 `basic`, 더 정확한 분석이 필요하면 `advanced`

---

## 트러블슈팅

### 에러 1: "Risk scoring API call failed: Connection refused"

**원인**: 리스크 스코어링 API가 실행되지 않음

**해결**:

1. 리스크 스코어링 API가 실행 중인지 확인
2. `RISK_SCORING_API_URL` 환경 변수가 올바른지 확인
3. 포트 5001이 열려있는지 확인

```bash
# 리스크 스코어링 API 확인
curl http://localhost:5001/health

# 환경 변수 확인
echo $RISK_SCORING_API_URL
```

### 에러 2: "chain_id is required"

**원인**: 필수 파라미터 누락

**해결**: `chain_id`와 `address` 파라미터를 모두 제공

### 에러 3: "analysis_type must be 'basic' or 'advanced'"

**원인**: 잘못된 `analysis_type` 값

**해결**: `analysis_type`을 "basic" 또는 "advanced"로 설정

### 에러 4: 응답 시간이 너무 길다

**원인**: `hop_count` 또는 `max_addresses_per_direction`이 너무 큼

**해결**:

- `hop_count`를 2~3으로 줄이기
- `max_addresses_per_direction`을 10 이하로 줄이기

---

## 체크리스트

통합 완료 후 다음을 확인하세요:

- [ ] 리스크 스코어링 API가 실행 중인가?
- [ ] `RISK_SCORING_API_URL` 환경 변수가 설정되어 있는가?
- [ ] `requests` 패키지가 설치되어 있는가?
- [ ] `/api/analysis/risk-scoring` 엔드포인트가 정상 작동하는가?
- [ ] 테스트 주소로 분석이 정상적으로 이루어지는가?

---

## 관련 문서

- [EC2 배포 가이드](./DEPLOYMENT.md)
- [리스크 스코어링 API 레포](https://github.com/paran-needless-to-say/aml-risk-engine2)

---

## 문의

API 사용 중 문제가 발생하면 백엔드 팀이나 예림님께 문의해주세요!
