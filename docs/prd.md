# Trading System PRD v2.2 (Single Source of Truth)

* Repo: `trading_system`
* Product Owner: Jason
* Primary Executor: Cursor Agent (구현/디버깅/테스트/배포 전담)
* Supporting Tools: Codex(설계/테스트케이스/초안), Copilot(반복 구현/PR 품질)
* Timezone: KST (+0900)
* Alerting: Slack Incoming Webhook (필수)
* KIS API SSOT: 프로젝트 루트 `api_docs/`의 CSV (필수)

> **목표:** 이 문서 하나로 개발을 끝낸다.
> 변경은 `docs/DECISIONS.md`에만 기록한다.
> 사용자는 개발 현황을 모니터링할 수 없으므로, 개발/운영 과정의 모든 상태 변화는 Slack으로 자동 통보한다.

---

## 0. Live(실전) 범위 결정 (확정)

### 0.1 결론(고정)

* **Phase 1:** localhost 중심으로 **PoC → MVP → PMF를 "Simulation + Paper(모의)" 모드로 완성**한다.

  * Phase 1 기본값: **Live 주문 비활성(Feature Flag OFF)**
  * Live 관련 코드는 존재 가능하나, **실계좌 주문 발행은 구조적으로 불가**해야 한다.
* **Phase 2:** 배포/보안/복구/감사 강화 후 **Live(실전) 모드를 활성화**한다.

### 0.2 Phase 1/2의 "실전(Live)" 정의

* **Live = 실계좌로 실제 주문 발행(place_order) 가능**
* Phase 1에서 허용되는 것은:

  * KIS 시세 조회/계좌 조회(가능하면) + Paper 체결(모의체결 or 테스트환경)
  * 단, **실계좌 주문 발행은 어떤 경로로도 불가**

---

## 1. 제품 정의

### 1.1 한 줄 정의

**Planner(계획 생성)와 Executor(실행)를 분리하고, 사람이 승인해야만 실행되는 안전·감사·재현 가능한 월간 리밸런싱 자동매매 OS**

### 1.2 운영 모드

* **SIMULATION:** 과거 데이터 백테스트(재현성/성능)
* **PAPER:** 실시간 데이터 + 모의 체결(또는 KIS 테스트 환경)로 운영 흐름 검증
* **LIVE:** 실계좌 주문(Phase 2에서만 enable)

### 1.3 고정 제약(초기값)

* Target Vol: 12%/년 (달성 "시도" + 리포트)
* MDD 정책 목표: -15% (즉시 청산이 아닌 "노출 축소/중단" 우선)
* Max positions: 20
* Max weight per name: 8%
* KR/US split: 40/60
* Rebalance: 월 1회 (기본)
* **No-Approve No-Trade**
* Slack: Incoming Webhook(필수)

---

## 2. SSOT(단일 소스) & 레퍼런스

### 2.1 KIS API 상세 문서 (SSOT)

* 프로젝트 루트 `api_docs/` 내 CSV가 **단일 소스**다.
* 구현 규칙:

  * 모든 endpoint/tr_id/요청·응답 필드/필수 헤더는 **CSV에서 로드**
  * 코드 하드코딩 금지(예외: 공통 프레임워크 수준의 키 이름만 허용)
  * CSV에서 찾지 못한 API는 호출 금지(= 개발자가 SSOT를 먼저 갱신/확인)

### 2.2 KIS GitHub 2개(필수 참조)

* `koreainvestment/open-trading-api`
* `koreainvestment/koreainvestment-mcp`
* 구현 규칙:

  * 인증/토큰/해시키/샘플 호출 패턴은 레퍼런스의 의미 체계를 따른다.
  * PR에 "참조한 레퍼런스/근거"를 남긴다.

### 2.3 MCP 요구사항(필수)

* **DevEx:** 개발 중 API 탐색/스펙 확인에 MCP를 적극 활용 가능(도구 단계)
* **Product:** 완성된 프로그램에서 **MCP Adapter를 통해 브로커 호출이 가능**해야 함

  * Phase 1 PMF까지 "MCP Adapter 통합 + 호출 성공/파싱 검증"
  * 단, Phase 1에서는 Live 주문 발행은 OFF 유지 가능

---

## 3. 최상위 원칙(우선순위)

1. **Safety First:** S0(치명 사고) 0건이 최우선
2. **No-Approve No-Trade:** 승인 없이는 구조적으로 실행 불가
3. **Idempotency:** 같은 `plan_id`는 절대 2번 실행되지 않는다
4. **Auditability:** 누가/언제/왜/무엇을 했는지 100% 남긴다
5. **Reproducibility:** 동일 입력+동일 데이터 스냅샷 → 동일 Proposal
6. **User Zero-Ops:** 사용자는 모니터링 불가 → Slack이 상태를 알려야 한다
7. **User Intervention = Decision Only:** 사용자 개입은 "의사결정"만, PR/머지/배포는 자동화

---

## 4. 사용자 개입 최소화(강제 규칙)

### 4.1 사용자 개입(허용) 3가지

1. Gate 통과 선언(G1/G2/G3/Phase2 Live Gate)
2. Live enable(Phase 2) 승인
3. 정책 예외 승인(제약 위반 강행 등)

### 4.2 나머지는 자동

* Issue/PR/리뷰/머지/릴리즈/배포/알림 자동화(에이전트+CI)
* 사용자는 Slack에서 **결정만** 한다.

---

## 5. Slack 알림(개발+운영 신경계)

### 5.1 Webhook 환경변수(필수)

* `SLACK_WEBHOOK_DEV`
* `SLACK_WEBHOOK_ALERTS`
* `SLACK_WEBHOOK_DECISIONS`

### 5.2 레벨

* `INFO`, `WARN`, `ERROR`, `DECISION_REQUIRED`

### 5.3 필수 이벤트(강제)

* PR 생성/업데이트 요약(자동)
* CI 시작/성공/실패
* 배포 시작/성공/실패
* DB 마이그레이션 적용/실패
* Plan 생성/승인/거절/만료
* 실행 시작/완료/실패
* Kill Switch ON/OFF
* Gate 결과 요약

### 5.4 DECISION_REQUIRED 트리거(무조건)

* Phase 2(Live) 진입 여부
* Live Feature Flag ON 요청
* 되돌리기 어려운 변경(데이터 마이그레이션/아키텍처 교체)
* 정책 예외(제약 위반인데 진행할지)

### 5.5 메시지 템플릿(고정)

* Title: `[LEVEL][env] component - short`
* Body(JSON):

  * `run_id`, `commit_sha`, `pr_url`
  * `impact`
  * `recommended_action`
  * `decision_options`(DECISION_REQUIRED만)
  * `timeout`(DECISION_REQUIRED만)

---

## 6. 기술 스택(고정: 단순화로 오류/개입 최소화)

> Phase 1은 Python 단일 생태계로 고정한다.

* Backend API: FastAPI (Python)
* GUI: Streamlit (Python) — 운영 콘솔 중심
* DB: Postgres
* Migration: Alembic
* Scheduler: APScheduler(로컬) + (Phase2) Render cron/worker
* Tests: pytest
* Lint/Format: ruff + black
* Logging: JSON 구조화 로그 + DB `runs/audit_events`
* Broker modes:

  * `direct`: KIS 직접 연동
  * `mcp`: KIS MCP sidecar 연동

---

## 7. 리포지토리 구조(필수)

```
trading_system/
  api_docs/                     # KIS SSOT CSV
  apps/
    api/                        # FastAPI
    ui/                         # Streamlit
    worker/                     # scheduler/planner/executor
  packages/
    core/                       # strategy/risk/optimizer/order_builder
    brokers/
      kis_direct/               # direct adapter
      kis_mcp/                  # mcp adapter
    data/                       # snapshots/marketdata pipeline
    ops/                        # slack, logging, health, guards
  docs/
    PRD.md
    DECISIONS.md
    RUNBOOK.md
  tests/
    unit/
    integration/
    e2e/
  .github/workflows/
    ci.yml
    notify-slack.yml
    release.yml
  docker-compose.yml
  README.md
```

---

## 8. 전략 명세(Phase 1 고정)

### 8.1 초기 전략: 월간 듀얼 모멘텀 (잠금)

* Lookback: 3개월(기본)
* 선택:

  * US bucket: 상위 N=4
  * KR bucket: 상위 M=2 (또는 1; Phase 1 기본 2)
* 배분:

  * KR/US split 40/60 준수
  * 각 bucket 내 균등 배분(Phase 1 단순화)
  * 제약 위반 시 자동 축소/재분배
* 모멘텀 점수:

  * `score = price(t) / price(t-lookback) - 1`

### 8.2 유니버스 정의(필수 파일 포맷)

* `config/universe_us.csv`, `config/universe_kr.csv`
* 컬럼:

  * `symbol` (필수)
  * `name` (선택)
  * `type` (ETF/STOCK, 선택)
  * `enabled` (true/false, 선택; 기본 true)

---

## 9. 리스크/제약 체크(필수)

### 9.1 Plan 생성 시 체크

* positions ≤ 20
* weight per name ≤ 8%
* KR/US split 준수(± 허용오차 1%)
* 데이터 결측/이상치(가격 0/NaN/급변) 감지
* 현금 여력(매도 후 매수 가능 여부)

### 9.2 제약 위반 처리

* Plan 생성 실패 또는 승인 불가
* 실패 사유는 UI/Slack에 노출
* 예외 진행은 **DECISION_REQUIRED**로만 가능

---

## 10. 주문/체결 정책(Phase 1 MVP 고정)

### 10.1 실행 순서

* **SELL → BUY**

### 10.2 부분체결/미체결

* 부분체결: 체결분 반영, 잔여는 `T+X분 후 취소`
* 미체결: `T+X분 후 취소`
* **재주문 없음(Phase 1 고정)**

### 10.3 현금 부족

* 매수는 랭킹 상위부터 가용 현금 내에서만 생성
* 부족분은 `SKIPPED` 기록 + 사유 명시

### 10.4 실패/재시도

* 일시 오류: N회 재시도(backoff)
* 반복 실패: `FAILED` + Kill Switch 유지 + Slack ERROR

---

## 11. 상태 머신(강제)

* Plan: `PROPOSED → APPROVED/REJECTED/EXPIRED`
* Execution: `PENDING → RUNNING → DONE/FAILED/CANCELED`
* Kill Switch: `ON/OFF`

**규칙**

* APPROVED가 아니면 실행 불가(403)
* Kill Switch ON이면 주문 발행 0 (Paper에서도 "실행 자체"를 막음)

---

## 12. 데이터/감사/재현성(필수)

### 12.1 필수 저장 엔티티

* `config_versions`, `data_snapshots`, `portfolio_snapshots`
* `rebalance_plans`, `plan_items`
* `executions`, `orders`, `fills`
* `runs`, `audit_events`, `alerts_sent`, `controls`

### 12.2 재현 키

* `strategy_version`(코드 해시)
* `config_version_id`
* `data_snapshot_id`
* `plan_id`, `run_id`

---

## 13. DB 스키마(필수: 그대로 구현)

### 13.1 Tables

#### `config_versions`

* `id` uuid pk
* `mode` enum(SIMULATION|PAPER|LIVE)
* `strategy_name` text
* `strategy_params` jsonb
* `constraints` jsonb
* `created_at` timestamptz
* `created_by` text

#### `data_snapshots`

* `id` uuid pk
* `source` text
* `asof` timestamptz
* `meta` jsonb
* `created_at` timestamptz

#### `portfolio_snapshots`

* `id` uuid pk
* `asof` timestamptz
* `mode` enum
* `positions` jsonb
* `cash` numeric
* `nav` numeric
* `created_at` timestamptz

#### `rebalance_plans`

* `id` uuid pk
* `run_id` uuid
* `config_version_id` uuid fk
* `data_snapshot_id` uuid fk
* `status` enum(PROPOSED|APPROVED|REJECTED|EXPIRED)
* `summary` jsonb
* `created_at` timestamptz
* `approved_at` timestamptz null
* `approved_by` text null
* `rejected_at` timestamptz null
* `rejected_by` text null
* `expires_at` timestamptz

#### `plan_items`

* `id` uuid pk
* `plan_id` uuid fk
* `symbol` text
* `market` enum(KR|US)
* `current_weight` numeric
* `target_weight` numeric
* `delta_weight` numeric
* `reason` text
* `checks` jsonb

#### `executions`

* `id` uuid pk
* `plan_id` uuid fk **unique** (idempotency)
* `status` enum(PENDING|RUNNING|DONE|FAILED|CANCELED)
* `started_at` timestamptz null
* `ended_at` timestamptz null
* `policy` jsonb
* `error` text null

#### `orders`

* `id` uuid pk
* `plan_id` uuid fk
* `execution_id` uuid fk null
* `symbol` text
* `side` enum(BUY|SELL)
* `qty` numeric
* `order_type` text
* `limit_price` numeric null
* `status` enum(CREATED|SENT|PARTIAL|FILLED|CANCELED|FAILED|SKIPPED)
* `broker_order_id` text null
* `error` text null
* `created_at` timestamptz

#### `fills`

* `id` uuid pk
* `order_id` uuid fk
* `filled_qty` numeric
* `filled_price` numeric
* `filled_at` timestamptz
* `raw` jsonb

#### `runs`

* `id` uuid pk
* `kind` enum(SIMULATION|PAPER|PLAN|EXECUTE)
* `status` enum(STARTED|DONE|FAILED)
* `started_at` timestamptz
* `ended_at` timestamptz null
* `meta` jsonb
* `error` text null

#### `audit_events`

* `id` uuid pk
* `event_type` text
* `actor` text
* `ref_type` text
* `ref_id` uuid
* `payload` jsonb
* `created_at` timestamptz

#### `alerts_sent`

* `id` uuid pk
* `level` enum(INFO|WARN|ERROR|DECISION_REQUIRED)
* `channel` text
* `title` text
* `body` jsonb
* `sent_at` timestamptz

#### `controls`

* `id` int pk (=1 고정)
* `kill_switch` bool
* `reason` text null
* `updated_at` timestamptz

### 13.2 Index/Constraints

* `executions.plan_id` UNIQUE
* `rebalance_plans(status, created_at)` index
* `orders(plan_id, status)` index

---

## 14. API 명세(FastAPI) (필수)

### 14.1 공통 응답 규칙

* 모든 응답에 `request_id`, `run_id` 포함(없으면 생성)
* 에러 표준:

  * `code`, `message`, `details`, `hint`

### 14.2 Endpoints

* `GET /health`

* `GET /controls`

* `POST /controls/kill-switch` `{ "on": true|false, "reason": "..." }`

* `GET /configs/latest`

* `POST /configs`

* `POST /plans/generate`

* `GET /plans?status=&from=&to=`

* `GET /plans/{plan_id}`

* `POST /plans/{plan_id}/approve`

* `POST /plans/{plan_id}/reject`

* `POST /plans/{plan_id}/expire`

* `POST /executions/{plan_id}/start` (APPROVED만)

* `GET /executions?status=&from=&to=`

* `GET /executions/{execution_id}`

* `GET /portfolio/latest`

* `POST /data/snapshot`

---

## 15. GUI 명세(Streamlit) (필수)

### 15.1 화면

* Dashboard
* Config
* Proposals(List)
* Proposal Detail(Approve/Reject)
* Executions
* Positions
* Audit/Logs
* Controls(Kill Switch)

### 15.2 Proposal Detail "요약 3줄"(강제)

1. KR/US 비중 변화 요약
2. Top 3 매매 변화
3. 제약/리스크 체크 결과(통과/실패 + 사유)

### 15.3 승인 UX

* 버튼 1회로 승인/거절 완료
* 승인 즉시 Slack 알림
* 승인 기한 표시 + 만료 자동 처리

---

## 16. KIS 연동 설계(Direct + MCP) (필수)

### 16.1 공통 인터페이스 `IBroker`

* `get_token()/refresh_token()`
* `get_quotes(symbols)`
* `get_balance()`
* `place_order(order)`  (Phase 1에서는 호출 자체가 금지되거나 no-op)
* `get_orders()/get_fills()`
* `cancel_order(id)`

### 16.2 Direct Adapter 규칙

* `api_docs/` CSV에서 스펙을 로드하여 요청 구성
* 스펙 미존재 시 즉시 실패(SSOT 갱신 유도)

### 16.3 MCP Adapter 규칙

* sidecar 방식 실행 가능
* `BROKER_MODE=direct|mcp` 스위치 제공
* Phase 1 PMF까지:

  * MCP 경로로 시세/잔고 등 호출 성공 및 파싱 검증
* Phase 2:

  * Live 주문 발행을 MCP 경로로도 가능해야 함

---

## 17. Phase 1/2 Feature Flags (필수)

### 17.1 필수 환경변수

* `APP_ENV=local|staging|prod`
* `TRADING_MODE=SIMULATION|PAPER|LIVE`
* `ENABLE_LIVE_TRADING=true|false`  (**Phase 1 항상 false**)
* `BROKER_MODE=direct|mcp`
* Slack webhooks 3종(섹션 5.1)
* KIS 인증/계좌 관련 키들(프로젝트에서 표준 명명으로 확정)

### 17.2 강제 규칙

* `ENABLE_LIVE_TRADING=false`이면:

  * `place_order()` 경로는 무조건 차단(예외 없음)
  * UI에서도 Live 선택 불가
  * API에서도 Live 실행 요청은 403

---

## 18. CI/CD (사용자 개입 제거)

### 18.1 GitHub Actions(필수)

* `ci.yml`: lint/test
* `notify-slack.yml`: PR/CI/릴리즈 이벤트 Slack 발송
* `release.yml`: 태그 릴리즈 + (Phase 2) 배포

### 18.2 자동 머지(권장)

* required checks 통과 시 automerge
* 사용자 PR 승인 요구 없음

---

## 19. Gate(검증 루프)

### G1 (PoC)

* Simulation 재현 가능
* Paper 자동 실행 3영업일 연속 성공
* GUI에서 설정→Plan→승인(모의)→결과 확인 가능
* Slack 알림 1분 내

### G2 (MVP)

* Paper 2주 안정 운영(치명 사고 0)
* 정책(현금부족/미체결/부분체결) 고정 + UI/Slack 반영
* Kill Switch 검증

### G3 (PMF)

* MCP Adapter 통합 완료(Direct/MCP 전환 가능)
* 운영 부담 ≤ 15분에 근접(프리뷰/리포트 자동화)

### Phase 2 Live Gate

* prod 배포 + 보안/복구 강화 완료
* DECISION_REQUIRED로 Live enable 승인
* 실전 8주: S0=0, S1=0

---

## 20. E2E 테스트 10개(완료 판정)

1. Plan 생성 정상
2. 제약 위반 시 생성 실패 + 사유
3. 승인 없이 실행 차단
4. 승인 후 1회만 실행(idempotency)
5. SELL→BUY 순서 보장
6. 현금 부족 시 매수 축소/스킵 기록
7. 부분체결→잔여 취소 정책 적용
8. 토큰 만료 자동 갱신
9. 데이터 결측/이상치 감지→자동중단+알림
10. Kill Switch ON→주문 발행 0

---

## 21. Decision Log (초기 잠금)

* 전략: 월간 듀얼 모멘텀
* 리밸런싱: 월 1회
* Paper: KIS 테스트/모의 + 자체 모의체결 보완
* Live: **Phase 2에서만 활성화(Phase 1 OFF)**
* MCP: Phase 1 PMF까지 adapter 통합(호출 검증), Live는 Phase 2에서 enable
* 미체결/부분체결: 재주문 없음, T+X 후 취소
* 현금 부족: 랭킹 상위부터 매수, 부족분 스킵

