# core/app_config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv
from dataclasses import dataclass
from pathlib import Path

load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    url: str


@dataclass(frozen=True)
class ScraperConfig:
    min_sleep_seconds: float
    max_sleep_seconds: float
    request_timeout_seconds: float
    ad_page_min_sleep_seconds: float
    ad_page_max_sleep_seconds: float


@dataclass(frozen=True)
class WorkerConfig:
    gemini_sleep_seconds: float
    archive_days_threshold: int


@dataclass(frozen=True)
class PathsConfig:
    logs_dir: Path
    worker_log_file: Path
    searches_dir: Path


@dataclass(frozen=True)
class StreamlitConfig:
    cache_ttl_seconds: int


@dataclass(frozen=True)
class AppConfig:
    db: DatabaseConfig
    scraper: ScraperConfig
    worker: WorkerConfig
    streamlit: StreamlitConfig
    paths: PathsConfig


def load_app_config() -> AppConfig:
    base_dir = Path(os.getenv("APP_BASE_DIR", ".")).resolve()
    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or "postgresql://lbc_user:lbc_password@localhost:5432/lbc_data"
    )

    scraper = ScraperConfig(
        min_sleep_seconds=float(os.getenv("SCRAPER_MIN_SLEEP", "2.5")),
        max_sleep_seconds=float(os.getenv("SCRAPER_MAX_SLEEP", "5.0")),
        request_timeout_seconds=float(os.getenv("SCRAPER_TIMEOUT", "10")),
        ad_page_min_sleep_seconds=float(
            os.getenv("SCRAPER_AD_MIN_SLEEP", "1.0")),
        ad_page_max_sleep_seconds=float(
            os.getenv("SCRAPER_AD_MAX_SLEEP", "2.0")),
    )

    worker = WorkerConfig(
        gemini_sleep_seconds=float(os.getenv("WORKER_GEMINI_SLEEP", "5")),
        archive_days_threshold=int(os.getenv("WORKER_ARCHIVE_DAYS", "3")),
    )

    streamlit = StreamlitConfig(
        cache_ttl_seconds=int(os.getenv("STREAMLIT_CACHE_TTL", "10")),
    )

    paths = PathsConfig(
        logs_dir=Path(os.getenv("LOGS_DIR", str(base_dir / "logs"))),
        worker_log_file=Path(
            os.getenv("WORKER_LOG_FILE", str(base_dir / "logs" / "worker.log"))),
        searches_dir=Path(
            os.getenv("SEARCHES_DIR", str(base_dir / "searches"))),
    )

    return AppConfig(
        db=DatabaseConfig(url=db_url),
        scraper=scraper,
        worker=worker,
        streamlit=streamlit,
        paths=paths,
    )
