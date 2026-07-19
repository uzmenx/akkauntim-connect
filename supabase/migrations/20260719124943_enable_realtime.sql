-- Supabase Realtime-ni kerakli jadvallar uchun yoqish
-- Bu orqali frontend-ga har 2 soniyada so'rov yubormasdan (polling) WebSockets orqali darhol xabar keladi.

BEGIN;

-- Agar public nashrida (publication) supabase_realtime yo'q bo'lsa uni yaratish 
-- Odatda supabase_realtime avtomat bor bo'ladi, biz unga faqat jadvallarni ulaymiz.
-- Eslatma: Ba'zan CREATE PUBLICATION ruxsat etilmasligi mumkin, shuning uchun ALTER dan boshlaymiz.

ALTER PUBLICATION supabase_realtime ADD TABLE bot_status;
ALTER PUBLICATION supabase_realtime ADD TABLE positions;
ALTER PUBLICATION supabase_realtime ADD TABLE trade_history;
ALTER PUBLICATION supabase_realtime ADD TABLE ai_signals;
ALTER PUBLICATION supabase_realtime ADD TABLE bot_settings;

COMMIT;
