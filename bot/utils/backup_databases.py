import os
import gzip
import shutil
import datetime
import logging

logger = logging.getLogger(__name__)

def backup_databases(config, databases=None):
    """Ma'lumotlar bazalarini gzip qilib Supabase Storage ga saqlash."""
    if databases is None:
        databases = ["decisions_log.db", "bot_learning.db", "trade_state.db"]
        
    try:
        if not getattr(config, "supabase_url", None) or not getattr(config, "supabase_key", None):
            logger.warning("Supabase URL yoki Key yo'q, backup o'tkazib yuborildi.")
            return False
            
        from supabase import create_client, Client
        supabase: Client = create_client(config.supabase_url, config.supabase_key)
        
        backup_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        success = True
        
        for db_file in databases:
            if not os.path.exists(db_file):
                logger.warning(f"Backup uchun {db_file} topilmadi.")
                continue
                
            gz_file = f"{db_file}.gz"
            try:
                # Zip fayl yaratish
                with open(db_file, 'rb') as f_in:
                    with gzip.open(gz_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                        
                # Supabase Storage ga yuklash
                bucket_name = "backups"
                remote_path = f"db_backups/{backup_date}/{gz_file}"
                
                with open(gz_file, 'rb') as f:
                    res = supabase.storage.from_(bucket_name).upload(
                        file=f,
                        path=remote_path,
                        file_options={"content-type": "application/gzip"}
                    )
                    
                logger.info(f"{db_file} zaxirasi Supabase'ga muvaffaqiyatli yuklandi: {remote_path}")
            except Exception as ex:
                if "Invalid Compact JWS" in str(ex):
                    logger.error(f"{db_file} ni zaxiralashda xatolik: SUPABASE_PUBLISHABLE_KEY haqiqiy JWT formati emas. Iltimos, .env faylidagi kalitni Supabase panelidagi to'g'ri 'anon' 'public' JWT kalitiga almashtiring.")
                else:
                    logger.error(f"{db_file} ni zaxiralashda xatolik: {ex}")
                success = False
            finally:
                # Local zip ni o'chirish
                if os.path.exists(gz_file):
                    os.remove(gz_file)
                    
        return success
    except Exception as e:
        logger.error(f"Backup jarayonida umumiy xatolik: {e}")
        return False
