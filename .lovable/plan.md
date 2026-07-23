
# AI Trading Bot — Professional Yaxshilash Rejasi

Kod bazasini o'qib chiqdim (`bot/main.py`, `bot/execution/*`, `bot/engine/*`, `bot/core/*`, `bot/sync/*`). Quyida topilgan **haqiqiy xatolar** va bosqichma-bosqich yaxshilashlar. Har bir band qat'iy tartibda — avval bug-fix, keyin funksional yaxshilashlar.

---

## FAZA 1 — Kritik BUG'lar (avval shu, aks holda risk noto'g'ri)

1. **`RiskManager.check_daily_loss_limit` doim default'ga tushadi**
   - `getattr(self.config, "max_daily_loss", 0.10)` — lekin `BotConfig` da maydon nomi `max_daily_loss_pct`. Har doim 10% ishlaydi.
   - Tuzatish: `max_daily_loss_pct` ga o'zgartirish + Cloud'dan kelgan `max_daily_loss` bilan sinxronlash.

2. **`OrderManager` da `stops_level` birligi noto'g'ri**
   - `stop_level_pips = symbol_info.trade_stops_level / 10.0` — bu faqat 5-xonali forex uchun to'g'ri. Gold (2 xona) va 3-xonali JPY uchun xato → SL/TP juda yaqin qo'yilib order rad etiladi.
   - Tuzatish: har symbol uchun `point`, `digits` va `pip_size` ni bitta helper (`_pip_size(symbol)`) orqali hisoblab, `stops_level` ni `point` da qoldirib `pip_size` orqali pips'ga o'girish.

3. **`RiskManager.calculate_lot_size` — hisob valyutasi konvertatsiyasi yo'q**
   - `tick_value` broker tomonidan hisob valyutasida beriladi, lekin kross juftliklarda (EURJPY, XAUUSD USD hisobda) `contract_size × tick_size × rate` bilan cheklash yo'q.
   - Tuzatish: `mt5.order_calc_profit(...)` orqali "1 pip = qancha USD" ni to'g'ridan-to'g'ri MT5 dan olish (allaqachon `order_calc_margin` mavjud).

4. **`bot/main.py::_get_smc_data` mavjud bo'lmagan modulni import qiladi**
   - `from bot.strategy.smc.structure import SMCStructure` — papkada faqat `zones.py` bor. Har siklda except'ga tushadi, SMC voting doimo HOLD.
   - Tuzatish: `bot/strategy/smc/engine.py` orqali `analyze_market_structure` natijasidan trend'ni ajratib olish.

5. **`AIClient` model nomlari xato + narx jadvali eskirgan**
   - `models_to_try` ga `claude-3-5-sonnet-20240620` majburan qo'shiladi, config esa `claude-sonnet-4-6` (mavjud emas) ni sanaydi. Barcha model'lar 404 bo'lganda AI o'chib qoladi.
   - Tuzatish: yagona ro'yxat (`claude-sonnet-4-5`, `claude-haiku-4-5`), `_calculate_cost` ni real narxlarga moslash, `.env` orqali override.

6. **`SupabaseSync.log_claude_cost` har chaqiruvda kumulyativ jami cost yuboradi**
   - `run_cycle` da `self.ai.total_cost` yuboriladi, lekin Edge Function `add_claude_cost` ni qo'shadi → cost ikki barobar oshib boradi.
   - Tuzatish: bot tomonda `delta = total_cost - last_reported_cost` ni yuborish.

---

## FAZA 2 — Ma'lumot va MT5 aloqasi

7. **Rate-cache** — har symbol uchun H1/M5/M15 ma'lumotlarini `run_cycle` boshida bir marta olib, barcha strategiyalarga uzatish (hozir SMC/Harmonic/Wyckoff/SR/Auto Patterns har biri qayta-qayta `copy_rates` chaqiryapti).
8. **Reconnect** — `MT5Client._check_connection` faqat `terminal_info` ni ko'radi; `login` muvaffaqiyatsiz bo'lsa qayta login qilmaydi. `connect()` ni exponential backoff bilan 3 marta urinib ko'rish.
9. **Symbol tanlash** — `symbol_select` ni siklning boshida bir marta bajarish; `symbol_info.visible` bo'lmasa ogohlantirish yozib symbol'ni ro'yxatdan chiqarish.

---

## FAZA 3 — Risk va portfel darajasi

10. **Bir symbol bo'yicha max ochiq pozitsiya** (default 1) — hozir cheklov yo'q, bot bir XAUUSD ni 5 marta ochishi mumkin.
11. **Korrelyatsiya cap** — bir vaqtda ochiq umumiy risk `≤ 2 × risk_per_trade` (masalan XAUUSD + EURUSD*USD ta'siri).
12. **Trailing daily-loss lock** — kunlik zarar `max_daily_loss_pct` ga yetsa, ochiq pozitsiyalarni yopmasdan yangi order **oldini olish**; hozir yopib yuboradigan mantiq yo'q va yangi savdo bloki `daily_loss_pct >= max` bo'lganda ham default 10% ga tushadi (bug #1).
13. **Cooldown** — bir symbol yopilgandan keyin N minut yangi entry taqiqlansin (revenge-trade ni oldini oladi).
14. **News blackout** — high-impact yangilikdan ±15 daqiqa oldin/keyin market order taqiqlansin (news straddle'dan tashqari).

---

## FAZA 4 — Order va Limit joylashtirish

15. **`PENDING_LIMIT` yo'nalishida sanity-check** — AI qaytargan `entry_price` joriy narxdan noto'g'ri tomonda bo'lsa (BUY_LIMIT current > ask), avtomatik BUY_STOP ga o'girish yoki rad etish.
16. **Pending order TTL** — pending order'lar `type_time = GTC` emas, `SPECIFIED` (masalan 6 soat) qilinsin — eskirgan setup'lar ochilmaydi.
17. **Broker filling mode** — `_get_filling_mode` `FILLING_RETURN` faqat pending uchun ruxsat etilsin; market'da `FOK/IOC` majburan.
18. **TP1 = alohida order** — hozirgi 70% partial-close ni ochilishda TP1 sifatida joylashtirish (broker tomonida) + `manage_open_trades` faqat qolgan 30% ni trail qilsin. Bu ulanish uzilganda ham TP1 ishlashini kafolatlaydi.
19. **`slippage/deviation` symbol-aware** — hozir hardcoded 20; volatile symbol'lar (XAUUSD) uchun kattaroq, majorlar uchun kichikroq.

---

## FAZA 5 — Strategiya va Confluence

20. **Per-symbol confluence weights** — `TradeReviewer` hozir yagona `reason_weights` beradi; buni `symbol → weights` ga kengaytirish (XAUUSD SMC og'irroq, majorlar Kill Zones og'irroq).
21. **Regime detection** — ATR/ADX asosida `trend / range / high-vol` rejimi aniqlab, range rejimida trend-follow strategiyalar og'irligini kamaytirish.
22. **MTF konfliktida threshold** — H4 va H1 qarama-qarshi bo'lsa `score_threshold_execute` ni +15 ga oshirish (hozir har doim bir xil).
23. **Session-based risk** — `kill_zones` faol bo'lsa `risk_pct` +25%; Asia sessiyasida majorlar uchun -25%.

---

## FAZA 6 — AI Learning

24. **Feature/Outcome dataset** — har `run_cycle` da confluence breakdown + har strategiyaning signal'i + so'ngra yopilgan savdo natijasi (`profit_r`, `hit_tp1`, `hit_sl`) `bot_learning.db` ga yozilsin. Bu keyinchalik oflayn ML uchun asos.
25. **Per-strategy KPI** — har strategiya (SMC, Harmonic, Wyckoff, SR, Auto Patterns, Kill Zones) uchun win-rate, expectancy alohida hisoblanib, `TradeReviewer` ga kirish sifatida uzatilsin. AI shu raqamlar asosida weight'ni tavsiya qiladi.
26. **A/B ghost-mode** — yangi `adjustments` set 10 savdodan keyin faol bo'lgunicha "ghost" tarzda log qilinib, eskisi bilan taqqoslansin. Yomonlashtirsa `revert`.
27. **Prompt kesh sifat nazorati** — hozirgi `_get_state_hash` juda dag'al (faqat 5 maydon). Confluence breakdown + spread bandi qo'shilsin, aks holda bir xil hash bo'lgan ikki xil setup uchun eski AI javob qaytariladi.

---

## FAZA 7 — Kuzatuv va sinovlar

28. **Structured logging** — har `run_cycle` oxirida bitta JSON qator: `{symbol, score, decision, sl, tp, lot, result}` — keyingi analitika uchun.
29. **Sog'liq endpoint** — `SupabaseSync` da har siklda `heartbeat` (last_cycle_time, last_error) yuborilsin, panel'da "bot online/offline" ko'rsatish uchun.
30. **Unit-testlar** — `tests/` ostida uchta yangi test:
    - `test_lot_math.py` — `calculate_lot_size` gold/JPY/major'da.
    - `test_stops_level.py` — SL/TP tumans hisobi.
    - `test_daily_loss.py` — max_daily_loss_pct trigger.
31. **Backtest sanity** — `bot/engine/backtester.py` orqali oxirgi 3 oy uchun eng ko'p savdo qilingan 3 symbol bo'yicha yopiq halqa (dry-run) hisobot: win-rate, PF, max DD.

---

## Tavsiya etilgan bajarish tartibi

1. Faza 1 (bug-fixes) — 1 iteratsiya, kod diff kichik.
2. Faza 2 + Faza 4 (data + order sifat) — birga; xavfsizlikka bevosita ta'sir.
3. Faza 3 (portfel risk) — mustaqil bosqich.
4. Faza 5 + Faza 6 (strategiya + learning) — birga, chunki learning yangi weight'ni beradi.
5. Faza 7 (test + monitor) — yopuvchi.

## Tasdiq so'raladigan qarorlar

- **Bir symbolga max ochiq pozitsiya:** default `1` yoki `2`?
- **News blackout oynasi:** ±15 daqiqami yoki ±30?
- **TP1 broker tomonida:** ha (2 ta alohida order — 70% TP1, 30% TP2) yoki hozirgidek bot tomonida partial-close saqlansinmi?
- **Cooldown davomiyligi:** yopilgan savdodan keyin nechа daqiqa (30 / 60 / 120)?

Rejaga OK bering — Faza 1 dan boshlab bajaraman.
