import MetaTrader5 as mt5

# MT5 terminaliga ulanish
if not mt5.initialize():
    print("Ulanishda xatolik, kod:", mt5.last_error())
    quit()

# Hisob ma'lumotlarini ko'rsatish
account_info = mt5.account_info()
print("Hisob raqami:", account_info.login)
print("Balans:", account_info.balance, account_info.currency)
print("Server:", account_info.server)

# EURUSD narxini olish
symbol = "EURUSD"
tick = mt5.symbol_info_tick(symbol)
print(f"\n{symbol} narxi:")
print("Bid (sotish):", tick.bid)
print("Ask (sotib olish):", tick.ask)

# Ulanishni yopish
mt5.shutdown()