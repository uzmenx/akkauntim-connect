import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

target = """        self.scaler = best_dataset.scaler
        self._save_scaler(best_dataset)"""
        
replacement = """        self.scaler = best_dataset.scaler
        self._save_scaler(best_dataset)
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump({"seq_length": best_config['seq_length'], "bidirectional": best_config['bidirectional']}, f)
            self.seq_length = best_config['seq_length']
        except Exception as e:
            logger.warning(f"Config saqlashda xatolik: {e}")"""
            
if target in content:
    with open("bot/learning/predictor.py", "w") as f:
        f.write(content.replace(target, replacement))
    print("Patched optimize_architecture")
else:
    print("Target not found")
