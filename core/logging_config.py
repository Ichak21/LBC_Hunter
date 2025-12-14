import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from core.app_config import load_app_config
import sys


def setup_logging(log_path: str | None = None, level: int = logging.INFO) -> None:
    cfg = load_app_config()
    if log_path is None:
        log_path = str(cfg.paths.worker_log_file)

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5_000_000,   # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.name = "lbc_file_handler"  # tag utile

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.name = "lbc_console_handler"

    root = logging.getLogger()
    root.setLevel(level)

    # ✅ Idempotent: retire uniquement NOS handlers (évite de casser Streamlit)
    root.handlers = [h for h in root.handlers if getattr(
        h, "name", "") not in {"lbc_file_handler", "lbc_console_handler"}]

    root.addHandler(file_handler)
    root.addHandler(console_handler)
