"""
CAYE v3.0 — Signal 6: GitHub API
DIMENSION: Hidden (35%)
Developer commit velocity ratio.
< 20% of baseline = abandonment_detected = True
Precedes hacks, rug pulls, and price collapse.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from statistics import mean
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class GitHubSignal:
    """
    Signal 6: GitHub REST API
    Monitors commit velocity for 6 blockchain repos.
    velocity_ratio < 0.20 = abandonment_detected = True
    """

    CACHE_NAMESPACE = "github_commits"
    BASE_URL = "https://api.github.com"
    MAX_RETRIES = 3
    ABANDONMENT_THRESHOLD = 0.20
    GITHUB_CACHE_RETRY_DELAY = 60  # seconds

    async def fetch_commit_data(
        self,
        db_session=None
    ) -> Dict[str, Any]:
        """
        Fetches commit activity for all monitored repos.
        Calculates velocity ratios.

        Returns:
            any_abandonment: bool
            abandonment_details: dict per repo
        """
        if not settings.github_token:
            logger.warning("GitHub: no token configured")
            return self._safe_default()

        # Check cache
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            return cached

        headers = {
            "Authorization": f"token {settings.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        repo_results = []

        for repo in settings.github_repos:
            result = await self._fetch_repo_commits(
                repo, headers
            )
            repo_results.append(result)

            # Store in DB
            if db_session and result.get("velocity_ratio") is not None:
                await self._store_snapshot(db_session, result)

            # Small delay between repos
            await asyncio.sleep(0.5)

        # Determine overall abandonment
        any_abandonment = any(
            r.get("abandonment_detected", False)
            for r in repo_results
        )

        abandonment_details = {
            r["repo"]: {
                "velocity_ratio": r.get("velocity_ratio"),
                "recent_avg": r.get("recent_avg"),
                "prior_avg": r.get("prior_avg"),
                "abandonment_detected": r.get(
                    "abandonment_detected", False
                )
            }
            for r in repo_results
        }

        result = {
            "any_abandonment": any_abandonment,
            "abandonment_details": abandonment_details,
            "repos_checked": len(repo_results),
            "repos_flagged": sum(
                1 for r in repo_results
                if r.get("abandonment_detected", False)
            )
        }

        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            result,
            settings.cache_ttl_github
        )

        if any_abandonment:
            flagged = [
                r["repo"] for r in repo_results
                if r.get("abandonment_detected", False)
            ]
            logger.warning(
                f"GitHub: ABANDONMENT DETECTED! "
                f"Flagged repos: {flagged}"
            )
        else:
            logger.info(
                f"GitHub: all {len(repo_results)} repos "
                f"at normal velocity"
            )

        return result

    async def _fetch_repo_commits(
        self,
        repo: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Fetches 52-week commit activity for one repo.
        Handles GitHub's cache delay (empty array response).
        """
        url = (
            f"{self.BASE_URL}/repos/{repo}"
            f"/stats/commit_activity"
        )

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=30.0
                ) as client:
                    response = await client.get(
                        url, headers=headers
                    )

                    # Rate limit check
                    if response.status_code == 403:
                        reset_time = response.headers.get(
                            "X-RateLimit-Reset"
                        )
                        logger.warning(
                            f"GitHub rate limited for {repo}"
                        )
                        return self._safe_repo_default(repo)

                    # GitHub returns 202 while computing
                    if response.status_code == 202:
                        logger.info(
                            f"GitHub computing stats for {repo} — "
                            f"retrying in {self.GITHUB_CACHE_RETRY_DELAY}s"
                        )
                        await asyncio.sleep(
                            self.GITHUB_CACHE_RETRY_DELAY
                        )
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Empty array = GitHub still computing
                    if not data or not isinstance(data, list):
                        if attempt < self.MAX_RETRIES - 1:
                            await asyncio.sleep(
                                self.GITHUB_CACHE_RETRY_DELAY
                            )
                            continue
                        return self._safe_repo_default(repo)

                    return self._calculate_velocity(repo, data)

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"GitHub {repo} HTTP {e.response.status_code} "
                    f"(attempt {attempt + 1})"
                )
            except Exception as e:
                logger.warning(
                    f"GitHub {repo} error: {e} "
                    f"(attempt {attempt + 1})"
                )

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.GITHUB_CACHE_RETRY_DELAY)

        return self._safe_repo_default(repo)

    def _calculate_velocity(
        self,
        repo: str,
        commit_activity: List[Dict]
    ) -> Dict[str, Any]:
        """
        Calculates commit velocity ratio.
        recent_4_weeks / prior_4_weeks
        ratio < 0.20 = abandonment
        """
        try:
            recent_4 = commit_activity[-4:]
            prior_4 = commit_activity[-8:-4]

            recent_avg = mean(
                [w.get("total", 0) for w in recent_4]
            )
            prior_avg = mean(
                [w.get("total", 0) for w in prior_4]
            )

            if prior_avg > 0:
                velocity_ratio = recent_avg / prior_avg
            else:
                # No prior activity = effectively abandoned
                velocity_ratio = 0.0

            abandonment_detected = (
                velocity_ratio < self.ABANDONMENT_THRESHOLD
            )

            return {
                "repo": repo,
                "recent_avg": round(recent_avg, 2),
                "prior_avg": round(prior_avg, 2),
                "velocity_ratio": round(velocity_ratio, 4),
                "abandonment_detected": abandonment_detected,
                "weeks_analyzed": len(commit_activity)
            }

        except Exception as e:
            logger.warning(
                f"GitHub velocity calc error for {repo}: {e}"
            )
            return self._safe_repo_default(repo)

    async def _store_snapshot(
        self,
        db_session,
        result: Dict[str, Any]
    ):
        """
        Stores GitHub commit snapshot to DB.
        """
        try:
            from backend.models import GitHubSnapshot
            snapshot = GitHubSnapshot(
                repo=result["repo"],
                recent_avg_commits=result.get("recent_avg"),
                prior_avg_commits=result.get("prior_avg"),
                velocity_ratio=result.get("velocity_ratio"),
                abandonment_detected=result.get(
                    "abandonment_detected", False
                )
            )
            db_session.add(snapshot)
            db_session.commit()
        except Exception as e:
            logger.warning(f"GitHub snapshot store error: {e}")
            db_session.rollback()

    def _safe_repo_default(self, repo: str) -> Dict[str, Any]:
        """
        Safe default for a single repo.
        CONSERVATIVE: abandonment_detected = False
        """
        return {
            "repo": repo,
            "recent_avg": None,
            "prior_avg": None,
            "velocity_ratio": None,
            "abandonment_detected": False
        }

    def _safe_default(self) -> Dict[str, Any]:
        """
        Safe default when GitHub unavailable.
        CONSERVATIVE: any_abandonment = False
        """
        return {
            "any_abandonment": False,
            "abandonment_details": {},
            "repos_checked": 0,
            "repos_flagged": 0
        }