# Trading System

Planner와 Executor를 분리한 안전·감사·재현 가능한 월간 리밸런싱 자동매매 OS

## 빠른 시작 (5분 안에 로컬 실행)

### 1. 사전 요구사항

- Python 3.11+
- Docker & Docker Compose (또는 로컬 PostgreSQL)
- Poetry (또는 pip)

### 2. 환경 설정

```bash
# 저장소 클론
git clone <repo-url>
cd trading_system

# 의존성 설치
poetry install
# 또는
pip install -e .

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

### 3. 데이터베이스 시작 및 마이그레이션

```bash
# Docker로 DB 시작
make db-up

# 또는 docker-compose 사용
docker-compose up -d postgres

# 마이그레이션 실행
make migrate
```

### 4. 애플리케이션 실행

```bash
# 터미널 1: API 서버
make run-api

# 터미널 2: UI
make run-ui

# 터미널 3: Worker (선택)
make run-worker
```

### 5. 접속

- API: http://localhost:8000
- UI: http://localhost:8501
- API Docs: http://localhost:8000/docs

## 프로젝트 구조

```
trading_system/
  api_docs/          # KIS API SSOT CSV
  apps/
    api/             # FastAPI
    ui/              # Streamlit
    worker/          # APScheduler
  packages/
    core/            # Models, schemas, interfaces
    brokers/         # KIS adapters
    data/            # Data pipeline
    ops/             # Slack, logging, guards
  tests/             # Tests
  docs/              # Documentation
```

## 주요 기능

- **Phase 1 안전장치**: `ENABLE_LIVE_TRADING=false`일 때 Live 주문 발행 불가
- **KIS API SSOT**: `api_docs/` CSV에서 API 스펙 로드
- **상태 머신**: Plan 승인 없이 실행 불가, Idempotency 보장
- **Slack 알림**: Webhook 없어도 동작 (no-op)

## 개발

```bash
# 테스트
make test

# 린트
make lint

# 포맷
make format
```

## 문서

- [PRD](docs/prd.md): 제품 요구사항 문서
- [DECISIONS](docs/decisions.md): 아키텍처 결정 사항
- [RUNBOOK](docs/runbook.md): 운영 가이드

## 라이선스

Private

