import aiosqlite
import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from bot.config import DATABASE_PATH
from bot.database.models import CREATE_TABLES_SQL

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def _get_connection(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        return conn

    async def init_db(self) -> None:
        async with await self._get_connection() as db:
            statements = [s.strip() for s in CREATE_TABLES_SQL.split(";") if s.strip()]
            for stmt in statements:
                try:
                    await db.execute(stmt)
                except Exception as e:
                    logger.warning(f"Error executing SQL: {e} | Statement: {stmt[:80]}")
            await db.commit()
        logger.info("Database initialized successfully")

    async def get_or_create_user(
        self, telegram_id: int, username: Optional[str], full_name: Optional[str]
    ) -> Dict[str, Any]:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE users SET last_active = CURRENT_TIMESTAMP, username = ?, full_name = ? WHERE telegram_id = ?",
                    (username, full_name, telegram_id),
                )
                await db.commit()
                return dict(row)
            await db.execute(
                "INSERT INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)",
                (telegram_id, username, full_name),
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
            return dict(row)

    async def update_user_language(self, telegram_id: int, language: str) -> None:
        async with await self._get_connection() as db:
            await db.execute(
                "UPDATE users SET language = ? WHERE telegram_id = ?",
                (language, telegram_id),
            )
            await db.commit()

    async def update_user_last_active(self, telegram_id: int) -> None:
        async with await self._get_connection() as db:
            await db.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?",
                (telegram_id,),
            )
            await db.commit()

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        async with await self._get_connection() as db:
            async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_active_users_count(self) -> int:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE is_banned = 0"
            ) as cursor:
                row = await cursor.fetchone()
            return row[0] if row else 0

    async def save_product(
        self,
        name: str,
        marketplace: str,
        url: Optional[str],
        image_url: Optional[str],
        price: float,
        currency: str = "UZS",
    ) -> int:
        async with await self._get_connection() as db:
            async with db.execute(
                """
                INSERT INTO products (name, marketplace, url, image_url, current_price, currency)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, marketplace, url, image_url, price, currency),
            ) as cursor:
                product_id = cursor.lastrowid
            await db.commit()
            await db.execute(
                "INSERT INTO price_history (product_id, price) VALUES (?, ?)",
                (product_id, price),
            )
            await db.commit()
        return product_id

    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_product_price(self, product_id: int, new_price: float) -> None:
        async with await self._get_connection() as db:
            await db.execute(
                "UPDATE products SET current_price = ?, last_checked = CURRENT_TIMESTAMP WHERE id = ?",
                (new_price, product_id),
            )
            await db.commit()

    async def save_price_history(self, product_id: int, price: float) -> None:
        async with await self._get_connection() as db:
            await db.execute(
                "INSERT INTO price_history (product_id, price) VALUES (?, ?)",
                (product_id, price),
            )
            await db.commit()

    async def get_price_history(
        self, product_id: int, days: int = 30
    ) -> List[Dict[str, Any]]:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        async with await self._get_connection() as db:
            async with db.execute(
                """
                SELECT price, recorded_at FROM price_history
                WHERE product_id = ? AND recorded_at >= ?
                ORDER BY recorded_at ASC
                """,
                (product_id, since),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def add_tracked_product(
        self,
        user_id: int,
        product_id: int,
        target_price: Optional[float] = None,
    ) -> bool:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT COUNT(*) FROM tracked_products WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
            count = row[0] if row else 0
            from bot.config import MAX_TRACKED_PRODUCTS
            if count >= MAX_TRACKED_PRODUCTS:
                return False
            async with db.execute(
                "SELECT id FROM tracked_products WHERE user_id = ? AND product_id = ? AND is_active = 1",
                (user_id, product_id),
            ) as cursor:
                existing = await cursor.fetchone()
            if existing:
                return True
            await db.execute(
                """
                INSERT INTO tracked_products (user_id, product_id, target_price, notify_any_drop)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, product_id, target_price, 1 if target_price is None else 0),
            )
            await db.commit()
        return True

    async def get_user_tracked_products(self, user_id: int) -> List[Dict[str, Any]]:
        async with await self._get_connection() as db:
            async with db.execute(
                """
                SELECT tp.id as tracking_id, tp.target_price, tp.notify_any_drop, tp.added_at,
                       p.id as product_id, p.name, p.marketplace, p.url, p.current_price, p.currency
                FROM tracked_products tp
                JOIN products p ON tp.product_id = p.id
                WHERE tp.user_id = ? AND tp.is_active = 1
                ORDER BY tp.added_at DESC
                """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def remove_tracked_product(self, tracking_id: int, user_id: int) -> bool:
        async with await self._get_connection() as db:
            await db.execute(
                "UPDATE tracked_products SET is_active = 0 WHERE id = ? AND user_id = ?",
                (tracking_id, user_id),
            )
            await db.commit()
        return True

    async def get_all_active_tracked(self) -> List[Dict[str, Any]]:
        async with await self._get_connection() as db:
            async with db.execute(
                """
                SELECT tp.id as tracking_id, tp.user_id, tp.target_price, tp.notify_any_drop,
                       p.id as product_id, p.name, p.marketplace, p.url, p.current_price, p.currency
                FROM tracked_products tp
                JOIN products p ON tp.product_id = p.id
                JOIN users u ON tp.user_id = u.telegram_id
                WHERE tp.is_active = 1 AND u.is_banned = 0
                """
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def add_to_wishlist(
        self, user_id: int, product_name: str, notes: Optional[str] = None
    ) -> bool:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT COUNT(*) FROM wishlist WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            count = row[0] if row else 0
            from bot.config import MAX_WISHLIST_ITEMS
            if count >= MAX_WISHLIST_ITEMS:
                return False
            await db.execute(
                "INSERT INTO wishlist (user_id, product_name, notes) VALUES (?, ?, ?)",
                (user_id, product_name, notes),
            )
            await db.commit()
        return True

    async def get_user_wishlist(self, user_id: int) -> List[Dict[str, Any]]:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT * FROM wishlist WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def remove_from_wishlist(self, wishlist_id: int, user_id: int) -> bool:
        async with await self._get_connection() as db:
            await db.execute(
                "DELETE FROM wishlist WHERE id = ? AND user_id = ?",
                (wishlist_id, user_id),
            )
            await db.commit()
        return True

    async def save_search(
        self, user_id: int, query: str, results_count: int = 0
    ) -> None:
        async with await self._get_connection() as db:
            await db.execute(
                "INSERT INTO search_history (user_id, query, results_count) VALUES (?, ?, ?)",
                (user_id, query, results_count),
            )
            await db.commit()

    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT COUNT(*) FROM search_history WHERE user_id = ?", (telegram_id,)
            ) as cursor:
                searches_row = await cursor.fetchone()
            async with db.execute(
                "SELECT COUNT(*) FROM tracked_products WHERE user_id = ? AND is_active = 1",
                (telegram_id,),
            ) as cursor:
                tracking_row = await cursor.fetchone()
            async with db.execute(
                "SELECT COUNT(*) FROM wishlist WHERE user_id = ?", (telegram_id,)
            ) as cursor:
                wishlist_row = await cursor.fetchone()
            async with db.execute(
                "SELECT created_at FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                user_row = await cursor.fetchone()
        return {
            "total_searches": searches_row[0] if searches_row else 0,
            "active_trackings": tracking_row[0] if tracking_row else 0,
            "wishlist_items": wishlist_row[0] if wishlist_row else 0,
            "member_since": user_row[0] if user_row else "N/A",
        }

    async def get_admin_stats(self) -> Dict[str, Any]:
        today = datetime.now().date().isoformat()
        async with await self._get_connection() as db:
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0") as cursor:
                users_row = await cursor.fetchone()
            async with db.execute(
                "SELECT COUNT(*) FROM tracked_products WHERE is_active = 1"
            ) as cursor:
                trackings_row = await cursor.fetchone()
            async with db.execute(
                "SELECT COUNT(*) FROM search_history WHERE DATE(searched_at) = ?", (today,)
            ) as cursor:
                searches_row = await cursor.fetchone()
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1") as cursor:
                banned_row = await cursor.fetchone()
        return {
            "total_users": users_row[0] if users_row else 0,
            "active_trackings": trackings_row[0] if trackings_row else 0,
            "today_searches": searches_row[0] if searches_row else 0,
            "banned_users": banned_row[0] if banned_row else 0,
        }

    async def ban_user(self, telegram_id: int) -> None:
        async with await self._get_connection() as db:
            await db.execute(
                "UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (telegram_id,)
            )
            await db.commit()

    async def unban_user(self, telegram_id: int) -> None:
        async with await self._get_connection() as db:
            await db.execute(
                "UPDATE users SET is_banned = 0 WHERE telegram_id = ?", (telegram_id,)
            )
            await db.commit()

    async def is_user_banned(self, telegram_id: int) -> bool:
        async with await self._get_connection() as db:
            async with db.execute(
                "SELECT is_banned FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
        return bool(row[0]) if row else False
