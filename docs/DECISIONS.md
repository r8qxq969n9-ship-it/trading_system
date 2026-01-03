# Architecture Decisions

이 문서는 PRD v2.2의 Decision Log를 기록합니다.

## 초기 잠금값 (Phase 1)

### 전략
- **전략**: 월간 듀얼 모멘텀
- **Lookback**: 3개월
- **US bucket**: 상위 N=4
- **KR bucket**: 상위 M=2
- **KR/US split**: 40/60

### 리밸런싱
- **주기**: 월 1회
- **승인 필수**: No-Approve No-Trade

### Paper Trading
- **모드**: KIS 테스트/모의 + 자체 모의체결 보완
- **Live 주문 발행**: Phase 1에서 OFF (구조적으로 불가)

### Live Trading
- **활성화**: Phase 2에서만 활성화
- **Phase 1**: `ENABLE_LIVE_TRADING=false` 고정

### MCP
- **Phase 1 PMF까지**: Adapter 통합 완료 (호출 검증)
- **Live 주문**: Phase 2에서 enable

### 미체결/부분체결 정책
- **재주문**: 없음
- **처리**: T+X분 후 취소

### 현금 부족 정책
- **매수 순서**: 랭킹 상위부터
- **부족분**: SKIPPED 기록

### 의존성 관리
- **도구**: Poetry 선택
- **이유**: Python 생태계에서 널리 사용되고 안정적

