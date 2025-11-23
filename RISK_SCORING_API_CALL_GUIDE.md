# 백엔드에서 리스크 스코어링 API 호출 가이드

백엔드에서 리스크 스코어링 API를 호출하기 위해 필요한 모든 정보를 정리한 문서입니다.

---

## 1. 호출 URL

### 환경별 URL 설정

리스크 스코어링 API의 호출 URL은 **환경 변수** `RISK_SCORING_API_URL`로 설정됩니다.

#### 로컬 개발 환경 (Docker 없이 실행)

```bash
export RISK_SCORING_API_URL=http://localhost:5001
```

**호출 URL**: `http://localhost:5001/api/analyze/address`

#### EC2 서버 환경 (기본값 - 외부 접근)

**기본 설정**:

- 기본값: `http://3.38.112.25:5001` (EC2 Public IP)
- 외부에서 접근 가능하도록 설정됨

**호출 URL**: `http://3.38.112.25:5001/api/analyze/address`

**주의**: EC2 보안 그룹에서 포트 5001이 열려있어야 합니다.

#### Docker Compose 내부 네트워크 사용 (선택 사항)

Docker Compose 내부 네트워크를 사용하려면 `.env` 파일에 다음을 추가:

```bash
# .env 파일
RISK_SCORING_API_URL=http://risk-scoring:5001
```

또는 `docker-compose.prod.yml`에서 환경 변수로 오버라이드:

```yaml
environment:
  - RISK_SCORING_API_URL=http://risk-scoring:5001
```

**호출 URL**: `http://risk-scoring:5001/api/analyze/address` (Docker 내부 네트워크)

---

## 2. HTTP 메서드

**POST** (JSON Body 전송)

---

## 3. 파라미터 종류

### 3.1 전체 URL 구성

```
{RISK_SCORING_API_URL}/api/analyze/address
```

예시:

- Docker: `http://risk-scoring:5001/api/analyze/address`
- 로컬: `http://localhost:5001/api/analyze/address`
- EC2 외부: `http://3.38.112.25:5001/api/analyze/address`

### 3.2 Request Body (JSON)

#### 필수 파라미터

| 파라미터       | 타입    | 설명                                                  | 예시                                          |
| -------------- | ------- | ----------------------------------------------------- | --------------------------------------------- |
| `address`      | string  | 분석 대상 주소                                        | `"0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"` |
| `chain_id`     | integer | 체인 ID (1=Ethereum, 42161=Arbitrum, 43114=Avalanche) | `1`                                           |
| `transactions` | array   | 거래 히스토리 배열 (최소 1개 이상)                    | `[{...}]`                                     |

#### 선택 파라미터

| 파라미터        | 타입   | 기본값    | 설명                                    | 예시      |
| --------------- | ------ | --------- | --------------------------------------- | --------- |
| `analysis_type` | string | `"basic"` | 분석 타입 (`"basic"` 또는 `"advanced"`) | `"basic"` |

#### transactions 배열의 각 항목 (필수 필드)

| 필드                   | 타입    | 설명                                                             | 예시                     |
| ---------------------- | ------- | ---------------------------------------------------------------- | ------------------------ |
| `tx_hash`              | string  | 트랜잭션 해시                                                    | `"0xabc123..."`          |
| `chain_id`             | integer | 체인 ID                                                          | `1`                      |
| `timestamp`            | string  | ISO8601 UTC 형식 타임스탬프                                      | `"2025-01-15T10:00:00Z"` |
| `block_height`         | integer | 블록 높이 (정렬용)                                               | `21039493`               |
| `target_address`       | string  | 스코어링 대상 주소                                               | `"0x742d35..."`          |
| `counterparty_address` | string  | 상대방 주소                                                      | `"0xdef456..."`          |
| `label`                | string  | 엔티티 라벨 (`mixer`, `bridge`, `cex`, `dex`, `defi`, `unknown`) | `"mixer"`                |
| `is_sanctioned`        | boolean | OFAC/제재 리스트 매핑 결과                                       | `false`                  |
| `is_known_scam`        | boolean | Scam/phishing 블랙리스트 매핑                                    | `false`                  |
| `is_mixer`             | boolean | 믹서 여부                                                        | `true`                   |
| `is_bridge`            | boolean | 브릿지 여부                                                      | `false`                  |
| `amount_usd`           | number  | 시세 기반 환산 금액 (USD)                                        | `5000.0`                 |
| `asset_contract`       | string  | 자산 종류                                                        | `"0xETH"`                |

### 3.3 Request Body 예시

```json
{
  "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "chain_id": 1,
  "transactions": [
    {
      "tx_hash": "0xabc123...",
      "chain_id": 1,
      "timestamp": "2025-01-15T10:00:00Z",
      "block_height": 21039493,
      "target_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "counterparty_address": "0xdef456...",
      "label": "mixer",
      "is_sanctioned": false,
      "is_known_scam": false,
      "is_mixer": true,
      "is_bridge": false,
      "amount_usd": 5000.0,
      "asset_contract": "0xETH"
    }
  ],
  "analysis_type": "basic"
}
```

---

## 4. Response 형식

### 성공 응답 (200 OK)

```json
{
  "target_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "risk_score": 78,
  "risk_level": "high",
  "risk_tags": ["mixer_inflow", "sanction_exposure"],
  "fired_rules": [
    { "rule_id": "E-101", "score": 25 },
    { "rule_id": "C-001", "score": 30 }
  ],
  "explanation": "...",
  "completed_at": "2025-01-15T10:00:01Z",
  "timestamp": "2025-01-15T10:00:00Z",
  "chain_id": 1,
  "value": 5000.0
}
```

### 에러 응답

#### 400 Bad Request

```json
{
  "error": "Missing required field: address"
}
```

#### 500 Internal Server Error

```json
{
  "error": "Analysis failed: ..."
}
```

---

## 5. 백엔드 코드에서 사용 예시

### 현재 구현 코드 위치

`backend/src/api/risk_scoring.py`의 `call_risk_scoring_api()` 함수:

```python
def call_risk_scoring_api(
    address: str,
    chain_id: int,
    transactions: List[Dict[str, Any]],
    analysis_type: str = "basic"
) -> Dict[str, Any]:
    """
    리스크 스코어링 API 호출

    Args:
        address: 분석 대상 주소
        chain_id: 체인 ID
        transactions: 거래 배열
        analysis_type: "basic" 또는 "advanced"

    Returns:
        리스크 스코어링 결과
    """
    url = f"{RISK_SCORING_API_URL}/api/analyze/address"

    payload = {
        "address": address,
        "chain_id": chain_id,
        "transactions": transactions,
        "analysis_type": analysis_type
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Risk scoring API call failed: {str(e)}")
```

### 사용 방법

```python
from src.api.risk_scoring import call_risk_scoring_api

# 거래 데이터 준비
transactions = [
    {
        "tx_hash": "0xabc...",
        "chain_id": 1,
        "timestamp": "2025-01-15T10:00:00Z",
        "block_height": 21039493,
        "target_address": "0x742d35...",
        "counterparty_address": "0xdef456...",
        "label": "mixer",
        "is_sanctioned": False,
        "is_known_scam": False,
        "is_mixer": True,
        "is_bridge": False,
        "amount_usd": 5000.0,
        "asset_contract": "0xETH"
    }
]

# API 호출
result = call_risk_scoring_api(
    address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    chain_id=1,
    transactions=transactions,
    analysis_type="basic"
)

# 결과 확인
print(f"Risk Score: {result['risk_score']}")
print(f"Risk Level: {result['risk_level']}")
```

---

## 6. 환경별 동작 확인

### ✅ 로컬 개발 환경

- **URL**: `http://localhost:5001/api/analyze/address`
- **설정**: 환경 변수로 설정하거나 기본값 사용
- **테스트**: ✅ 성공 (테스트 완료)

### ✅ Docker Compose 환경

- **URL**: `http://risk-scoring:5001/api/analyze/address`
- **설정**: `docker-compose.prod.yml`에서 자동 설정
- **동작**: ✅ 정상 작동

### ✅ EC2 서버 환경

**EC2 서버 내부 (Docker Compose)**

- **URL**: `http://risk-scoring:5001/api/analyze/address`
- **설정**: `docker-compose.prod.yml`에서 자동 설정
- **동작**: ✅ 정상 작동 (같은 Docker 네트워크 내에서)

**EC2 서버 외부 접근**

- **URL**: `http://<EC2-PUBLIC-IP>:5001/api/analyze/address`
- **설정**: `.env` 파일에 `RISK_SCORING_API_URL=http://3.38.112.25:5001` 추가
- **주의**: EC2 보안 그룹에서 포트 5001이 열려있어야 함

---

## 7. 체인 ID 참고

| 체인              | Chain ID |
| ----------------- | -------- |
| Ethereum          | 1        |
| Arbitrum One      | 42161    |
| Avalanche C-Chain | 43114    |
| Base              | 8453     |
| Polygon           | 137      |
| BSC               | 56       |
| Optimism          | 10       |
| Blast             | 81457    |

---

## 8. 타임아웃 설정

현재 타임아웃: **30초**

- `analysis_type: "basic"`: 1-2초 소요
- `analysis_type: "advanced"`: 5-30초 소요

필요시 `timeout` 값을 조정할 수 있습니다.

---

## 요약

| 항목              | 값                                           |
| ----------------- | -------------------------------------------- |
| **호출 URL**      | `{RISK_SCORING_API_URL}/api/analyze/address` |
| **HTTP 메서드**   | `POST`                                       |
| **Content-Type**  | `application/json`                           |
| **필수 파라미터** | `address`, `chain_id`, `transactions`        |
| **선택 파라미터** | `analysis_type` (기본값: `"basic"`)          |
| **타임아웃**      | 30초                                         |

---

**✅ 결론**: 백엔드에서 리스크 스코어링 API를 올바르게 호출할 수 있습니다!

- 로컬, Docker Compose, EC2 모든 환경에서 동작합니다.
- 환경 변수 `RISK_SCORING_API_URL`로 URL을 설정하면 됩니다.
