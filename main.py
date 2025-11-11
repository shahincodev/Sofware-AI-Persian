#!/usr/bin/env python3
# SPDX-License-Identifier: NOASSERTION
# Copyright (c) 2025 TahaNili (Shahin)

"""
نقطه ورودی اصلی سیستم نرم‌افزاری هوش مصنوعی.
این ماژول یک رابط خط فرمان (CLI) برای تعامل با قابلیت‌های اصلی سیستم فراهم می‌کند.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional
from pyfiglet import Figlet
from colorama import init as colorama_init, Fore, Style


from core.agent_core import create_agent
from core.memory_system import MemoryManager
from core.task_engine import TaskEngine
from core.voice_io import VoiceManager
from dotenv import load_dotenv
from core.logging_config import setup_logging, install_exception_hook

colorama_init(autoreset=True) # در ویندوز، فعال کردن مدیریت ANSI
with open('banner.txt', 'r', encoding='utf-8') as file:
    banner = file.read()

# پیکربندی ثبت وقایع در هنگام راه‌اندازی اولیه تنظیم می‌شود (به `setup_logging` مراجعه کنید)
logger = logging.getLogger(__name__)

def setup_environment() -> None:
    """مقداردهی اولیه متغیرهای محیطی و ایجاد پوشه‌های مورد نیاز."""
    # بارگذاری متغیرهای محیطی از فایل .env
    load_dotenv()
    
    # اطمینان از وجود پوشه‌های مورد نیاز
    for dir_path in ["data/logs", "data/logs/cache"]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def parse_arguments() -> argparse.Namespace:
    """تجزیه و تحلیل آرگومان‌های خط فرمان."""
    parser = argparse.ArgumentParser(
        description="سیستم نرم‌افزاری هوش مصنوعی - پردازش هوشمند تسک‌ها",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--mode",
        choices=["browser", "code"],
        default="browser",
        help="حالت عملیات: 'browser' برای تعامل با وب، 'code' برای تحلیل کد"
    )
    
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="تعداد تسک‌های همزمان قابل اجرا (پیش‌فرض: 3)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="فعال‌سازی لاگ‌های دیباگ"
    )
    parser.add_argument(
        "--input-mode",
        choices=["text", "voice"],
        default="text",
        help="انتخاب نوع ورودی: 'text' برای کیبورد، 'voice' برای میکروفون"
    )
    parser.add_argument(
        "--tts-provider",
        choices=["google-cloud", "gtts"],
        default="gtts",
        help="انتخاب سرویس تبدیل متن به گفتار: 'google-cloud' (پولی، کیفیت بالا) یا 'gtts' (رایگان)"
    )

    return parser.parse_args()

def print_banner(text=banner, color=Fore.CYAN) -> None:
    """چاپ بنر خوش‌آمدگویی در CLI."""
    term_width = shutil.get_terminal_size((80, 20)).columns
    
    try:
        # اگر متن از قبل ASCII art است، مستقیماً آن را نمایش می‌دهیم
        lines = str(text).splitlines()
        for line in lines:
            # محاسبه فاصله لازم برای مرکز قرار دادن متن
            padding = (term_width - len(line)) // 2
            if padding > 0:
                print(color + " " * padding + line + Style.RESET_ALL)
            else:
                print(color + line + Style.RESET_ALL)
    except Exception as e:
        logger.error(f"Khata dar Namayeshe Banner: {str(e)}")
        print(color + str(text) + Style.RESET_ALL)

async def process_user_input(task_engine: TaskEngine, memory: MemoryManager, mode: str, input_mode: str, voice: VoiceManager) -> None:
    """پردازش ورودی کاربر در یک حلقه تعاملی."""

    print_banner(banner, color=Fore.CYAN)
    # خوش‌آمدگویی صوتی اگر حالت voice انتخاب شده باشد
    if input_mode == "voice":
        voice.speak("سلام! به سامانه هوش مصنوعی خوش آمدید.", block=True)
    print("\n Be Systeme Narm Afzarie Hooshe Masnoee Sofware-AI Khosh Amadid !")
    print("Task haaye khod ra vared konid (har task dar yek khat). Baraye khorooj az Ctrl+C estefade konid.\n")

    try:
        # حلقه بیرونی: امکان چندین دور اضافه کردن + اجرای وظایف را فراهم می‌کند
        while True:
            # حلقه داخلی: یک یا چند وظیفه را از کاربر دریافت می‌کند
            while True:
                try:

                    if input_mode == "voice":
                        user_input = voice.listen(timeout=7)
                        if not user_input:
                            print("ورودی صوتی دریافت نشد، لطفاً دوباره تلاش کنید.")
                            continue
                    else:
                        user_input = input("Taske Jadid > ").strip()
                        if not user_input:
                            continue

                    # ذخیره تسک در حافظه کوتاه‌مدت
                    memory.remember_short(
                        content=user_input,
                        ttl=3600,  # 1 ساعت TTL
                        metadata={"type": "user_task", "mode": mode}
                    )

                    # افزودن تسک به موتور پردازش
                    task_engine.add_task(user_input, mode=mode)
                    print(f"Task ezafe shod: {user_input}")

                    # پرسش برای افزودن تسک بیشتر یا شروع اجرا

                    if input_mode == "voice":
                        voice.speak("آیا تسک دیگری دارید؟ برای افزودن تسک جدید بگویید بله یا برای ادامه سکوت کنید.")
                        choice = voice.listen(timeout=5)
                        if choice and ("بله" in choice or "yes" in choice.lower()):
                            continue
                        else:
                            break
                    else:
                        choice = input("\n Aya task digari darid? (y/N) ").strip().lower()
                        if choice == 'y':
                            continue
                        else:
                            break

                except EOFError:
                    break

            # اگر در این دور هیچ وظیفه‌ای اضافه نشده است، بپرسید که آیا ادامه دهید یا خارج شوید

            if not task_engine.queue:
                if input_mode == "voice":
                    voice.speak("هیچ تسکی اضافه نشده است. آیا می‌خواهید ادامه دهید؟ اگر نه بگویید نه.")
                    cont = voice.listen(timeout=5)
                    if cont and ("نه" in cont or "no" in cont.lower()):
                        break
                    else:
                        continue
                else:
                    cont = input("\n Hich taski ezafe nashode ast. Aya mikhahid edame dahid? (Y/n) ").strip().lower()
                    if cont == 'n':
                        break
                    else:
                        continue

            # اجرای تمام تسک‌های جمع‌آوری شده
            print("\n Dar hal ejraaye task-ha...")

            # وظایف را قبل از اجرا عکس‌برداری می‌کند، زیرا run_all صف را پاک نمی‌کند
            tasks_list = list(task_engine.queue)
            results = await task_engine.run_all()

            # ذخیره نتایج در حافظه بلندمدت
            for (task_text, task_mode), result in zip(tasks_list, results):
                if result:
                    memory.remember_long(
                        content=result,
                        metadata={
                            "type": "task_result",
                            "original_task": task_text,
                            "mode": task_mode
                        }
                    )
                    print(f"\nNatiije task: {result}\n")
                else:
                    print(f"\nTask ba shekast movajeh shod ya natije-i nadasht\n")

            # صف موتور را خالی کنید تا دور بعدی از نو شروع شود
            task_engine.queue.clear()

            # بپرسید که آیا کاربر می‌خواهد وظایف بیشتری اضافه کند یا اجرا کند

            if input_mode == "voice":
                voice.speak("آیا می‌خواهید تسک‌های بیشتری اضافه کنید یا اجرا کنید؟ اگر نه بگویید نه.")
                cont = voice.listen(timeout=5)
                if cont and ("نه" in cont or "no" in cont.lower()):
                    break
                else:
                    continue
            else:
                cont = input("\n Aya mikhahid task haye bishtari ezafe konid ya anjam dahid? (Y/n) ").strip().lower()
                if cont == 'n':
                    break
                else:
                    continue

    except KeyboardInterrupt:
        print("\nDar hal khamosh shodan narm-afzar...")
    finally:
        memory.shutdown()
        voice.shutdown()

async def main() -> None:
    """نقطه ورود اصلی برنامه."""
    try:
        # تجزیه آرگومان‌های خط فرمان
        args = parse_arguments()

        # راه‌اندازی محیط
        setup_environment()

        # مقداردهی اولیه گزارش‌گیری پس از آماده‌سازی محیط. با توجه به پرچم --debug
        setup_logging(level=logging.DEBUG if args.debug else None)
        install_exception_hook()

        # راه‌اندازی اجزای اصلی
        task_engine = TaskEngine(concurrency=args.concurrency)
        memory = MemoryManager()
        voice = VoiceManager(tts_provider=args.tts_provider)

        # پردازش ورودی کاربر و اجرای تسک‌ها
        await process_user_input(task_engine, memory, args.mode, args.input_mode, voice)

    except Exception as e:
        logger.exception("Khataaye mohalek rokh daad")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())