with open('bot/engine/prompt_builder.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == 'system_prompt += "':
        continue
    if line.strip() == '=== AI TRADE REVIEWER XULOSASI ===':
        continue
    if line.strip() == "Quyidagi tavsiyalar avvalgi xatolaringdan o'rganilgan:":
        continue
    if line.strip() == '=== KITOBLARDAN O\'RGANILGAN QOIDALAR ===':
        continue
    if line.strip() == "Quyidagi qoidalar sening o'qigan kitoblaringdan olingan:":
        continue
    if line.strip() == '=== AI XOTIRASI (OLDINGI SABOQLAR) ===':
        continue
    if line.strip() == "Quyidagi saboqlar sening oldingi savdolaring va xatolaringdan olingan:":
        continue
    if line.strip() == '" + json.dumps(context.get(\'learning_adjustments\', {}))':
        continue
    if line.strip() == '" + str(context.get(\'book_knowledge\', "Hali kitob o\'qilmagan."))':
        continue
    if line.strip() == '" + str(context.get(\'ai_memory\', "Xotira hali bo\'sh."))':
        continue
    new_lines.append(line)

with open('bot/engine/prompt_builder.py', 'w') as f:
    f.writelines(new_lines)
