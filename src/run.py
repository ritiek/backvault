import os
import logging
from bw_client import BitwardenClient
from datetime import datetime
from sys import stdout
import sqlcipher3
import hashlib
import base64
import uuid
from db import init_db, db_connect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(stdout)],
)
logger = logging.getLogger(__name__)

def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val

def init_db(db_path: str, PRAGMA_KEY: str):
    conn = sqlcipher3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA {PRAGMA_KEY}")
    conn.commit()


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_password TEXT NOT NULL,
            client_id TEXT NOT NULL,
            client_secret TEXT NOT NULL,
            file_password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def main():
    t_sha = hashlib.sha512()
    t_sha.update(base64.urlsafe_b64encode(uuid.uuid4().bytes) + base64.urlsafe_b64encode(uuid.uuid4().bytes))
    hashed_pragma = base64.urlsafe_b64encode(t_sha.digest())
    PRAGMA_KEY = f"key='{hashed_pragma.__str__()}';"
    init_db("backup/backvault.db", PRAGMA_KEY)

    db_conn = sqlcipher3.connect("backup/backvault.db")
    db_cursor = db_conn.cursor()

    db_cursor.execute("INSERT INTO keys VALUES (2, 'master_pw_example', 'client_id_example', 'client_secret_example', 'file_pw_example')")
    db_conn.commit()
    
    # Vault access information
    client_id = db_cursor.execute("SELECT client_id FROM keys").fetchone()[0]
    client_secret = db_cursor.execute("SELECT client_secret FROM keys").fetchone()[0]
    master_pw = db_cursor.execute("SELECT master_password FROM keys").fetchone()[0]
    file_pw = db_cursor.execute("SELECT file_password FROM keys").fetchone()[0]

    server = require_env("BW_SERVER")


    # Configuration
    backup_dir = os.getenv("BACKUP_DIR", "/app/backups")
    log_file = os.getenv("LOG_FILE")  # Optional log file
    encryption_mode = os.getenv("BACKUP_ENCRYPTION_MODE", "bitwarden").lower()

    if log_file:
        logger.addHandler(logging.FileHandler(log_file))

    os.makedirs(backup_dir, exist_ok=True)

    # Create client
    logger.info("Connecting to vault...")
    source = BitwardenClient(
        bw_cmd="bw",
        server=server,
        client_id=client_id,
        client_secret=client_secret,
        use_api_key=True,
    )
    try:
        try:
            source.login()
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return

        try:
            source.unlock(master_pw)
        except Exception as e:
            logger.error(f"Unlock failed: {e}")
            return

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.enc")

        logger.info(f"Starting export with mode: '{encryption_mode}'")

        if encryption_mode == "raw":
            source.export_raw_encrypted(backup_file, file_pw)
        elif encryption_mode == "bitwarden":
            source.export_bitwarden_encrypted(backup_file, file_pw)
        else:
            logger.error(
                f"Invalid BACKUP_ENCRYPTION_MODE: '{encryption_mode}'. Must be 'bitwarden' or 'raw'."
            )
            return

        logger.info(f"Export completed successfully to {backup_file}.")
    finally:
        source.logout()
        logger.info("Successfully logged out.")


if __name__ == "__main__":
    main()
