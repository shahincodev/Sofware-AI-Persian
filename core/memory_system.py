"""
ماژول سیستم حافظه: پشتیبانی از حافظهٔ کوتاه‌مدت (درون‌فرایندی با TTL)
و حافظهٔ بلندمدت (پایدار با sqlite). این پیاده‌سازی مینیمال، ایمن
و قابل ایمپورت است و با معماری MVP سازگار می‌ماند.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple

@dataclass
class MemoryItem:
    id: str
    content: str
    metadata: Dict[str, Any]
    created_at: float
    expires_at: Optional[float] = None

class ShortTermMemory:
    """حافظهٔ کوتاه‌مدت: ذخیره در حافظهٔ RAM با زمان انقضا (TTL).

    رفتار:
    - افزودن با ttl (ثانیه) یا بدون ttl (موقتی تا پاکسازی دستی)
    - بازیابی و جستجو ساده بر اساس متن
    - پاکسازی خودکار موارد منقضی
    """

    def __init__(self) -> None:
        self._store: Dict[str, MemoryItem] = {}
        self._lock = Lock()

    def add(self, content: str, ttl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        """افزودن یک آیتم به حافظهٔ کوتاه‌مدت. بازگشت MemoryItem ساخته‌شده."""
        if metadata is None: 
            metadata= {}
        item_id = str(uuid.uuid4())
        now = time.time()
        expires_at = now + ttl if ttl is not None else None
        item = MemoryItem(id=item_id, content=content, metadata=metadata, created_at=now, expires_at=expires_at)
        with self._lock:
            self._store[item_id] = item
        return item
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
         """دریافت آیتم بر اساس شناسه. اگر منقضی شده باشد None بازمی‌گردد."""
         with self._lock:
             item = self._store.get(item_id)
             if item is None: 
                 return None
             if item.expires_at is not None and time.time() > item.expires_at:
                # منقضی شده است؛ حذف و None برگردان
                del self._store[item_id]
                return None
                return item
             
    def query(self, keyword: str, limit: int = 10) -> List[MemoryItem]:
        """جستجوی ساده بر اساس دربرداشتن keyword در content یا metadata (رشته‌ها)."""
        keyword_lover = keyword.lower()
        matches: List[MemoryItem] = []
        with self._lock:
            # پاکسازی موارد منقضی قبل از جستجو
            self._cleanup_locked()
            for item in self._store.values():
                if (keyword_lover in item.content.lower() or
                    any(keyword_lover in str(v).lower() for v in item.metadata.values())):
                    matches.append(item)
                    if len(matches) >= limit:
                        break

                else: 
                    # جستجو در متادیتا به صورت رشته
                    meta_str = json.dumps(item.metadata, ensure_ascii=False).lower()
                    if keyword_lover in meta_str:
                        matches.append(item)
                        if len(matches) >= limit:
                            break

        return matches
    def all_items(self) -> List[MemoryItem]:
        """بازگرداندن تمام آیتم‌های غیرمنقضی در حافظه."""
        with self._lock:
            self._cleanup_locked()
            return list(self._store.values())
        
    def _cleanup_locked(self) -> None:
        """حذف موارد منقضی شده؛ فرض می‌شود lock از قبل گرفته شده باشد."""
        now = time.time()
        to_delete = [item_id for item_id, item in self._store.items()
                     if item.expires_at is not None and now > item.expires_at]
        for item_id in to_delete:
            del self._store[item_id]

    def cleanup(self) -> None:
        """پاکسازی ایمن موارد منقضی‌شده."""
        with self._lock:
            self._cleanup_locked()

    def pop_oldest(self) -> Optional[MemoryItem]:
        """برداشتن قدیمی‌ترین آیتم (برای مهاجرت به حافظهٔ بلندمدت)."""
        with self._lock:
            if not self._store:
                return None
            oldest_item = min(self._store.values(), key=lambda item: item.created_at)
            del self._store[oldest_item.id]
            return oldest_item
        
class LongTermMemory:
    """حافظهٔ بلندمدت: ذخیره‌سازی پایدار با SQLite.

    رفتار:
    - افزودن، بازیابی و جستجو بر اساس متن
    - ذخیره‌سازی ایمن با استفاده از پارامترهای SQL برای جلوگیری از تزریق
    """

    """حافظهٔ بلندمدت: ذخیرهٔ پایدار در SQLite.

    طراحی مینیمال:
    - جدول memories(id TEXT PRIMARY KEY, content TEXT, metadata TEXT, created_at REAL)
    - جستجوی ساده با LIKE برای متن؛ در آینده می‌توان embedding/FAISS افزود.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = str(Path("./data").resolve() / "memories.sqlite3")
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._lock = Lock()
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """ایجاد جدول حافظه در صورت عدم وجود."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at REAL NOT NULL
                )
            """)
            self._conn.commit()

    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        """افزودن یک آیتم به حافظهٔ بلندمدت و برگرداندن MemoryItem آن."""
        if metadata is None:
            metadata = {}
        item_id = str(uuid.uuid4())
        now = time.time()
        meta_json = json.dumps(metadata, ensure_ascii=False)
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO memories (id, content, metadata, created_at)
                VALUES (?, ?, ?, ?)
            """, (item_id, content, meta_json, now))
            self._conn.commit()

        return MemoryItem(id=item_id, content=content, metadata=metadata, created_at=now)
    def get(self, item_id: str) -> Optional[MemoryItem]:
        """دریافت آیتم بر اساس شناسه از پایگاه داده."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT id, content, metadata, created_at FROM memories WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            meta_dict = json.loads(row[2]) if row[2] else {}
            return MemoryItem(id=row[0], content=row[1], metadata=meta_dict, created_at=row[3])
        
    def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """جستجوی ساده بر اساس LIKE روی ستون content و metadata."""
        like_q = f"%{query}%"
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT id, content, metadata, created_at FROM memories
                WHERE content LIKE ? OR metadata LIKE ?
                LIMIT ?
            """, (like_q, like_q, limit))
            rows = cursor.fetchall()
            results: List[MemoryItem] = []
            for row in rows:
                meta_dict = json.loads(row[2]) if row[2] else {}
                results.append(MemoryItem(id=row[0], content=row[1], metadata=meta_dict, created_at=row[3]))
            return results
    def delete(self, item_id: str) -> bool: 
        """حذف آیتم بر اساس شناسه. بازگشت True اگر آیتم حذف شده باشد."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (item_id,))
            self._conn.commit()
            return cursor.rowcount > 0
        
    def all(self, limit: int = 100) -> List[MemoryItem]:
        """دریافت مجموعه‌ای از آیتم‌ها (جدیدترین‌ها ابتدا)."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT id, content, metadata, created_at FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results: List[MemoryItem] = []
            for row in rows:
                meta_dict = json.loads(row[2]) if row[2] else {}
                results.append(MemoryItem(id=row[0], content=row[1], metadata=meta_dict, created_at=row[3]))
            return results
        
    def close(self) -> None:
        """بستن اتصال پایگاه داده."""
        with self._lock:
            try:
                self._conn.commit()
            finally: 
                self._conn.close()


class MemoryManager:
    """مدیریت یکپارچهٔ حافظه: ترکیب short-term و long-term با سیاست سادهٔ همگرایی.

    قابلیت‌ها:
    - افزودن به short-term با ttl و سپس انتقال خودکار موارد قدیمی/بزرگ به long-term
    - افزودن مستقیم به long-term
    - جستجوی متحد (اول short-term سپس long-term)
    - متدهای کمک برای پاکسازی و شاتر داون
    """

    def __init__(self, *, lt_db_path: Optional[str] = None, consolidation_threshold: int = 50) -> None:
        # consolidation_threshold: اگر تعداد آیتم‌های short-term بیشتر از این شد، آیتم‌های قدیمی منتقل شوند
        self.short = ShortTermMemory()
        self.long = LongTermMemory(db_path=lt_db_path)
        self._consolidation_threshold = max(1, int(consolidation_threshold))
        self._lock = Lock()

    def remember_short(self, content: str, ttl: Optional[float] = 60.0, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        """ذخیرهٔ سریع در حافظهٔ کوتاه‌مدت. به‌صورت خودکار ممکن است به حافظهٔ بلندمدت منتقل شود."""
        item = self.short.add(content, ttl=ttl, metadata=metadata)
        # سیاست سادهٔ همگرایی: اگر تعداد بیش از حد شد، قدیمی‌ترین‌ها را به long-term منتقل کن
        self._maybe_consolidate()
        return item
    
    def remember_long(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        """ذخیرهٔ دائمی در حافظهٔ بلندمدت."""
        return self.long.add(content, metadata=metadata)
    def recall(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """جستجوی متحد: ابتدا در short-term سپس در long-term."""
        results: List[MemoryItem] = []
        # جستجو در short-term
        results.extend(self.short.query(query, limit=limit))
        if len(results) < limit:
            # کمبود نتایج: جستجو در long-term
            remaining = limit - len(results)
            results.extend(self.long.search(query, limit=remaining))
        return results

    def forget_long(self, item_id: str) -> bool:
        """حذف آیتم از حافظهٔ بلندمدت بر اساس شناسه. بازگشت True اگر حذف شده باشد."""
        return self.long.delete(item_id)
    
    def _maybe_consolidate(self) -> None:
        """در صورت نیاز، یک یا چند آیتم از short-term را به long-term منتقل می‌کند."""
        with self._lock: 
            items = self.short.all_items()
            if len(items) > self._consolidation_threshold:
                return
            # منتقل کردن تا رسیدن به آستانه (حذف قدیمی‌ترین‌ها)
            to_move_count = len(items) - self._consolidation_threshold
            for _ in range(to_move_count):
                old = self.short.pop_oldest()
                if old is None:
                    continue
                self.long.add(content=old.content, metadata=old.metadata)

    def shutdown(self) -> None:
        """شاتر داون ایمن حافظهٔ بلندمدت."""
        self.short.cleanup()
        self.long.close()
