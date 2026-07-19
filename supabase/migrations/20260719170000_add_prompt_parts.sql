ALTER TABLE public.bot_settings 
ADD COLUMN prompt_identity TEXT DEFAULT 'Sen professional Forex treyderi va fundamental tahlilchisisan.',
ADD COLUMN prompt_strategy TEXT DEFAULT 'SMC, Garmonik patternlar va Iqtisodiy yangiliklarni birlashtirib eng yaxshi nuqtadan savdoga kirish qarorini qabul qilgin.',
ADD COLUMN prompt_output TEXT DEFAULT 'JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday izoh yoki tushuntirish yozma. Format: {"signal": "BUY" | "SELL" | "HOLD", "confidence": 0-100, "reasoning": "...", "stop_loss_pips": 20, "take_profit_pips": 40}';
