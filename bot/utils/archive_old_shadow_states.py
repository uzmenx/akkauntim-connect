import os
import sqlite3
import logging
import datetime
from typing import Tuple

logger = logging.getLogger(__name__)

def archive_old_shadow_states(db_path: str = "bot_learning.db", days_cutoff: int = 90, threshold_mb: float = 100.0) -> Tuple[bool, str]:
    """
    Checks bot_learning.db size. If it exceeds threshold_mb (default 100MB) or manual run,
    archives shadow_states older than days_cutoff to an archive SQLite file (compressed/separate)
    and VACUUMs the main database.
    """
    if not os.path.exists(db_path):
        return False, f"Database file {db_path} does not exist."
    
    file_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    logger.info(f"Checking {db_path}: Current size is {file_size_mb:.2f} MB")
    
    if file_size_mb < threshold_mb and not os.environ.get("FORCE_ARCHIVE"):
        return True, f"Database size ({file_size_mb:.2f} MB) is below threshold ({threshold_mb} MB). No archiving needed."

    cutoff_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_cutoff)).isoformat()
    archive_db_name = f"bot_learning_archive_{datetime.datetime.now().strftime('%Y%m%d')}.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table shadow_states exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shadow_states'")
        if not cursor.fetchone():
            conn.close()
            return False, "Table shadow_states not found in database."

        # Count records to archive
        cursor.execute("SELECT COUNT(*) FROM shadow_states WHERE timestamp < ?", (cutoff_date,))
        old_count = cursor.fetchone()[0]
        
        if old_count == 0:
            conn.close()
            return True, f"No records older than {days_cutoff} days found to archive."

        # Attach archive DB and transfer old records
        cursor.execute("ATTACH DATABASE ? AS archive", (archive_db_name,))
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archive.shadow_states AS 
            SELECT * FROM main.shadow_states WHERE 1=0
        ''')
        
        cursor.execute('''
            INSERT INTO archive.shadow_states 
            SELECT * FROM main.shadow_states WHERE timestamp < ?
        ''', (cutoff_date,))
        
        # Delete archived rows from main table
        cursor.execute("DELETE FROM main.shadow_states WHERE timestamp < ?", (cutoff_date,))
        conn.commit()
        
        cursor.execute("DETACH DATABASE archive")
        conn.commit()
        
        # Reclaim disk space
        logger.info(f"Vacuuming {db_path} after archiving {old_count} rows...")
        cursor.execute("VACUUM")
        conn.close()
        
        new_size_mb = os.path.getsize(db_path) / (1024 * 1024)
        msg = f"Archived {old_count} old rows to {archive_db_name}. Reduced DB size from {file_size_mb:.2f} MB to {new_size_mb:.2f} MB."
        logger.info(msg)
        return True, msg

    except Exception as e:
        logger.error(f"Error archiving shadow states: {e}")
        return False, str(e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success, message = archive_old_shadow_states(threshold_mb=0.1) # test/run check
    print(message)
