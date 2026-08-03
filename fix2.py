with open('bot/engine/prompt_builder.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if i == 112:
        new_lines.append(line)
        new_lines.append('        system_prompt += "\\n\\n=== AI TRADE REVIEWER XULOSASI ===\\nQuyidagi tavsiyalar avvalgi xatolaringdan o\'rganilgan:\\n" + json.dumps(context.get(\'learning_adjustments\', {}))\n')
        new_lines.append('        system_prompt += "\\n\\n=== KITOBLARDAN O\'RGANILGAN QOIDALAR ===\\nQuyidagi qoidalar sening o\'qigan kitoblaringdan olingan:\\n" + str(context.get(\'book_knowledge\', "Hali kitob o\'qilmagan."))\n')
        new_lines.append('        system_prompt += "\\n\\n=== AI XOTIRASI (OLDINGI SABOQLAR) ===\\nQuyidagi saboqlar sening oldingi savdolaring va xatolaringdan olingan:\\n" + str(context.get(\'ai_memory\', "Xotira hali bo\'sh."))\n')
        continue
    if 113 <= i <= 127:
        continue
    new_lines.append(line)

with open('bot/engine/prompt_builder.py', 'w') as f:
    f.writelines(new_lines)
