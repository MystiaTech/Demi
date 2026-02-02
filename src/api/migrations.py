import sqlite3
import os
from src.core.logger import DemiLogger

logger = DemiLogger()

def get_db_path() -> str:
    """Get database path from environment or config"""
    # Try DATABASE_URL first
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url.replace("sqlite:///", "")

    # Fall back to config-based path
    from pathlib import Path
    demi_dir = Path(os.getenv("DEMI_DATA_DIR", "~/.demi")).expanduser()
    demi_dir.mkdir(parents=True, exist_ok=True)
    return str(demi_dir / "demi.sqlite")

def create_users_table():
    """Create users table if not exists"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP
        )
        """)
        # Index for login lookups
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email
        ON users(email)
        """)
        conn.commit()
        logger.info("Users table created/verified")

def create_sessions_table():
    """Create sessions table for multi-device support"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            device_fingerprint TEXT,
            refresh_token_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            last_activity TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """)
        # Index for session lookups
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user
        ON sessions(user_id, is_active, expires_at)
        """)
        conn.commit()
        logger.info("Sessions table created/verified")

def run_all_migrations():
    """Run all database migrations"""
    create_users_table()
    create_sessions_table()
