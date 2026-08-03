import sys

with open('bot/sync/supabase_sync.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = '''                    "closed_at": datetime.datetime.fromtimestamp(d.time).isoformat(),
                })'''
replacement = '''                    "closed_at": datetime.datetime.fromtimestamp(d.time).isoformat(),
                    "mt5_comment": str(d.comment) if getattr(d, 'comment', None) else "",
                    "mt5_reason": int(d.reason) if hasattr(d, 'reason') else None,
                })'''

code = code.replace(target, replacement)

with open('bot/sync/supabase_sync.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied.")
