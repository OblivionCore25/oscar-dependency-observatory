"""
OSCAR — Unified Enrichment Service

Orchestrates deps.dev, OpenSSF Scorecard, and download stats clients
into a single enrichment call. All results are optional — enrichment
is additive and never blocks the primary API response.

Usage:
    service = EnrichmentService()
    data = await service.enrich_package("npm", "express", "5.1.0")
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from app.enrichment.deps_dev_client import DepsDevClient
from app.enrichment.scorecard_client import ScorecardClient
from app.enrichment.download_stats_client import DownloadStatsClient

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentData:
    """Unified enrichment result combining all external sources."""

    # deps.dev — dependent counts (true ecosystem-wide fan-in)
    global_fan_in: Optional[int] = None
    global_direct_dependents: Optional[int] = None
    global_indirect_dependents: Optional[int] = None

    # deps.dev — package metadata
    source_repo_url: Optional[str] = None
    licenses: list[str] = field(default_factory=list)
    published_at: Optional[str] = None
    is_deprecated: bool = False

    # OpenSSF Scorecard
    scorecard_score: Optional[float] = None
    scorecard_checks: Optional[dict[str, int]] = None

    # Download popularity
    monthly_downloads: Optional[int] = None

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary, omitting None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


# Singleton instances so caches persist across requests within the process
_deps_dev_client: Optional[DepsDevClient] = None
_scorecard_client: Optional[ScorecardClient] = None
_download_stats_client: Optional[DownloadStatsClient] = None


def _get_deps_dev() -> DepsDevClient:
    global _deps_dev_client
    if _deps_dev_client is None:
        _deps_dev_client = DepsDevClient()
    return _deps_dev_client


def _get_scorecard() -> ScorecardClient:
    global _scorecard_client
    if _scorecard_client is None:
        _scorecard_client = ScorecardClient()
    return _scorecard_client


def _get_download_stats() -> DownloadStatsClient:
    global _download_stats_client
    if _download_stats_client is None:
        _download_stats_client = DownloadStatsClient()
    return _download_stats_client


class EnrichmentService:
    """
    Orchestrates all three external data sources into a single enrichment call.
    
    The call chain is:
      1. deps.dev → dependent counts + package info (source repo URL)
      2. Source repo URL → OpenSSF Scorecard
      3. Registry → download count
      
    All three are called concurrently via asyncio. Any failure is swallowed
    and the corresponding fields are left as None.
    """

    def __init__(self):
        self.deps_dev = _get_deps_dev()
        self.scorecard = _get_scorecard()
        self.downloads = _get_download_stats()

    async def enrich_package(
        self, ecosystem: str, package_name: str, version: str
    ) -> EnrichmentData:
        """
        Enrich a single package with data from all external sources.
        Returns an EnrichmentData with whatever data was successfully retrieved.
        """
        result = EnrichmentData()

        # Step 1: deps.dev — dependents + package info (parallel)
        import asyncio

        dependents_task = asyncio.create_task(
            self.deps_dev.get_dependents(ecosystem, package_name, version)
        )
        info_task = asyncio.create_task(
            self.deps_dev.get_package_info(ecosystem, package_name, version)
        )
        downloads_task = asyncio.create_task(
            self.downloads.get_downloads(ecosystem, package_name)
        )

        dependents, info, downloads = await asyncio.gather(
            dependents_task, info_task, downloads_task,
            return_exceptions=True
        )

        # Process dependents
        if dependents and not isinstance(dependents, Exception):
            result.global_fan_in = dependents.total
            result.global_direct_dependents = dependents.direct
            result.global_indirect_dependents = dependents.indirect

        # Process package info
        source_repo_url = None
        if info and not isinstance(info, Exception):
            result.source_repo_url = info.source_repo_url
            result.licenses = info.licenses
            result.published_at = info.published_at
            result.is_deprecated = info.is_deprecated
            source_repo_url = info.source_repo_url

        # Process downloads
        if downloads and not isinstance(downloads, Exception):
            result.monthly_downloads = downloads

        # Step 2: OpenSSF Scorecard (requires repo URL from step 1)
        if source_repo_url:
            try:
                scorecard = await self.scorecard.get_scorecard(source_repo_url)
                if scorecard:
                    result.scorecard_score = scorecard.score
                    result.scorecard_checks = scorecard.checks
            except Exception as e:
                logger.warning(f"Scorecard enrichment failed: {e}")

        return result
