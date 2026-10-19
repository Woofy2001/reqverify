import hashlib
import json
import sqlite3
import pytest

class SpikeSQLiteCache:
    """Minimal SQLite cache implementing Guide §6.3 keying with run_id."""
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS calls("
            "key TEXT PRIMARY KEY, created REAL, run_id TEXT, "
            "request TEXT, response TEXT, meta TEXT)"
        )

    def compute_key(self, model: str, system: str, user: str, schema: dict, run_id: str) -> str:
        payload = json.dumps(
            {"model": model, "system": system, "user": user,
             "schema": schema, "run_id": run_id},
            sort_keys=True
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT response, meta FROM calls WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return {"response": json.loads(row[0]), "meta": json.loads(row[1])}
        return None

    def put(self, key: str, run_id: str, request: dict, response: dict, meta: dict):
        self.conn.execute(
            "INSERT OR REPLACE INTO calls VALUES (?, 1.0, ?, ?, ?, ?)",
            (key, run_id, json.dumps(request), json.dumps(response), json.dumps(meta))
        )
        self.conn.commit()

def test_spike_s5_cache_hit_same_run_id():
    cache = SpikeSQLiteCache()
    schema = {"type": "object", "properties": {"status": {"type": "string"}}}
    
    key1 = cache.compute_key("claude-sonnet-5-5", "sys", "user prompt", schema, "run-alpha")
    cache.put(key1, "run-alpha", {"prompt": "user prompt"}, {"result": "PASS"}, {"tokens": 150})
    
    hit = cache.get(key1)
    assert hit is not None
    assert hit["response"]["result"] == "PASS"

def test_spike_s5_cache_miss_distinct_run_id():
    cache = SpikeSQLiteCache()
    schema = {"type": "object", "properties": {"status": {"type": "string"}}}
    
    key_run1 = cache.compute_key("claude-sonnet-5-5", "sys", "user prompt", schema, "run-replicate-1")
    key_run2 = cache.compute_key("claude-sonnet-5-5", "sys", "user prompt", schema, "run-replicate-2")
    
    # Assert keys are completely distinct
    assert key_run1 != key_run2
    
    # Store result under replicate 1
    cache.put(key_run1, "run-replicate-1", {"prompt": "user prompt"}, {"result": "PASS"}, {"tokens": 150})
    
    # Query with replicate 2 produces cache miss
    assert cache.get(key_run2) is None
    # Query with replicate 1 produces cache hit
    assert cache.get(key_run1) is not None
