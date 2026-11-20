import os
import json
import sqlite3
import hashlib
import requests
from datetime import datetime
from typing import Dict, Any, Optional

DB_FILE = "saas_database.db"
CONFIG_FILE = "config.json"

def get_supabase_credentials():
    """Reads Supabase credentials from st.secrets, config.json, or environment variables."""
    sb_url = ""
    sb_key = ""
    
    # 1. Try Streamlit Secrets (for cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            sb_url = st.secrets.get("SUPABASE_URL", "")
            sb_key = st.secrets.get("SUPABASE_KEY", "")
    except Exception:
        pass
        
    # 2. Try environment variables
    if not sb_url or not sb_key:
        sb_url = os.environ.get("SUPABASE_URL", "")
        sb_key = os.environ.get("SUPABASE_KEY", "")
        
    # 3. Try local config.json
    if not sb_url or not sb_key:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    sb_url = sb_url or cfg.get("supabase_url", "")
                    sb_key = sb_key or cfg.get("supabase_key", "")
            except Exception:
                pass
            
    return (sb_url or "").strip().rstrip('/'), (sb_key or "").strip()

def is_supabase_enabled() -> bool:
    sb_url, sb_key = get_supabase_credentials()
    return bool(sb_url and sb_key and sb_url.startswith("http"))

def hash_password(password: str) -> str:
    """Hashes a password with SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ==========================================
# 1. LOCAL SQLITE DATABASE IMPLEMENTATION
# ==========================================

def get_local_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_local_db():
    conn = get_local_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        subscription_tier TEXT DEFAULT 'free',
        extractions_used INTEGER DEFAULT 0,
        extractions_limit INTEGER DEFAULT 2,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_reset_date TEXT
    )
    """)
    conn.commit()
    conn.close()

# ==========================================
# 2. SUPABASE REST API IMPLEMENTATION
# ==========================================

def supabase_headers(sb_key: str):
    return {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

# ==========================================
# 3. UNIFIED AUTHENTICATION INTERFACE
# ==========================================

def register_user(email: str, password: str) -> Dict[str, Any]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return {"success": False, "error": "Please enter a valid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters long."}
        
    pw_hash = hash_password(password)
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    # Mode A: Supabase Cloud
    if is_supabase_enabled():
        sb_url, sb_key = get_supabase_credentials()
        url = f"{sb_url}/rest/v1/users"
        payload = {
            "email": email,
            "password_hash": pw_hash,
            "subscription_tier": "free",
            "extractions_used": 0,
            "extractions_limit": 2,
            "last_reset_date": now_str
        }
        try:
            resp = requests.post(url, json=payload, headers=supabase_headers(sb_key), timeout=10)
            if resp.status_code in (200, 201):
                data = resp.json()
                user = data[0] if isinstance(data, list) and data else payload
                if "password_hash" in user:
                    del user["password_hash"]
                return {"success": True, "user": user}
            elif resp.status_code == 409 or "duplicate" in resp.text.lower():
                return {"success": False, "error": "An account with this email already exists. Please log in."}
            else:
                return {"success": False, "error": f"Supabase Error ({resp.status_code}): {resp.text}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to connect to Supabase: {str(e)}"}

    # Mode B: Local SQLite Database
    init_local_db()
    conn = get_local_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (email, password_hash, subscription_tier, extractions_used, extractions_limit, last_reset_date)
            VALUES (?, ?, 'free', 0, 2, ?)
        """, (email, pw_hash, now_str))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {
            "success": True,
            "user": {
                "id": user_id,
                "email": email,
                "subscription_tier": "free",
                "extractions_used": 0,
                "extractions_limit": 2
            }
        }
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "An account with this email already exists. Please log in."}
    except Exception as e:
        conn.close()
        return {"success": False, "error": f"Registration failed: {str(e)}"}

def login_user(email: str, password: str) -> Dict[str, Any]:
    email = email.strip().lower()
    pw_hash = hash_password(password)
    
    # Mode A: Supabase Cloud
    if is_supabase_enabled():
        sb_url, sb_key = get_supabase_credentials()
        url = f"{sb_url}/rest/v1/users?email=eq.{email}&select=*"
        try:
            resp = requests.get(url, headers=supabase_headers(sb_key), timeout=10)
            if resp.status_code == 200:
                rows = resp.json()
                if not rows:
                    return {"success": False, "error": "No account found with this email."}
                user = rows[0]
                if user.get("password_hash") != pw_hash:
                    return {"success": False, "error": "Incorrect password. Please try again."}
                del user["password_hash"]
                return {"success": True, "user": user}
            else:
                return {"success": False, "error": f"Supabase Error: {resp.text}"}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    # Mode B: Local SQLite Database
    init_local_db()
    conn = get_local_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"success": False, "error": "No account found with this email."}
        
    if row["password_hash"] != pw_hash:
        return {"success": False, "error": "Incorrect password. Please try again."}
        
    user_dict = dict(row)
    del user_dict["password_hash"]
    return {"success": True, "user": user_dict}

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    email = email.strip().lower()
    
    # Mode A: Supabase Cloud
    if is_supabase_enabled():
        sb_url, sb_key = get_supabase_credentials()
        url = f"{sb_url}/rest/v1/users?email=eq.{email}&select=*"
        try:
            resp = requests.get(url, headers=supabase_headers(sb_key), timeout=10)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    u = rows[0]
                    if "password_hash" in u:
                        del u["password_hash"]
                    return u
        except Exception:
            pass
        return None

    # Mode B: Local SQLite
    init_local_db()
    conn = get_local_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        del d["password_hash"]
        return d
    return None

def record_extraction_usage(email: str) -> Dict[str, Any]:
    email = email.strip().lower()
    user = get_user_by_email(email)
    if not user:
        return {"allowed": False, "error": "User not found."}
        
    tier = user.get("subscription_tier", "free")
    used = user.get("extractions_used", 0)
    limit = user.get("extractions_limit", 2)
    
    if tier == "pro":
        new_count = used + 1
        _update_usage_count(email, new_count)
        return {"allowed": True, "tier": "pro", "extractions_used": new_count, "limit": "Unlimited"}
        
    if used >= limit:
        return {
            "allowed": False,
            "tier": "free",
            "extractions_used": used,
            "limit": limit,
            "error": f"You have reached your Free Plan limit ({used}/{limit} videos). Upgrade to Pro for unlimited extractions!"
        }
        
    new_count = used + 1
    _update_usage_count(email, new_count)
    return {"allowed": True, "tier": "free", "extractions_used": new_count, "limit": limit}

def _update_usage_count(email: str, count: int):
    email = email.strip().lower()
    if is_supabase_enabled():
        sb_url, sb_key = get_supabase_credentials()
        url = f"{sb_url}/rest/v1/users?email=eq.{email}"
        try:
            requests.patch(url, json={"extractions_used": count}, headers=supabase_headers(sb_key), timeout=10)
        except Exception:
            pass
    else:
        init_local_db()
        conn = get_local_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET extractions_used = ? WHERE email = ?", (count, email))
        conn.commit()
        conn.close()

def upgrade_user_to_pro(email: str) -> bool:
    email = email.strip().lower()
    if is_supabase_enabled():
        sb_url, sb_key = get_supabase_credentials()
        url = f"{sb_url}/rest/v1/users?email=eq.{email}"
        try:
            r = requests.patch(url, json={"subscription_tier": "pro", "extractions_limit": 999999}, headers=supabase_headers(sb_key), timeout=10)
            return r.status_code in (200, 204)
        except Exception:
            return False
    else:
        init_local_db()
        conn = get_local_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET subscription_tier = 'pro', extractions_limit = 999999 WHERE email = ?", (email,))
        conn.commit()
        cnt = cursor.rowcount
        conn.close()
        return cnt > 0
