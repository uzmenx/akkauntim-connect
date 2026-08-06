# Parolni tiklash (MT5 login + server orqali)

## Maqsad
1. Login sahifasida "Meni eslab qol" qatorining o'ng tomonida "Parolni unutdim?" havolasi.
2. Foydalanuvchi MT5 login va ro'yxatdan o'tgan MT5 serverini kiritib, o'zini tasdiqlaydi va yangi parol qo'yadi.

## Foydalanuvchi oqimi
```text
Login sahifa
  [ Meni eslab qol ]            [ Parolni unutdim? ]
                                        |
                                        v
  /reset-password  -> 1-qadam: MT5 Login + MT5 Server
                      2-qadam: Yangi parol + tasdiqlash
                      3-qadam: Muvaffaqiyat -> avtomatik /auth ga qaytish
```

## Nima qilinadi

### 1. Login sahifasi (`src/pages/AuthPage.tsx`)
- "Meni eslab qol" checkbox qatorini `justify-between` qilib, o'ng tomonga "Parolni unutdim?" havolasi qo'yiladi (faqat `signin` rejimida ko'rinadi).
- Havola `/reset-password` sahifasiga olib boradi. Mavjud shisha (glassmorphism) uslubi saqlanadi.

### 2. Yangi sahifa `src/pages/ResetPasswordPage.tsx`
- AuthPage bilan bir xil dizayn (fon, blob'lar, Card).
- 1-qadam: MT5 Login + MT5 Server maydonlari -> tekshirish.
- 2-qadam: Yangi parol (min 6 belgi) + qayta kiritish; mos kelmasa xato.
- Xatolar o'zbek tilida ("Login yoki server topilmadi", va h.k.).
- Muvaffaqiyatdan keyin login sahifasiga qaytariladi.

### 3. Route
- `src/App.tsx` ga `/reset-password` public route qo'shiladi (tizimga kirmasdan ochiladi).

### 4. Backend funksiya `reset-mt5-password`
Yangi edge function, ikki amalni bajaradi:
- `action: "verify"` — kiritilgan login+server `bot_settings` yozuvi bilan mos kelishini tekshiradi (server katta-kichik harf va bo'shliqlarga sezgir emas), mos bo'lsa qisqa muddatli (10 daqiqa) bir martalik token qaytaradi.
- `action: "reset"` — token to'g'ri bo'lsa, service role bilan foydalanuvchi parolini yangilaydi va `bot_settings.mt5_password` ni ham yangi parolga sinxronlaydi (bot ham shu parolni ishlatadi). Token ishlatilgach o'chiriladi.

## Texnik tafsilotlar
- Funksiya `verify_jwt = false` bilan ishlaydi (foydalanuvchi hali tizimga kirmagan), lekin ichida qat'iy validatsiya bo'ladi: zod bilan input tekshirish, login uchun raqam/uzunlik limiti.
- Tokenlar uchun kichik jadval `password_reset_tokens` (`id`, `user_id`, `token_hash`, `expires_at`, `used_at`). RLS yoqiladi, hech qanday client policy berilmaydi — faqat service role o'qiydi/yozadi. GRANT faqat `service_role` uchun.
- Brute-force himoyasi: bir login uchun 15 daqiqada 5 martadan ko'p urinishga ruxsat berilmaydi (urinishlar shu jadvalda hisoblanadi), noto'g'ri holatda umumiy xato matni qaytariladi (login mavjudligi oshkor qilinmaydi).
- Parol o'zgartirish `service_role` client bilan `auth.admin.updateUserById` orqali amalga oshiriladi.
- Frontend `supabase.functions.invoke("reset-mt5-password", ...)` ishlatadi.

## Xavfsizlik haqida ogohlantirish
MT5 login + server juftligi kuchli sir emas (login raqamini boshqa odam bilishi mumkin, serverlar esa ommaviy). Bu usul qulaylik uchun mos, lekin haqiqiy himoya uchun keyinchalik ixtiyoriy haqiqiy email yoki Telegram tasdiqlashini qo'shishni tavsiya qilaman.
