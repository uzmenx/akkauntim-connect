import re

def update_shadow_engine():
    path = "bot/engine/shadow_decision_engine.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    target = '''            else:
                # Fallback if no fresh zones found
                if direction == "BUY":
                    sl_price = current_price - (1.5 * atr)
                else:
                    sl_price = current_price + (1.5 * atr)'''
                    
    replacement = '''            else:
                # Fallback if no fresh zones found
                warnings.append("SMC zonasi topilmadi (No Fresh Zones). Xavfsizlik maqsadida savdo bekor qilinmoqda.")
                return self._get_safe_fallback("SMC zonasi topilmadi", warnings)'''

    if 'SMC zonasi topilmadi (No Fresh Zones)' not in content:
        content = content.replace(target, replacement)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update_shadow_engine()
    print("Done")
