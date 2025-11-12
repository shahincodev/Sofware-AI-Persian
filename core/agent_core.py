# SPDX-License-Identifier: NOASSERTION
# Copyright (c) 2025 Shahin

"""Factory برای ساخت Agent یا CodeAgent با تنظیمات امن‌تر.

تغییرات کلیدی:
- بارگذاری مدل از طریق AIBrain
- حذف مقادیر حساس هاردکد شده؛ مقدار session key از متغیر محیطی خوانده می‌شود
- مسیرهای فایل به صورت قابل پیکربندی و امن قرار می‌گیرند
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from browser_use import Agent, CodeAgent
from .ai_brain import AIBrain
from .browser_core import create_browser


def create_agent(task: str, mode: str = "browser") -> Agent | CodeAgent:
    """یک Agent یا CodeAgent را بر اساس حالت (mode) می‌سازد.

    پارامترها:
    - task: متن کار برای عامل
    - mode: 'browser' یا 'code'
    """

    ai_brain = AIBrain()
    # تعیین مدل بر اساس نوع agent
    llm = ai_brain.get_model("browse" if mode == "browser" else "analyze")

    browser = create_browser() if mode == "browser" else None

    agent_class = CodeAgent if mode == "code" else Agent

    # مقدار session key را از متغیر محیطی بخوانید؛ اگر تنظیم نشده، از None استفاده می‌شود
    session_key = os.getenv("SESSION_KEY")

    # مسیرهای مجاز برای agent (در صورت نیاز، می‌توانید تنظیمات را از فایل یا env بخوانید)
    available_paths = [str(Path("./data").resolve())]

    # اگر agent_class یک ماژول است (مثلاً به‌خاطر import اشتباه)، تلاش کنیم کلاس مناسب را از درون ماژول استخراج کنیم
    if not callable(agent_class):
        module = agent_class
        cls = None
        # اولویت به اسامی شناخته‌شده بدهیم
        for name in ("CodeAgent", "Agent"):
            cls = getattr(module, name, None)
            if cls and callable(cls):
                agent_class = cls
                break
        # اگر هنوز پیدا نشده، اولین نوع تعریف‌شده در ماژول را بردار
        if not callable(agent_class):
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type):
                    agent_class = obj
                    break
        if not callable(agent_class):
            raise TypeError(f"agent_class ({module!r}) is not callable and no suitable class was found in the module")

    agent = agent_class(
        task=task,
        llm=llm,
        browser=browser,
        max_steps=20,
        use_vision=False,
        flash_mode=(mode == "fast"),
        sensitive_data={"session_key": session_key} if session_key else None,
        available_file_paths=available_paths,
    )

    return agent