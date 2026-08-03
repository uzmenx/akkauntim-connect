import sys

with open("bot/learning/simulator.py", "r") as f:
    content = f.read()

# Add is_eval to __init__
content = content.replace(
    "def __init__(self, db_path: str, symbol=None, initial_balance=1000.0, max_steps=1000, curriculum_level=3):",
    "def __init__(self, db_path: str, symbol=None, initial_balance=1000.0, max_steps=1000, curriculum_level=3, is_eval=False):"
)

content = content.replace(
    "self.curriculum_level = curriculum_level",
    "self.curriculum_level = curriculum_level\n        self.is_eval = is_eval"
)

# Modify _load_data
old_load = """            df = pd.read_sql_query("SELECT price_open, price_high, price_low, price_close, tick_volume FROM shadow_states WHERE symbol = ? ORDER BY timestamp ASC LIMIT 50000", conn, params=(symbol,))
            conn.close()"""
new_load = """            df = pd.read_sql_query("SELECT price_open, price_high, price_low, price_close, tick_volume FROM shadow_states WHERE symbol = ? ORDER BY timestamp ASC LIMIT 50000", conn, params=(symbol,))
            conn.close()
            
            # OOS (Out-Of-Sample) split: last 20% for eval
            split_idx = int(len(df) * 0.8)
            if hasattr(self, 'is_eval') and self.is_eval:
                df = df.iloc[split_idx:].reset_index(drop=True)
            else:
                df = df.iloc[:split_idx].reset_index(drop=True)"""
content = content.replace(old_load, new_load)

# Modify _update_ui_stats
old_update = """    def _update_ui_stats(self, env, model, timesteps_played):
        try:
            # Modelni qisqa test qilib ko'ramiz
            obs = env.reset()"""
new_update = """    def _update_ui_stats(self, env, model, timesteps_played):
        try:
            # OOS test uchun yangi muhit
            eval_env = make_vec_env(lambda: TradingEnv(self.db_path, is_eval=True), n_envs=1)
            obs = eval_env.reset()"""
content = content.replace(old_update, new_update)

content = content.replace(
    "obs, rewards, dones, infos = env.step(action)",
    "obs, rewards, dones, infos = eval_env.step(action)"
)

with open("bot/learning/simulator.py", "w") as f:
    f.write(content)

print("Patched simulator.py")
