# SPDX-License-Identifier: NOASSERTION
# Copyright (c) 2025 Shahin

"""تنظیمات متمرکز لاگ‌گیری برای Sofware-AI

این ماژول تابع setup_logging() رو ارائه می‌کنه که یه handler برای نمایش لاگ‌ها تو کنسول
و یه handler چرخشی برای فایل (data/logs/app.log) تنظیم می‌کنه.
همچنین یه هوک استثنا نصب می‌کنه تا خطاهای گرفته‌نشده هم لاگ بشن.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


DEFAULT_LOG_FILE = Path("data") / "logs" / "app.log"


def ensure_logs_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def setup_logging(log_file: Optional[str] = None, level: Optional[int] = None) -> None:
    """تنظیم لاگر اصلی برنامه

    - RotatingFileHandler -> فایل data/logs/app.log (حداکثر ۵ مگابایت، ۵ فایل بک‌آپ)
    - StreamHandler -> نمایش لاگ‌ها توی کنسول (stdout)
    - سطح لاگ‌گیری از آرگومان level میاد، اگر نبود از متغیر محیطی LOG_LEVEL 
      و اگر اونم نبود، پیش‌فرض INFO می‌شه
    """
    log_path = Path(log_file) if log_file else DEFAULT_LOG_FILE
    ensure_logs_dir(log_path)

    env_level = os.getenv("LOG_LEVEL")
    if level is None:
        if env_level:
            try:
                level = int(env_level)
            except Exception:
                level_name = env_level.upper()
                level = getattr(logging, level_name, logging.INFO)
        else:
            level = logging.INFO

    root = logging.getLogger()
    # اطمینان از اینکه level یک سطح معتبر لاگ‌گیری باشه (عدد یا اسم رشته‌ای)
    lvl = level
    if not isinstance(lvl, int):
        try:
            lvl = int(lvl)  # type: ignore[arg-type]
        except Exception:
            lvl = getattr(logging, str(lvl).upper(), logging.INFO)
    root.setLevel(lvl)

    # حذف تمام handler های قبلی تا هنگام راه‌اندازی مجدد، لاگ‌ها دوبار ثبت نشن 
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s"
    )

    # کنترل کننده کنسول
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(lvl)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # گرداننده فایل چرخشی
    fh = logging.handlers.RotatingFileHandler(
        filename=str(log_path), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(lvl)
    fh.setFormatter(formatter)
    root.addHandler(fh)


def install_exception_hook() -> None:
    """برای ثبت استثنائات مدیریت نشده، sys.excepthook را نصب کنید."""

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # اجازه دهید KeyboardInterrupt عبور کند تا امکان خروج تمیز فراهم شود
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger().exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


__all__ = ["setup_logging", "install_exception_hook"]