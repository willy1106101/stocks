from fastapi import APIRouter
from pydantic import BaseModel
from db import get_db_connection

router = APIRouter()

class SettingItem(BaseModel):
    key: str
    value: str

@router.get("/api/settings/{key}")
def get_setting(key: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return {"value": row["value"] if row else ""}

@router.post("/api/settings")
def save_setting(item: SettingItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (item.key, item.value))
    conn.commit()
    conn.close()
    return {"status": "success"}