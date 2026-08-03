import sys
import os
import sqlite3
import datetime
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
import random

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.predictor import ShadowDataset, MarketPredictorLSTM, TORCH_AVAILABLE

def set_seed(seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

def calculate_metrics(all_preds, all_targets):
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
    return val_acc, macro_f1

def evaluate_ensemble():
    if not TORCH_AVAILABLE:
        print("PyTorch is not installed")
        return

    db_path = "test_ensemble_search.db"
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
    for i in range(600):
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

    seq_len = 10
    train_dataset = ShadowDataset(db_path, seq_length=seq_len, split='train', train_ratio=0.8)
    val_dataset = ShadowDataset(db_path, seq_length=seq_len, split='val', train_ratio=0.8, scaler=train_dataset.scaler)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    train_dist = train_dataset.get_class_distribution()
    class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)

    epochs = 10

    print("================== SINGLE MODEL (Base) ==================")
    set_seed(42)
    single_model = MarketPredictorLSTM(input_size=12, hidden_size=64, num_layers=2, dropout=0.3, bidirectional=True)
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    optimizer = optim.Adam(single_model.parameters(), lr=0.001)

    for ep in range(epochs):
        single_model.train()
        for inputs, labels in train_loader:
            optimizer.zero_grad()
            outputs = single_model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

    single_model.eval()
    all_preds_single, all_targets_single = [], []
    with torch.no_grad():
        for inputs, labels in val_loader:
            outputs = single_model(inputs)
            preds = torch.argmax(outputs, dim=1)
            all_preds_single.extend(preds.tolist())
            all_targets_single.extend(labels.tolist())

    acc_single, f1_single = calculate_metrics(all_preds_single, all_targets_single)
    print(f"Single Model -> MacroF1: {f1_single:.2f}%, ValAcc: {acc_single:.2f}%")

    print("\n================== ENSEMBLE (3 smaller models) ==================")
    ensemble_size = 3
    models = []
    
    for i in range(ensemble_size):
        set_seed(42 + i * 100)
        # Using smaller hidden size to avoid over-parameterization for ensemble
        model = MarketPredictorLSTM(input_size=12, hidden_size=32, num_layers=2, dropout=0.3, bidirectional=True)
        opt = optim.Adam(model.parameters(), lr=0.001)
        
        for ep in range(epochs):
            model.train()
            for inputs, labels in train_loader:
                opt.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                opt.step()
        
        model.eval()
        models.append(model)
        
    all_preds_ensemble, all_targets_ensemble = [], []
    with torch.no_grad():
        for inputs, labels in val_loader:
            ensemble_outputs = torch.zeros(inputs.size(0), 3)
            for model in models:
                outputs = model(inputs)
                ensemble_outputs += torch.softmax(outputs, dim=1)
            
            ensemble_outputs /= ensemble_size
            preds = torch.argmax(ensemble_outputs, dim=1)
            all_preds_ensemble.extend(preds.tolist())
            all_targets_ensemble.extend(labels.tolist())

    acc_ensemble, f1_ensemble = calculate_metrics(all_preds_ensemble, all_targets_ensemble)
    print(f"Ensemble (3 models) -> MacroF1: {f1_ensemble:.2f}%, ValAcc: {acc_ensemble:.2f}%")
    
    print("\n================== SUMMARY ==================")
    print(f"Single Model   : F1={f1_single:.2f}%, Acc={acc_single:.2f}%")
    print(f"Ensemble (n=3) : F1={f1_ensemble:.2f}%, Acc={acc_ensemble:.2f}%")

    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    evaluate_ensemble()
