# 보안 그룹 설정 후 Swagger UI 테스트

## 현재 설정
- 포트: 5001
- 소스: 내 IP (`125.132.10.41/32`)
- 의미: 현재 PC에서만 접근 가능

## 테스트 방법

### 1. 규칙 저장 후 확인

1. **"규칙 저장"** 버튼 클릭
2. 저장 완료 메시지 확인

### 2. 브라우저에서 테스트

```
http://3.38.112.25:5001/health
```

또는 Swagger UI:
```
http://3.38.112.25:5001/api-docs
```

### 3. 터미널에서 테스트

```bash
# Health Check
curl http://3.38.112.25:5001/health

# Swagger UI JSON
curl http://3.38.112.25:5001/apispec.json
```

## 예상 결과

### 성공 응답
```json
{
  "status": "ok",
  "service": "aml-risk-engine"
}
```

### 실패 시 확인 사항

1. **서버가 실행 중인가?**
   ```bash
   # EC2 서버에 SSH 접속 후
   docker-compose -f docker-compose.prod.yml ps
   ```

2. **포트가 리스닝 중인가?**
   ```bash
   # EC2 서버에서
   curl http://localhost:5001/health
   ```

3. **보안 그룹 규칙이 저장되었는가?**
   - AWS 콘솔에서 다시 확인
   - 인바운드 규칙 목록에 포트 5001이 있는지 확인

## 다른 위치에서 접근해야 하는 경우

소스 유형을 **"모든 위치"** 또는 **"0.0.0.0/0"**로 변경하세요.

