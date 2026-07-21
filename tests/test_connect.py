import MetaTrader5 as mt5
import datetime

# MT5 terminaliga ulanish
if not mt5.initialize():
    print("Ulanishda xatolik, kod:", mt5.last_error())
    quit()

print("MT5 ga muvaffaqiyatli ulandi!\n")

# 1. Hisob ma'lumotlari
account_info = mt5.account_info()
if account_info is not None:
    print("=== HISOB MA'LUMOTLARI ===")
    print(f"Hisob raqami: {account_info.login}")
    print(f"Balans: {account_info.balance} {account_info.currency}")
    print(f"Ekvit (Equity): {account_info.equity}")
    print(f"Foyda (Profit): {account_info.profit}")
    print(f"Server: {account_info.server}")
    print("-" * 30)
else:
    print("Hisob ma'lumotlarini olib bo'lmadi.")

# 2. Narxni tekshirish
symbol = "EURUSD"
tick = mt5.symbol_info_tick(symbol)
if tick is not None:
    print(f"\n=== NARX TEKSHIRISH ({symbol}) ===")
    print(f"Bid (Sotish): {tick.bid}")
    print(f"Ask (Sotib olish): {tick.ask}")
    print("-" * 30)

# 3. Ochiq pozitsiyalarni olish
print("\n=== OCHIQ POZITSIYALAR ===")
positions = mt5.positions_get()
if positions is None:
    print("Pozitsiyalarni olishda xatolik yuz berdi.")
elif len(positions) > 0:
    for pos in positions:
        side = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
        print(f"Ticket: {pos.ticket} | Symbol: {pos.symbol} | Type: {side} | Volume: {pos.volume} | Open: {pos.price_open} | Current: {pos.price_current} | Profit: {pos.profit}")
else:
    print("Ochiq pozitsiyalar yo'q.")
print("-" * 30)

# 4. Kutilayotgan buyurtmalar (Pending Orders)
print("\n=== KUTILAYOTGAN BUYURTMALAR ===")
orders = mt5.orders_get()
if orders is None:
    print("Buyurtmalarni olishda xatolik yuz berdi.")
elif len(orders) > 0:
    for ord in orders:
        print(f"Ticket: {ord.ticket} | Symbol: {ord.symbol} | Volume: {ord.volume_current} | Price: {ord.price_open}")
else:
    print("Kutilayotgan buyurtmalar yo'q.")
print("-" * 30)

# 5. Tarix (Barcha yopiq savdolar)
print("\n=== SAVDO TARIXI (Barcha tarix) ===")
from_date = datetime.datetime(2000, 1, 1)
to_date = datetime.datetime(2030, 1, 1)
deals = mt5.history_deals_get(from_date, to_date)
if deals is None:
    print("Tarixni olishda xatolik yuz berdi.")
elif len(deals) > 0:
    print(f"Umumiy tarixda {len(deals)} ta amal topildi. Quyida ularning tahlili:")
    found_trades = False
    for deal in deals:
        if deal.entry in (1, 2) and deal.symbol: # Faqat savdo pozitsiyalarini yopish amallari
            side = "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL"
            print(f"Ticket: {deal.position_id} | Symbol: {deal.symbol} | Type: {side} | Volume: {deal.volume} | Price: {deal.price} | Profit: {deal.profit}")
            found_trades = True
    if not found_trades:
        print("Savdolar topilmadi.")
else:
    print("Hech qanday tarix yo'q.")
print("-" * 30)

# Ulanishni yopish
mt5.shutdown()
print("\nMT5 ulanishi yopildi.")