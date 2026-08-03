import MetaTrader5 as mt5

if not mt5.initialize():
    print("Xatolik:", mt5.last_error())
    quit()

symbol = "EURUSD"
symbol_info = mt5.symbol_info(symbol)
account_info = mt5.account_info()

print("Balans:", account_info.balance)
print("Point:", symbol_info.point)
print("Trade tick value:", symbol_info.trade_tick_value)
print("Trade tick size:", symbol_info.trade_tick_size)
print("Volume min:", symbol_info.volume_min)
print("Volume max:", symbol_info.volume_max)
print("Volume step:", symbol_info.volume_step)
print("Contract size:", symbol_info.trade_contract_size)

mt5.shutdown()