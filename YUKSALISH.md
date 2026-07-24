# Yuksalish — global CLI

Botni istalgan katalogdan `yuksalish` kalit so'zi bilan ishga tushirish uchun.

## 1) O'rnatish (bir marta)

Loyiha katalogida (bu repo joylashgan joyda) terminal oching:

```bash
pip install -e .
```

Bu `yuksalish` buyrug'ini tizim `PATH`iga qo'shadi.

> Windowsda `pip` topilmasa: `py -m pip install -e .`

## 2) Loyiha yo'lini eslab qolish

Bot `.env` va `config.json` fayllarini o'qishi kerak. Loyiha katalogini muhit o'zgaruvchisiga yozing:

**Windows (CMD, doimiy):**
```cmd
setx YUKSALISH_HOME "C:\path\to\forex_bot"
```
Yangi CMD oynasini oching (setx faqat yangi sessiyada ishlaydi).

**Linux / macOS (bash/zsh):**
```bash
echo 'export YUKSALISH_HOME="/path/to/forex_bot"' >> ~/.bashrc
source ~/.bashrc
```

## 3) Ishga tushirish

Endi CMD/Terminal istalgan joydan:

```
yuksalish
```

To'xtatish: `Ctrl+C`.

## Eslatma

- `pip install -r bot_requirements.txt` endi shart emas — `pip install -e .` bog'liqliklarni o'zi o'rnatadi.
- `python run_bot.py` ham ishlaydi (eski usul).
- Agar `YUKSALISH_HOME` o'rnatilmasa, bot joriy katalogdan `.env` qidiradi.
