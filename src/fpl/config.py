"""Load pipeline settings from config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    manager_id: int
    base_url: str
    user_agent: str
    request_delay: float
    timeout: float
    max_attempts: int
    raw_dir: Path
    marts_dir: Path
    warehouse: Path
    run_log: Path


def load_settings(path: Path | str = "config.toml") -> Settings:
    """Read config.toml. Relative paths inside it resolve against the file's own folder."""
    path = Path(path).resolve()
    with path.open("rb") as f:
        cfg = tomllib.load(f)

    root = path.parent
    api = cfg["api"]
    paths = cfg["paths"]
    return Settings(
        manager_id=int(cfg["manager"]["id"]),
        base_url=api["base_url"],
        user_agent=api["user_agent"],
        request_delay=float(api.get("request_delay_seconds", 0.5)),
        timeout=float(api.get("timeout_seconds", 30)),
        max_attempts=int(api.get("max_attempts", 5)),
        raw_dir=root / paths["raw_dir"],
        marts_dir=root / paths["marts_dir"],
        warehouse=root / paths["warehouse"],
        run_log=root / paths["run_log"],
    )
