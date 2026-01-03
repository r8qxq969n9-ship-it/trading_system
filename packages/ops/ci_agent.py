"""CI 자동 수정 에이전트.

CI 실패 시 로그를 분석하고 자동 수정 가능한 이슈를 처리합니다.
"""

import logging
import os
import re
import subprocess
import sys
from typing import Any

import httpx

from packages.core.models import AlertLevel
from packages.ops.slack import send

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"
MAX_RETRIES = 5


class CIFailureReason:
    """CI 실패 원인 분류."""

    RUFF_LINT = "ruff_lint"
    BLACK_FORMAT = "black_format"
    TEST_FAILURE = "test_failure"
    MIGRATION_FAILURE = "migration_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    UNKNOWN = "unknown"


def get_github_token() -> str:
    """GitHub 토큰 가져오기."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return token


def get_retry_count_from_commits() -> int:
    """최근 커밋에서 [CI Auto-Fix] 커밋 수를 세어 재시도 횟수 계산."""
    try:
        # 원격 저장소 정보 가져오기 (최신 정보 반영)
        subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            timeout=10,
            check=False,
        )

        # 현재 브랜치 가져오기
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = branch_result.stdout.strip()

        # 원격 브랜치가 있으면 원격 기준, 없으면 로컬 기준
        remote_branch = f"origin/{branch}"
        check_remote = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch],
            capture_output=True,
            timeout=5,
            check=False,
        )

        if check_remote.returncode == 0 and check_remote.stdout.strip():
            # 원격 브랜치 기준으로 확인
            log_target = remote_branch
        else:
            # 로컬 브랜치 기준으로 확인
            log_target = branch

        # 최근 20개 커밋에서 [CI Auto-Fix] 커밋 확인
        result = subprocess.run(
            ["git", "log", log_target, "--oneline", "-20", "--grep", "[CI Auto-Fix]"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout:
            # 매칭되는 커밋 수 계산
            lines = [line for line in result.stdout.strip().split("\n") if line and "[CI Auto-Fix]" in line]
            return len(lines)
        return 0
    except Exception as e:
        logger.warning(f"Failed to get retry count from commits: {e}, defaulting to 0")
        return 0


def parse_run_url(run_url: str) -> tuple[str, str, str]:
    """워크플로우 run URL에서 owner, repo, run_id 추출.

    예: https://github.com/owner/repo/actions/runs/1234567890
    """
    pattern = r"github\.com/([^/]+)/([^/]+)/actions/runs/(\d+)"
    match = re.search(pattern, run_url)
    if not match:
        raise ValueError(f"Invalid run URL format: {run_url}")
    return match.group(1), match.group(2), match.group(3)


def download_workflow_logs(owner: str, repo: str, run_id: str, token: str) -> str:
    """워크플로우 run의 로그 다운로드."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        logger.error(f"Failed to download logs: {e}")
        raise


def analyze_ci_logs(logs: str) -> dict[str, Any]:
    """CI 로그를 분석하여 실패 원인 추출."""
    failure_reason = CIFailureReason.UNKNOWN
    failed_step = None
    error_message = ""

    # ruff 실패 감지
    if re.search(r"ruff check", logs, re.IGNORECASE) and re.search(
        r"error|failed|exit code [1-9]", logs, re.IGNORECASE
    ):
        failure_reason = CIFailureReason.RUFF_LINT
        failed_step = "Lint with ruff"
        # ruff 오류 메시지 추출
        ruff_errors = re.findall(r"ruff check.*?(?=\n\n|\n[A-Z]|\Z)", logs, re.DOTALL | re.IGNORECASE)
        if ruff_errors:
            error_message = ruff_errors[-1][:500]  # 최대 500자

    # black 실패 감지
    elif re.search(r"black --check", logs, re.IGNORECASE) and re.search(
        r"would reformat|reformatted|exit code [1-9]", logs, re.IGNORECASE
    ):
        failure_reason = CIFailureReason.BLACK_FORMAT
        failed_step = "Format check with black"
        # black 오류 메시지 추출
        black_errors = re.findall(r"black.*?(?=\n\n|\n[A-Z]|\Z)", logs, re.DOTALL | re.IGNORECASE)
        if black_errors:
            error_message = black_errors[-1][:500]

    # pytest 실패 감지
    elif re.search(r"pytest", logs, re.IGNORECASE) and re.search(
        r"FAILED|ERROR|failed|error", logs, re.IGNORECASE
    ):
        failure_reason = CIFailureReason.TEST_FAILURE
        failed_step = "Test with pytest"
        # pytest 오류 메시지 추출
        pytest_errors = re.findall(r"FAILED.*?(?=\n\n|\n[A-Z]|\Z)", logs, re.DOTALL | re.IGNORECASE)
        if pytest_errors:
            error_message = pytest_errors[-1][:500]

    # migration 실패 감지
    elif re.search(r"alembic|migration", logs, re.IGNORECASE) and re.search(
        r"error|failed|exception", logs, re.IGNORECASE
    ):
        failure_reason = CIFailureReason.MIGRATION_FAILURE
        failed_step = "Run database migrations"
        migration_errors = re.findall(
            r"alembic.*?(?=\n\n|\n[A-Z]|\Z)", logs, re.DOTALL | re.IGNORECASE
        )
        if migration_errors:
            error_message = migration_errors[-1][:500]

    # 의존성 설치 실패 감지
    elif re.search(r"pip install|install dependencies", logs, re.IGNORECASE) and re.search(
        r"error|failed|exit code [1-9]", logs, re.IGNORECASE
    ):
        failure_reason = CIFailureReason.DEPENDENCY_FAILURE
        failed_step = "Install dependencies"
        dep_errors = re.findall(
            r"pip install.*?(?=\n\n|\n[A-Z]|\Z)", logs, re.DOTALL | re.IGNORECASE
        )
        if dep_errors:
            error_message = dep_errors[-1][:500]

    return {
        "failure_reason": failure_reason,
        "failed_step": failed_step,
        "error_message": error_message[:500] if error_message else "No specific error message found",
    }


def can_auto_fix(failure_reason: str) -> bool:
    """자동 수정 가능 여부 판단."""
    return failure_reason in [CIFailureReason.RUFF_LINT, CIFailureReason.BLACK_FORMAT]


def apply_fixes(failure_reason: str) -> bool:
    """자동 수정 적용."""
    try:
        if failure_reason == CIFailureReason.RUFF_LINT:
            logger.info("Applying ruff fixes...")
            result = subprocess.run(
                ["ruff", "check", ".", "--fix"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error(f"ruff fix failed: {result.stderr}")
                return False
            logger.info("Ruff fixes applied successfully")
            return True

        elif failure_reason == CIFailureReason.BLACK_FORMAT:
            logger.info("Applying black formatting...")
            result = subprocess.run(
                ["black", "."],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error(f"black format failed: {result.stderr}")
                return False
            logger.info("Black formatting applied successfully")
            return True

        return False
    except subprocess.TimeoutExpired:
        logger.error("Fix command timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to apply fixes: {e}")
        return False


def commit_and_push(retry_count: int, failure_reason: str) -> bool:
    """변경사항 커밋 및 push."""
    try:
        # 변경사항 확인
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if not result.stdout.strip():
            logger.info("No changes to commit")
            return False

        # git config 설정 (필요한 경우)
        subprocess.run(
            ["git", "config", "user.name", "CI Auto-Fix Agent"],
            check=False,
            timeout=5,
        )
        subprocess.run(
            ["git", "config", "user.email", "ci-agent@trading-system.local"],
            check=False,
            timeout=5,
        )

        # 변경사항 추가
        subprocess.run(["git", "add", "."], check=True, timeout=10)

        # 커밋 메시지 생성
        if failure_reason == CIFailureReason.RUFF_LINT:
            commit_msg = f"[CI Auto-Fix] Fix linting errors (retry {retry_count + 1})"
        elif failure_reason == CIFailureReason.BLACK_FORMAT:
            commit_msg = f"[CI Auto-Fix] Fix formatting errors (retry {retry_count + 1})"
        else:
            commit_msg = f"[CI Auto-Fix] Fix CI errors (retry {retry_count + 1})"

        # 커밋
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            timeout=10,
        )

        # 현재 브랜치 가져오기
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = branch_result.stdout.strip()

        # Push
        subprocess.run(
            ["git", "push", "origin", branch],
            check=True,
            timeout=30,
        )

        logger.info(f"Successfully committed and pushed changes (retry {retry_count + 1})")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to commit and push: {e}")
        return False


def main():
    """메인 로직."""
    # 환경변수에서 필요한 정보 가져오기
    run_url = os.getenv("GITHUB_RUN_URL")
    github_token = get_github_token()

    if not run_url:
        logger.error("GITHUB_RUN_URL environment variable is required")
        sys.exit(1)

    # 재시도 횟수 계산 (환경변수 또는 커밋 히스토리에서)
    retry_count = int(os.getenv("RETRY_COUNT", "0"))
    if retry_count == 0:
        # 커밋 히스토리에서 자동 계산
        retry_count = get_retry_count_from_commits()

    if retry_count >= MAX_RETRIES:
        logger.error(f"Maximum retries ({MAX_RETRIES}) reached. Stopping.")
        send(
            AlertLevel.ERROR,
            "dev",
            "CI Auto-Fix: Maximum Retries Reached",
            {
                "run_url": run_url,
                "retry_count": retry_count,
                "message": f"Failed to fix CI after {MAX_RETRIES} attempts",
            },
        )
        sys.exit(1)

    logger.info(f"Starting CI auto-fix agent (retry {retry_count + 1}/{MAX_RETRIES})")
    logger.info(f"Run URL: {run_url}")

    try:
        # URL 파싱
        owner, repo, run_id = parse_run_url(run_url)

        # 로그 다운로드
        logger.info("Downloading workflow logs...")
        logs = download_workflow_logs(owner, repo, run_id, github_token)

        # 로그 분석
        logger.info("Analyzing logs...")
        analysis = analyze_ci_logs(logs)
        failure_reason = analysis["failure_reason"]
        failed_step = analysis["failed_step"]
        error_message = analysis["error_message"]

        logger.info(f"Failure reason: {failure_reason}")
        logger.info(f"Failed step: {failed_step}")

        # 자동 수정 가능 여부 확인
        if not can_auto_fix(failure_reason):
            logger.warning(f"Cannot auto-fix: {failure_reason}")
            # DECISION_REQUIRED 알림
            send(
                AlertLevel.DECISION_REQUIRED,
                "decisions",
                "CI Auto-Fix: Manual Intervention Required",
                {
                    "run_url": run_url,
                    "failure_reason": failure_reason,
                    "failed_step": failed_step,
                    "error_message": error_message,
                    "retry_count": retry_count,
                    "recommended_action": "Review the CI failure and fix manually",
                },
            )
            sys.exit(1)

        # 자동 수정 적용
        logger.info("Applying automatic fixes...")
        if not apply_fixes(failure_reason):
            logger.error("Failed to apply fixes")
            sys.exit(1)

        # 커밋 및 push
        logger.info("Committing and pushing changes...")
        if not commit_and_push(retry_count, failure_reason):
            logger.warning("No changes to commit or push failed")
            # 변경사항이 없거나 push 실패한 경우
            if retry_count >= MAX_RETRIES - 1:
                # 마지막 시도에서도 실패한 경우
                send(
                    AlertLevel.ERROR,
                    "dev",
                    "CI Auto-Fix: No Changes or Push Failed",
                    {
                        "run_url": run_url,
                        "failure_reason": failure_reason,
                        "retry_count": retry_count + 1,
                        "message": "Auto-fix applied but no changes to commit or push failed",
                    },
                )
            sys.exit(1)

        # Slack 알림 (첫 번째 시도 또는 마지막 시도 전에만)
        if retry_count == 0 or retry_count == MAX_RETRIES - 1:
            send(
                AlertLevel.INFO if retry_count == 0 else AlertLevel.WARN,
                "dev",
                "CI Auto-Fix: Fixes Applied",
                {
                    "run_url": run_url,
                    "failure_reason": failure_reason,
                    "failed_step": failed_step,
                    "retry_count": retry_count + 1,
                    "message": "Automatic fixes applied and pushed. CI will rerun.",
                },
            )

        logger.info("CI auto-fix completed successfully. Waiting for CI to rerun...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"CI auto-fix failed: {e}", exc_info=True)
        send(
            AlertLevel.ERROR,
            "dev",
            "CI Auto-Fix: Error",
            {
                "run_url": run_url,
                "retry_count": retry_count,
                "error": str(e),
            },
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

