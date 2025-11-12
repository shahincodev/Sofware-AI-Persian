# SPDX-License-Identifier: NOASSERTION
# Copyright (c) 2025 Shahin

"""Engine ساده برای صف‌بندی و اجرای همزمان تسک‌ها.

این ماژول مدیریت اجرای موازی چند Agent را به عهده دارد. هدف: خط‌مشی ساده، مدیریت خطا و محدودیت همزمانی.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, List, Optional, Tuple

from .agent_core import create_agent

logger = logging.getLogger(__name__)


class TaskEngine:
    """مدیریت صفِ تسک‌ها و اجرای آن‌ها به‌صورت همزمان با محدودیت قابل تنظیم.

    پارامترها:
    - concurrency: تعداد همزمانی (کوانتوم اجرا)؛ پیش‌فرض 3
    """

    def __init__(self, *, concurrency: int = 3) -> None:
        self.queue: List[Tuple[str, str]] = []
        self._concurrency = max(1, int(concurrency))

    def add_task(self, task: str, mode: str = "browser") -> None:
        """یک تسک جدید به صف اضافه می‌کند.

        task: متن تسک برای Agent
        mode: 'browser' یا 'code'
        """
        self.queue.append((task, mode))

    async def run_all(self) -> List[Optional[str]]:
        """تمام تسک‌ها را اجرا می‌کند و لیستی از نتایج (یا None در صورت خطا) بازمی‌گرداند."""

        # Semaphore برای محدود کردن تعداد همزمان اجراها
        sem = asyncio.Semaphore(self._concurrency)

        async def _wrapped_run(task: str, mode: str) -> Optional[str]:
            async with sem:
                return await self.run_task(task, mode)

        coros = [_wrapped_run(t, m) for t, m in self.queue]
        # return_exceptions=False -> در صورت استثنا آن را دریافت و هندل می‌کنیم
        results = await asyncio.gather(*coros)
        return results

    async def run_task(self, task: str, mode: str) -> Optional[str]:
        """اجرای یک تسک واحد و بازگرداندن نتیجهٔ نهایی (یا None در صورت خطا).

        این تابع استثناها را هندل می‌کند و لاگ‌ می‌زند.
        """
        logger.info("🚀 Running: %s", task)
        agent = create_agent(task, mode)
        try:
            history: Any = await agent.run()
            # بعضی Agentها ممکن است نوعی تاریخچه متفاوت بازگردانند؛ تلاش می‌کنیم
            # ابتدا به متد final_result دسترسی پیدا کنیم و در صورت نبود آن، نمایشی از history را بازگردانیم.
            try:
                result = history.final_result()
            except Exception:
                result = str(history)

            logger.info("✅ Anham-Shod: %s", task)
            return result
        except Exception as exc:
            logger.exception("❌ Shekast-Khord: %s", task)
            return None