"""
OSCAR — OpenSSF Scorecard Client

Wraps the OpenSSF Scorecard REST API for security health scoring.
API: https://api.scorecard.dev/projects/{repo_url}

The Scorecard evaluates GitHub repositories (not package names directly).
OSCAR chains: package → deps.dev → source_repo_url → Scorecard.
"""

import logging
from typing import Optional

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

SCORECARD_BASE = "https://api.scorecard.dev"


class ScorecardData:
    """Parsed OpenSSF Scorecard result."""

    def __init__(
        self,
        score: float,
        checks: dict[str, int],
        repo_url: str,
    ):
        self.score = score
        self.checks = checks  # e.g. {"Maintained": 10, "Code-Review": 10, ...}
        self.repo_url = repo_url

    def __repr__(self) -> str:
        return f"ScorecardData(score={self.score}, checks={len(self.checks)})"


class ScorecardClient:
    """
    Async HTTP client for the OpenSSF Scorecard API.
    Results are TTL-cached for 6 hours (Scorecard runs weekly scans).
    """

    def __init__(self, cache_ttl: int = 21600, cache_maxsize: int = 500):
        self._cache: TTLCache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self._timeout = httpx.Timeout(15.0, connect=5.0)

    async def get_scorecard(self, repo_url: str) -> Optional[ScorecardData]:
        """
        Fetch Scorecard data for a GitHub repository.

        Args:
            repo_url: GitHub repo URL, e.g. "https://github.com/expressjs/express"
                      or "github.com/expressjs/express"

        Returns:
            ScorecardData or None on failure.
        """
        if not repo_url:
            return None

        # Normalize URL: strip protocol prefix for the API path
        normalized = repo_url
        for prefix in ("https://", "http://"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break

        # Strip trailing slash
        normalized = normalized.rstrip("/")

        cache_key = normalized
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{SCORECARD_BASE}/projects/{normalized}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                score = data.get("score", 0.0)
                checks = {}
                for check in data.get("checks", []):
                    name = check.get("name", "")
                    check_score = check.get("score", -1)
                    if name and check_score >= 0:
                        checks[name] = check_score

                result = ScorecardData(
                    score=score,
                    checks=checks,
                    repo_url=repo_url,
                )
                self._cache[cache_key] = result
                return result

        except Exception as e:
            logger.warning(f"Scorecard call failed for {repo_url}: {e}")
            return None
