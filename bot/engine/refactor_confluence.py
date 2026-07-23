import re

file_path = r"c:\Users\PC\Desktop\akkauntim-connect\bot\engine\confluence.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update cfg definition
old_cfg = """    cfg = {
        "score_threshold_execute": 100,   # 100+ = avtomatik EXECUTE
        "score_threshold_ai": 60,         # 60-99 = AI qaror bersin
        "max_zone_distance_atr": 2.0,     # OB/FVG max masofa (ATR birligida)
        "prz_overlap_threshold": 0.5,     # ATR*0.5 masofa = overlap hisoblanadi
        "ob_ball": 40,
        "prz_overlap_ball": 40,
        "fvg_ball": 20,
        "trend_ball": 15,
        "liquidity_ball": 15,
        "news_ball": 10,
        "wyckoff_spring_ball": 30,
        "wyckoff_phase_ball": 15,
        "wyckoff_penalty": -30,
        "sr_volume_ball": 25,
        "auto_pattern_ball": 30,
        "kill_zone_ball": 15,
        "overlap_ball": 10,
    }"""

new_cfg = """    cfg = {
        "score_threshold_execute": 30,    # 30+ = avtomatik EXECUTE
        "score_threshold_ai": 20,         # 20-29 = AI qaror bersin
        "max_zone_distance_atr": 2.0,     # OB/FVG max masofa (ATR birligida)
        "prz_overlap_threshold": 0.5,     # ATR*0.5 masofa = overlap hisoblanadi
        "smc_ob_weight": 10,
        "harmonic_prz_weight": 10,
        "smc_fvg_weight": 10,
        "smc_trend_weight": 10,
        "smc_liquidity_weight": 10,
        "news_bias_weight": 10,
        "wyckoff_spring_weight": 10,
        "wyckoff_phase_weight": 10,
        "sr_volume_weight": 10,
        "auto_pattern_weight": 10,
        "kill_zone_weight": 10,
        "overlap_bonus_weight": 10,
    }"""

content = content.replace(old_cfg, new_cfg)

# 2. Add get_weight helper function after cfg.update(config)
helper_func = """    if config:
        cfg.update(config)

    def get_weight(key: str) -> int:
        return max(5, min(20, cfg.get(key, 10)))"""
content = content.replace("    if config:\n        cfg.update(config)", helper_func)

# 3. Replace all point additions with new weight keys
replacements = {
    'cfg["ob_ball"]': 'get_weight("smc_ob_weight")',
    'cfg["fvg_ball"]': 'get_weight("smc_fvg_weight")',
    'cfg["prz_overlap_ball"]': 'get_weight("harmonic_prz_weight")',
    'cfg["overlap_ball"]': 'get_weight("overlap_bonus_weight")',
    'cfg["trend_ball"]': 'get_weight("smc_trend_weight")',
    'cfg["liquidity_ball"]': 'get_weight("smc_liquidity_weight")',
    'cfg["news_ball"]': 'get_weight("news_bias_weight")',
    'cfg["wyckoff_spring_ball"]': 'get_weight("wyckoff_spring_weight")',
    'cfg["wyckoff_phase_ball"]': 'get_weight("wyckoff_phase_weight")',
    'cfg["wyckoff_penalty"]': '-10', # Fixed penalty
    'cfg["sr_volume_ball"]': 'get_weight("sr_volume_weight")',
    'cfg["auto_pattern_ball"]': 'get_weight("auto_pattern_weight")',
    'cfg["kill_zone_ball"]': 'get_weight("kill_zone_weight")',
    
    # Text adjustments inside score_breakdown
    '"fresh_ob"': '"smc_fresh_ob"',
    '"fvg"': '"smc_fvg"',
    '"prz_overlap"': '"harmonic_prz_overlap"',
    '"trend_align"': '"smc_trend_align"',
    '"liquidity_sweep"': '"smc_liquidity_sweep"',
    '"news_bias"': '"news_bias_align"',
    '"wyckoff_spring"': '"wyckoff_spring"',
    '"sr_volume"': '"sr_volume_breakout"',
    '"kill_zone"': '"kill_zones_session"',
}

for old, new in replacements.items():
    content = content.replace(old, new)

# 4. Modify Risk Calculator (_calculate_risk_pct) at bottom
old_risk_logic = """    ob_score = breakdown.get("fresh_ob", 0)
    prz_score = breakdown.get("prz_overlap", 0)
    combined_core = ob_score + prz_score

    if total_score >= 100 and combined_core >= 60:
        return 0.04  # 4% — uchta strategiya + kuchli overlap
    elif total_score >= cfg.get("score_threshold_execute", 70):
        if combined_core >= 50:
            return 0.03  # 3% — kuchli confluence
        else:
            return 0.025  # 2.5% — yaxshi confluence lekin zaifroq
    elif total_score >= cfg.get("score_threshold_ai", 50):
        return 0.02  # 2% — AI xulosasiga tashlanadigan o'rtacha signal
    else:
        return 0.0  # yetarli emas"""

new_risk_logic = """    ob_score = breakdown.get("smc_fresh_ob", 0)
    prz_score = breakdown.get("harmonic_prz_overlap", 0)

    if total_score >= 40:
        return 0.04  # 4% — 4+ ta sabab, juda kuchli
    elif total_score >= cfg.get("score_threshold_execute", 30):
        return 0.03  # 3% — 3 ta sabab, EXECUTE
    elif total_score >= cfg.get("score_threshold_ai", 20):
        return 0.02  # 2% — kamida 2 ta sabab (AI DECIDE)
    else:
        return 0.0  # yetarli emas (< 20)"""

content = content.replace(old_risk_logic, new_risk_logic)

# Overwrite
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("confluence.py successfully refactored!")
