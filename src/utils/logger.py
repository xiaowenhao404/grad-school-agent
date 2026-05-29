"""统一日志配置。使用 loguru。"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logger(level: str = "INFO", log_file: str | None = None) -> None:
    """初始化全局 logger。在 app.py 启动时调用一次。"""
    logger.remove()
    logger.add(sys.stderr, level=level, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(log_file, level=level, rotation="10 MB", encoding="utf-8")


def get_logger(name: str | None = None):
    return logger.bind(name=name) if name else logger
