# Yuksalish & Yuksal — global CLI

Botni istalgan katalogdan `yuksalish` yoki qisqacha `yuksal` kalit so'zi bilan tezkor ishga tushirish uchun qo'llanma.

## 1) O'rnatish (bir marta)

Loyiha katalogida (`C:\Users\PC\Desktop\akkauntim-connect`) terminal oching:

```bash
pip install -e .
```

Bu `yuksalish` va `yuksal` buyruqlarini tizim `PATH`iga qo'shadi.

> Windowsda `pip` topilmasa: `py -m pip install -e .`

## 2) Loyiha yo'lini eslab qolish (YUKSALISH_HOME)

Bot `.env` va `config.json` fayllarini to'g'ri o'qishi uchun tizimga loyiha katalogini ko'rsatish kerak. Buning uchun Windows buyruq satrida (CMD) quyidagi buyruqni bir marta bajaring:

**Windows (CMD, doimiy):**
```cmd
setx YUKSALISH_HOME "C:\Users\PC\Desktop\akkauntim-connect"
```
*Eslatma: `setx` buyrug'i bajarilgandan so'ng, o'zgarishlar kuchga kirishi uchun joriy CMD oynasini yopib, yangi CMD oynasini oching.*

**Linux / macOS (bash/zsh):**
```bash
echo 'export YUKSALISH_HOME="/Users/PC/Desktop/akkauntim-connect"' >> ~/.bashrc
source ~/.bashrc
```

## 3) Ishga tushirish

Endi terminal/CMD ning istalgan joyidan (katalogidan qat'i nazar) quyidagi so'zning birini yozib enterni bossangiz bot avtomatik ishga tushadi:

```cmd
yuksal
```
yoki
```cmd
yuksalish
```

To'xtatish: `Ctrl+C`.

## Eslatmalar

- `pip install -r bot_requirements.txt` endi shart emas — `pip install -e .` barcha bog'liqliklarni o'zi o'rnatadi.
- Botni ishga tushirishdan oldin har safar yangi kodlarni yuklab olishni istasangiz, buyruq satriga git buyrug'ini qo'shib ishlatishingiz mumkin.
- Agar `YUKSALISH_HOME` o'rnatilmasa, bot joriy ishchi katalogdan `.env` va `config.json` fayllarini qidiradi.
