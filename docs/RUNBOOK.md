# Runbook

운영 가이드 및 장애 대응 절차

## 장애 대응

### Kill Switch 활성화

1. UI에서 Controls 페이지 접속
2. "Turn ON" 버튼 클릭
3. 또는 API 호출:
   ```bash
   curl -X POST http://localhost:8000/controls/kill-switch \
     -H "Content-Type: application/json" \
     -d '{"on": true, "reason": "Emergency stop"}'
   ```

### Kill Switch 비활성화

1. UI에서 Controls 페이지 접속
2. "Turn OFF" 버튼 클릭
3. 또는 API 호출:
   ```bash
   curl -X POST http://localhost:8000/controls/kill-switch \
     -H "Content-Type: application/json" \
     -d '{"on": false, "reason": "Resume operations"}'
   ```

## 재시도 정책

### 일시 오류
- N회 재시도 (backoff)
- 재시도 실패 시 `FAILED` 상태로 기록

### 반복 실패
- `FAILED` 상태 기록
- Kill Switch 유지
- Slack ERROR 알림 발송

## Phase 2 Live 활성화 절차

1. **사전 요건 확인**
   - prod 배포 완료
   - 보안/복구 강화 완료
   - Gate 통과

2. **DECISION_REQUIRED Slack 알림 확인**
   - Live enable 승인 요청

3. **환경변수 설정**
   ```bash
   ENABLE_LIVE_TRADING=true
   TRADING_MODE=LIVE
   ```

4. **검증**
   - 8주 모니터링
   - S0=0, S1=0 확인

## 데이터베이스 마이그레이션

```bash
# 마이그레이션 실행
make migrate

# 또는 직접
python -m alembic upgrade head

# 롤백 (필요시)
python -m alembic downgrade -1
```

## 로그 확인

- **API 로그**: JSON 구조화 로그 (stdout)
- **DB 감사**: `audit_events` 테이블
- **알림 기록**: `alerts_sent` 테이블

## 헬스체크

```bash
curl http://localhost:8000/health
```

## 백업

- **DB 백업**: PostgreSQL 덤프
- **스냅샷**: `data_snapshots`, `portfolio_snapshots` 테이블

