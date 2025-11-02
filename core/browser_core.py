"""ابزار کمکی برای ایجاد یک شیء Browser با تنظیمات پیش‌فرض قابل تنظیم.

اینجا می‌توانیم تنظیمات مرتبط با مرورگر را از متغیرهای محیطی بخوانیم تا
پیکربندی در محیط‌های مختلف ساده باشد.
"""

from __future__ import annotations

import os
from typing import Any
from browser_use import Browser


def create_browser(*, headless: bool | None = None, window_size: dict | None = None) -> Browser:
    """یک نمونهٔ Browser با تنظیمات منطقی برمی‌گرداند.

    پارامترها:
    - headless: اگر None باشد مقدار از متغیر محیطی BROWSER_HEADLESS خوانده می‌شود
    - window_size: دیکشنری {'width': ..., 'height': ...}
    """
    if headless is None:
        # مقدار پیش‌فرض از متغیر محیطی خوانده می‌شود ("1" یا "true" به معنی headless)
        env_val = os.getenv("BROWSER_HEADLESS", "1").lower()
        headless = env_val not in ("0", "false", "no")

    if window_size is None:
        window_size = {"width": 1280, "height": 720}

    # برگرداندن instance مرورگر با تنظیمات مشخص
    return Browser(
        headless=headless,
        keep_alive=True,
        window_size=window_size,
    )