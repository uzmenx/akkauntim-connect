import os
import MetaTrader5 as mt5
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime

# Env faylni yuklash
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY")  # Yoki SERVICE_ROLE_KEY agar RLS bo'lsa

# Supabase klientini yaratish
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print("Supabase client ulanishda xato:", e)
    supabase = None

# Tizimda qaysi user_id ga yozish kerakligini bilish qiyin bo'lsa, xozircha bitta sabit ID ishlatamiz.
# Yoki Frontend Auth o'chirib qo'yilgan bo'lsa, "00000000-0000-0000-0000-000000000000" ni ishlatamiz
USER_ID = "00000000-0000-0000-0000-000000000000"

def sync_bot_status(is_running=True, message="Bot is running"):
    if not supabase: return
    if not mt5.initialize():
        print("sync_bot_status: MT5 ga ulanib bo'lmadi")
        return

    account_info = mt5.account_info()
    if account_info is None:
        print("sync_bot_status: Hisob ma'lumotlarini olib bo'lmadi")
        return

    equity = account_info.equity
    balance = account_info.balance
    currency = account_info.currency

    data = {
        "user_id": USER_ID,
        "is_running": is_running,
        "message": message,
        "account_equity": equity,
        "account_balance": balance,
        "account_currency": currency
    }

    try:
        supabase.table("bot_status").upsert(data).execute()
        print(f"OK: Bot Status sinxronlandi: Balans=${balance}")
    except Exception as e:
        print(f"XATO: Supabase ga bot_status yozishda xatolik: {e}")

def sync_positions():
    if not supabase: return
    if not mt5.initialize():
        return

    positions = mt5.positions_get()
    
    # Eskilarini o'chirishga harakat qilamiz
    try:
        supabase.table("positions").delete().eq("user_id", USER_ID).execute()
    except Exception:
        pass 

    if positions is None or len(positions) == 0:
        return

    new_data = []
    for pos in positions:
        side = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
        dt = datetime.datetime.fromtimestamp(pos.time).isoformat()
        
        new_data.append({
            "id": pos.ticket,
            "user_id": USER_ID,
            "symbol": pos.symbol,
            "side": side,
            "volume": pos.volume,
            "open_price": pos.price_open,
            "profit": pos.profit,
            "opened_at": dt
        })

    if new_data:
        try:
            supabase.table("positions").upsert(new_data).execute()
            print(f"OK: Ochiq pozitsiyalar sinxronlandi ({len(new_data)} ta)")
        except Exception as e:
            print(f"XATO: Supabase ga positions yozishda xatolik: {e}")

def run_sync():
    sync_bot_status()
    sync_positions()

if __name__ == "__main__":
    run_sync()
