import sys
import os
import sqlite3
import datetime
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.predictor import ShadowDataset, MarketPredictorLSTM, TORCH_AVAILABLE

def test_sequence_lengths():
    if not TORCH_AVAILABLE:
        print("PyTorch is not installed")
        return

    db_path = "test_seq_search.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE shadow_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            price_open REAL,
            price_high REAL,
            price_low REAL,
            price_close REAL,
            tick_volume REAL,
            smc_context TEXT,
            indicators TEXT,
            market_regime TEXT,
            ai_decision TEXT
        )
    ''')
    # Insert a sufficient amount of realistic candle rows
    base_price = 1.1000
    start_time = datetime.datetime(2026, 8, 1, 0, 0, 0)
    for i in range(500):
        ts = (start_time + datetime.timedelta(minutes=5 * i)).isoformat()
        open_p = base_price + (i % 4) * 0.0004
        high_p = open_p + 0.0012
        low_p = open_p - 0.0009
        close_p = open_p + (0.0006 if i % 2 == 0 else -0.0005)
        vol = 300 + i * 2
        decision = "UP" if i % 3 == 0 else ("DOWN" if i % 3 == 1 else "HOLD")
        cursor.execute('''
            INSERT INTO shadow_states 
            (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ts, "EURUSD", "M5", open_p, high_p, low_p, close_p, vol, "{}", "{}", "TRENDING", decision))
    conn.commit()
    conn.close()

    candidate_seq_lengths = [10, 15, 20, 30]
    candidate_bidirectional = [False, True]
    
    results = []

    for seq_len in candidate_seq_lengths:
        train_dataset = ShadowDataset(db_path, seq_length=seq_len, split='train', train_ratio=0.8)
        val_dataset = ShadowDataset(db_path, seq_length=seq_len, split='val', train_ratio=0.8, scaler=train_dataset.scaler)
        
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
        
        train_dist = train_dataset.get_class_distribution()
        class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)

        for is_bi in candidate_bidirectional:
            cand_model = MarketPredictorLSTM(input_size=12, hidden_size=64, num_layers=2, dropout=0.3, bidirectional=is_bi)
            criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
            optimizer = optim.Adam(cand_model.parameters(), lr=0.001)

            epochs = 5
            final_train_loss = 0.0
            for ep in range(epochs):
                cand_model.train()
                ep_train_loss = 0.0
                for inputs, labels in train_loader:
                    optimizer.zero_grad()
                    outputs = cand_model(inputs)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()
                    ep_train_loss += loss.item() * len(labels)
                final_train_loss = ep_train_loss / max(len(train_dataset), 1)

            cand_model.eval()
            val_loss = 0.0
            all_preds, all_targets = [], []
            with torch.no_grad():
                for inputs, labels in val_loader:
                    outputs = cand_model(inputs)
                    loss = criterion(outputs, labels)
                    val_loss += loss.item() * len(labels)
                    preds = torch.argmax(outputs, dim=1)
                    all_preds.extend(preds.tolist())
                    all_targets.extend(labels.tolist())

            avg_val_loss = val_loss / max(len(val_dataset), 1)
            val_total = max(len(all_targets), 1)
            val_correct = sum(1 for p, t in zip(all_preds, all_targets) if p == t)
            val_acc = (val_correct / val_total) * 100.0

            f1_scores = []
            for c in [0, 1, 2]:
                tp = sum(1 for p, t in zip(all_preds, all_targets) if p == c and t == c)
                fp = sum(1 for p, t in zip(all_preds, all_targets) if p == c and t != c)
                fn = sum(1 for p, t in zip(all_preds, all_targets) if p != c and t == c)
                prec = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
                rec = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
                f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
                f1_scores.append(f1)
            macro_f1 = (sum(f1_scores) / len(f1_scores)) * 100.0

            results.append({
                "seq_length": seq_len,
                "bidirectional": is_bi,
                "macro_f1": macro_f1,
                "val_acc": val_acc
            })
            print(f"SeqLen: {seq_len}, BiDir: {is_bi} => MacroF1: {macro_f1:.2f}%, ValAcc: {val_acc:.2f}%")

    if os.path.exists(db_path):
        os.remove(db_path)
        
    best = max(results, key=lambda x: x["macro_f1"])
    print("\n================== BEST CONFIG ==================")
    print(best)
    
if __name__ == "__main__":
    test_sequence_lengths()
