with open("bot/main.py", "r") as f:
    lines = f.readlines()

shadow_merger_start = -1
shadow_merger_end = -1
rl_agent_start = -1
rl_agent_end = -1

for i, line in enumerate(lines):
    if "# --- SHADOW MERGER TRACKING ---" in line:
        shadow_merger_start = i
    if "logger.error(f\"[{symbol}] Shadow Merger Tracker xatosi:" in line:
        shadow_merger_end = i + 2 # include # -----
    if "# RL Agent Action (Jonli qaror)" in line:
        rl_agent_start = i
    if "rl_action = \"HOLD\"" in line:
        rl_agent_end = i + 1

# Swap them
if shadow_merger_start != -1 and rl_agent_start != -1:
    shadow_block = lines[shadow_merger_start:shadow_merger_end]
    rl_block = lines[rl_agent_start:rl_agent_end]
    
    # We will also add rl_direction=rl_action to Shadow Merger Tracking
    # Find the shadow_trade_count line in the shadow_block
    for j, sl in enumerate(shadow_block):
        if "shadow_trade_count=shadow_stats[\"trade_count\"]" in sl:
            shadow_block[j] = sl.replace("shadow_trade_count=shadow_stats[\"trade_count\"]", "shadow_trade_count=shadow_stats[\"trade_count\"],\n                rl_direction=rl_action")
            break
            
    # Now build the new lines
    new_lines = lines[:shadow_merger_start] + rl_block + ["\n"] + shadow_block + lines[rl_agent_end:]
    
    with open("bot/main.py", "w") as f:
        f.writelines(new_lines)
    print("Updated bot/main.py successfully.")
else:
    print("Could not find blocks.")
