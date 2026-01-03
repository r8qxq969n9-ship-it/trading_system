"""CI 자동 수정 에이전트.

CI 실패 시 로그를 분석하고 자동 수정 가능한 이슈를 처리합니다.
"""

import gzip
import io
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


def get_failed_job_and_step(owner: str, repo: str, run_id: str, token: str) -> tuple[str | None, str | None]:
    """GitHub Jobs API를 사용하여 실패한 job과 step 찾기.
    
    Returns:
        (failed_job_name, failed_step_name)
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    try:
        response = httpx.get(url, headers=headers, params={"per_page": 100}, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        
        jobs = data.get("jobs", [])
        for job in jobs:
            if job.get("conclusion") == "failure":
                job_name = job.get("name", "unknown")
                # 실패한 step 찾기
                steps = job.get("steps", [])
                for step in steps:
                    if step.get("conclusion") == "failure":
                        step_name = step.get("name", "unknown")
                        return job_name, step_name
                # step이 없으면 job name 반환
                return job_name, job_name
        
        # 실패한 job이 없으면 첫 번째 job 반환 (fallback)
        if jobs:
            return jobs[0].get("name", "unknown"), "unknown"
        
        return None, None
    except httpx.HTTPError as e:
        logger.error(f"Failed to get jobs: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error getting failed job/step: {e}")
        return None, None


def get_job_logs(owner: str, repo: str, job_id: int, token: str) -> str:
    """Job logs 다운로드 및 파싱.
    
    Returns:
        로그 텍스트 (최대 40줄의 에러 부분)
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    try:
        response = httpx.get(url, headers=headers, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        
        # Content-Type 확인
        content_type = response.headers.get("content-type", "")
        content = response.content
        
        # gzip 압축 해제 시도
        if "gzip" in content_type or content.startswith(b"\x1f\x8b"):
            try:
                content = gzip.decompress(content)
            except Exception:
                pass  # gzip이 아니면 그대로 사용
        
        # 텍스트로 변환
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="ignore")
        
        # 마지막 에러 부분 추출 (최대 40줄)
        lines = text.split("\n")
        # 에러가 있는 부분 찾기
        error_lines = []
        for i in range(len(lines) - 1, max(0, len(lines) - 100), -1):
            line = lines[i]
            if any(keyword in line.lower() for keyword in ["error", "failed", "exception", "traceback"]):
                error_lines.insert(0, line)
                if len(error_lines) >= 40:
                    break
        
        if error_lines:
            return "\n".join(error_lines[-40:])
        
        # 에러가 없으면 마지막 40줄 반환
        return "\n".join(lines[-40:])
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to fetch logs: status_code={e.response.status_code}, body={e.response.text[:500]}")
        return f"could not fetch logs: status_code={e.response.status_code}, body={e.response.text[:200]}"
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch logs: {e}")
        return f"could not fetch logs: {str(e)}"
    except Exception as e:
        logger.error(f"Error parsing logs: {e}")
        return f"could not parse logs: {str(e)}"


def get_failed_job_id(owner: str, repo: str, run_id: str, token: str) -> int | None:
    """실패한 job의 ID 가져오기."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    try:
        response = httpx.get(url, headers=headers, params={"per_page": 100}, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        
        jobs = data.get("jobs", [])
        for job in jobs:
            if job.get("conclusion") == "failure":
                return job.get("id")
        
        # 실패한 job이 없으면 첫 번째 job 반환
        if jobs:
            return jobs[0].get("id")
        
        return None
    except Exception as e:
        logger.error(f"Error getting failed job ID: {e}")
        return None


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


def map_failure_reason(step_name: str | None, job_name: str | None) -> str:
    """Step name 또는 job name으로부터 failure_reason 매핑."""
    if not step_name and not job_name:
        return CIFailureReason.UNKNOWN
    
    search_text = (step_name or "").lower() + " " + (job_name or "").lower()
    
    if "ruff" in search_text:
        return CIFailureReason.RUFF_LINT
    elif "black" in search_text:
        return CIFailureReason.BLACK_FORMAT
    elif "alembic" in search_text or "migration" in search_text:
        return CIFailureReason.MIGRATION_FAILURE
    elif "pytest" in search_text or "test" in search_text:
        return CIFailureReason.TEST_FAILURE
    else:
        return CIFailureReason.UNKNOWN


def analyze_ci_failure(owner: str, repo: str, run_id: str, token: str) -> dict[str, Any]:
    """GitHub Jobs API를 사용하여 CI 실패 원인 분석."""
    # 실패한 job과 step 찾기
    failed_job, failed_step = get_failed_job_and_step(owner, repo, run_id, token)
    
    # failure_reason 매핑
    failure_reason = map_failure_reason(failed_step, failed_job)
    
    # 실패한 job ID 가져오기
    job_id = get_failed_job_id(owner, repo, run_id, token)
    
    # 로그 가져오기
    error_message = ""
    if job_id:
        error_message = get_job_logs(owner, repo, job_id, token)
    else:
        error_message = "could not fetch logs: job_id not found"
    
    # failed_step이 없으면 job name 사용
    if not failed_step:
        failed_step = failed_job or "unknown"
    
    # failed_job이 없으면 job name 사용
    if not failed_job:
        failed_job = "unknown"
    
    return {
        "failure_reason": failure_reason,
        "failed_step": failed_step,
        "failed_job": failed_job,
        "error_message": error_message[:2000] if error_message else "No specific error message found",
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
    run_id = os.getenv("TARGET_RUN_ID")
    run_url = os.getenv("TARGET_RUN_URL")
    target_sha = os.getenv("TARGET_SHA", "")
    target_branch = os.getenv("TARGET_BRANCH", "")
    github_token = get_github_token()

    if not run_id or not run_url:
        logger.error("TARGET_RUN_ID and TARGET_RUN_URL environment variables are required")
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
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Target SHA: {target_sha[:7] if target_sha else 'unknown'}")

    try:
        # URL 파싱
        owner, repo, _ = parse_run_url(run_url)

        # CI 실패 분석 (Jobs API 사용)
        logger.info("Analyzing CI failure using Jobs API...")
        analysis = analyze_ci_failure(owner, repo, run_id, github_token)
        failure_reason = analysis["failure_reason"]
        failed_step = analysis["failed_step"]
        failed_job = analysis["failed_job"]
        error_message = analysis["error_message"]

        logger.info(f"Failure reason: {failure_reason}")
        logger.info(f"Failed job: {failed_job}")
        logger.info(f"Failed step: {failed_step}")

        # 에러 메시지 스니펫 추출 (20-40줄)
        error_lines = error_message.split("\n")
        error_snippet = "\n".join(error_lines[-40:]) if len(error_lines) > 40 else error_message
        if len(error_snippet) > 2000:
            error_snippet = error_snippet[-2000:]

        # 자동 수정 가능 여부 확인
        if not can_auto_fix(failure_reason):
            logger.warning(f"Cannot auto-fix: {failure_reason}")
            # DECISION_REQUIRED 알림 (개선된 메시지)
            send(
                AlertLevel.DECISION_REQUIRED,
                "decisions",
                "CI Auto-Fix: Manual Intervention Required",
                {
                    "run_url": run_url,
                    "target_sha7": target_sha[:7] if target_sha else "unknown",
                    "target_branch": target_branch,
                    "failed_job": failed_job or "unknown",
                    "failed_step": failed_step or "unknown",
                    "failure_reason": failure_reason,
                    "error_snippet": error_snippet,
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
                    "target_sha7": target_sha[:7] if target_sha else "unknown",
                    "failed_job": failed_job or "unknown",
                    "failed_step": failed_step or "unknown",
                    "failure_reason": failure_reason,
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
                "run_url": run_url or "unknown",
                "target_sha7": target_sha[:7] if target_sha else "unknown",
                "retry_count": retry_count,
                "error": str(e),
            },
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

