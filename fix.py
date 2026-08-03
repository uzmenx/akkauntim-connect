import re

with open('bot/engine/prompt_builder.py', 'r') as f:
    code = f.read()

bad_pattern = '''        system_prompt \+= "
=== AI TRADE REVIEWER XULOSASI ===
Quyidagi tavsiyalar avvalgi xatolaringdan o'rganilgan:
" \+ json\.dumps\(context\.get\('learning_adjustments', \{\}\)\)
        system_prompt \+= "
=== KITOBLARDAN O'RGANILGAN QOIDALAR ===
Quyidagi qoidalar sening o'qigan kitoblaringdan olingan:
" \+ str\(context\.get\('book_knowledge', "Hali kitob o'qilmagan\."\)\)
        system_prompt \+= "
=== AI XOTIRASI \(OLDINGI SABOQLAR\) ===
Quyidagi saboqlar sening oldingi savdolaring va xatolaringdan olingan:
" \+ str\(context\.get\('ai_memory', "Xotira hali bo'sh\."\)\)'''

good_pattern = '''        system_prompt += "\\n\\n=== AI TRADE REVIEWER XULOSASI ===\\nQuyidagi tavsiyalar avvalgi xatolaringdan o'rganilgan:\\n" + json.dumps(context.get('learning_adjustments', {}))
        system_prompt += "\\n\\n=== KITOBLARDAN O'RGANILGAN QOIDALAR ===\\nQuyidagi qoidalar sening o'qigan kitoblaringdan olingan:\\n" + str(context.get('book_knowledge', "Hali kitob o'qilmagan."))
        system_prompt += "\\n\\n=== AI XOTIRASI (OLDINGI SABOQLAR) ===\\nQuyidagi saboqlar sening oldingi savdolaring va xatolaringdan olingan:\\n" + str(context.get('ai_memory', "Xotira hali bo'sh."))'''

code = re.sub(bad_pattern, good_pattern, code)

with open('bot/engine/prompt_builder.py', 'w') as f:
    f.write(code)

