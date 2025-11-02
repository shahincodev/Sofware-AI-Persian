"""لایهٔ ساده برای انتخاب مدل‌های LLM.

اینجا از lazy-loading استفاده می‌کنیم تا بارگذاری ماژول‌های سنگین تنها هنگام نیاز انجام شود.
همچنین امکان پیکربندی از طریق متغیرهای محیطی فراهم است.
"""

from __future__ import annotations

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AIBrain:
    """کلاس برای مدیریت و انتخاب مدل مناسب بر اساس منظور (purpose).

    روش کار: مدل‌ها هنگام نیاز ساخته می‌شوند تا زمان شروع برنامه سبک بماند.
    """

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}

    def _load_model(self, name: str) -> Any:
        """بارگذاری مدل با نام منطقی. این توابع importهای سنگین را محصور می‌کند."""
        try:
            if name == "reasoning":
                from browser_use.llm.google.chat import ChatGoogle

                model = ChatGoogle(model=os.getenv("GOOGLE_REASONING_MODEL", "gemini-2.5-flash"),
                                   temperature=float(os.getenv("MODEL_TEMPERATURE", "0.5")))
            elif name == "browser_use":
                from browser_use.llm.browser_use.chat import ChatBrowserUse

                model = ChatBrowserUse()
            elif name == "fast":
                from browser_use.llm.groq.chat import ChatGroq

                model = ChatGroq(model=os.getenv("GROQ_MODEL", "groq-1"),
                                  temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7")))
            else:
                from browser_use.llm.openai.chat import ChatOpenAI

                model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini"),
                                    temperature=float(os.getenv("MODEL_TEMPERATURE", "0")))
            logger.info("Loaded model: %s", name)
            return model
        except Exception as exc:
            logger.exception("Failed to load model %s: %s", name, exc)
            raise

    def get_model(self, purpose: str) -> Any:
        """انتخاب مدل بر اساس منظور (purpose).

        مقادیر ممکن برای purpose: 'analyze', 'browse', 'realtime', یا پیش‌فرض.
        """
        key = {
            "analyze": "reasoning",
            "browse": "browser_use",
            "realtime": "fast",
        }.get(purpose, "normal")

        if key not in self._models:
            self._models[key] = self._load_model(key)

        return self._models[key]