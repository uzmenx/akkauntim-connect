import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

# Fix predict
target1 = """        if not TORCH_AVAILABLE or self.model is None or len(recent_candles) < 10:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}
            
        features_np = compute_12_features(recent_candles)
        if len(features_np) < 10:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}

        features_seq = features_np[-10:] # Last 10 candles"""

replacement1 = """        if not TORCH_AVAILABLE or self.model is None or len(recent_candles) < self.seq_length:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}
            
        features_np = compute_12_features(recent_candles)
        if len(features_np) < self.seq_length:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}

        features_seq = features_np[-self.seq_length:] # Last seq_length candles"""

if target1 in content:
    content = content.replace(target1, replacement1)
    print("Patched predict")
else:
    print("Target1 not found")

# Fix check_class_imbalance
target2 = """        dataset = ShadowDataset(target_db, seq_length=10, split='all', symbol=self.symbol)"""
replacement2 = """        dataset = ShadowDataset(target_db, seq_length=getattr(self, 'seq_length', 10), split='all', symbol=self.symbol)"""

if target2 in content:
    content = content.replace(target2, replacement2)
    print("Patched check_class_imbalance")
else:
    print("Target2 not found")
    
# Fix train_incremental
target3 = """        train_dataset = ShadowDataset(self.db_path, seq_length=10, split='train', train_ratio=train_ratio, symbol=target_symbol)
        if len(train_dataset) < 40:"""
replacement3 = """        train_dataset = ShadowDataset(self.db_path, seq_length=getattr(self, 'seq_length', 10), split='train', train_ratio=train_ratio, symbol=target_symbol)
        if len(train_dataset) < 40:"""
        
# Actually, let's just use regex for train_incremental
content = re.sub(r'ShadowDataset\(self\.db_path, seq_length=10', r'ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10)', content)

# Also fix calculate_feature_importance
content = re.sub(r'ShadowDataset\(self\.db_path, seq_length=10, split=\'val\'', r'ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10), split=\'val\'', content)
# wait the previous regex already matched it if the signature starts the same.

with open("bot/learning/predictor.py", "w") as f:
    f.write(content)

print("Patching complete")
