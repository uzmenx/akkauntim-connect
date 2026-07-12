import MetaTrader5 as mt5
from order_manager import place_order

if not mt5.initialize():
    print("MT5 ulanishda xatolik:", mt5.last_error())
    quit()

# QO'LDA BELGILANGAN TEST QIYMATLARI (AI'siz, faqat modulni sinash uchun)
success, message, info = place_order(
    symbol="EURUSD",
    signal="BUY",
    lot_size=0.01,          # eng kichik hajm — faqat test uchun
    stop_loss_pips=20,
    take_profit_pips=40
)

print("Natija:", message)
if success:
    print("Order ma'lumoti:", info)

mt5.shutdown()