import sqlite3
import pytest
from pathlib import Path

def test_db_seed_schema_and_counts():
    """Verify that the seeded SQLite database contains exact deterministic counts per Guide §8.1."""
    db_path = Path("techstore/data/techstore.db")
    if not db_path.exists():
        pytest.skip("TechStore database not initialized yet")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert {"users", "products", "coupons", "orders"}.issubset(tables)

    # 1. Users count: exactly 2 users (1 test user, 1 admin user)
    cursor.execute("SELECT count(*) FROM users")
    assert cursor.fetchone()[0] == 2

    # Verify credentials
    cursor.execute("SELECT email, role FROM users WHERE email='testuser@example.com'")
    user = cursor.fetchone()
    assert user is not None and user[1] == "user"

    cursor.execute("SELECT email, role FROM users WHERE email='admin@example.com'")
    admin = cursor.fetchone()
    assert admin is not None and admin[1] == "admin"

    # 2. Products count: exactly 10 products
    cursor.execute("SELECT count(*) FROM products")
    assert cursor.fetchone()[0] == 10

    # 3. Coupons count: at least SAVE20 coupon exists
    cursor.execute("SELECT code, discount_percent FROM coupons WHERE code='SAVE20'")
    coupon = cursor.fetchone()
    assert coupon is not None
    assert coupon[1] == 20

    conn.close()
