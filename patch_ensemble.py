import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

# 1. Update __init__ to include ensemble attributes
target_init = """        self.is_trained = False
        self.seq_length = 10
        self.config_path = os.path.join(root_dir, 'bot', 'learning', f'lstm_config{filename_suffix}.json')"""

replacement_init = """        self.is_trained = False
        self.seq_length = 10
        self.use_ensemble = True
        self.ensemble_size = 3
        self.ensemble_models = []
        self.config_path = os.path.join(root_dir, 'bot', 'learning', f'lstm_config{filename_suffix}.json')"""

if target_init in content:
    content = content.replace(target_init, replacement_init)
else:
    print("Init target not found")

# 2. Update evaluate_ensemble_approach method (we will add it before optimize_architecture)
target_eval = """    def optimize_architecture("""

replacement_eval = """    def evaluate_ensemble_approach(self, train_ratio: float = 0.8, epochs: int = 5, symbol: Optional[str] = None) -> dict:
        \"\"\"
        Ensemble yondashuvini izchil backtest bilan o'lchash:
        1 ta yirik model va 3 ta kichik model (turli seed) bilan o'qitilib,
        Validation dataset da Macro F1 va Accuracy natijalarini solishtiradi.
        \"\"\"
        if not TORCH_AVAILABLE:
            return {"status": "error", "message": "PyTorch unavailable"}
            
        target_symbol = symbol or self.symbol
        train_dataset = ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10), split='train', train_ratio=train_ratio, symbol=target_symbol)
        
        if len(train_dataset) < 40:
            return {"status": "error", "message": "Ma'lumot yetarli emas"}
            
        val_dataset = ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10), split='val', train_ratio=train_ratio, scaler=train_dataset.scaler, symbol=target_symbol)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
        
        train_dist = train_dataset.get_class_distribution()
        class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        
        # 1. Single Model Training
        import random
        torch.manual_seed(42); np.random.seed(42); random.seed(42)
        single_model = MarketPredictorLSTM(input_size=12, hidden_size=64, num_layers=2, dropout=0.3, bidirectional=getattr(self, "seq_length", 10) > 10)
        optimizer_s = optim.Adam(single_model.parameters(), lr=0.001)
        for ep in range(epochs):
            single_model.train()
            for inputs, labels in train_loader:
                optimizer_s.zero_grad()
                out = single_model(inputs)
                loss = criterion(out, labels)
                loss.backward()
                optimizer_s.step()
                
        single_model.eval()
        s_preds, s_targets = [], []
        with torch.no_grad():
            for inputs, labels in val_loader:
                out = single_model(inputs)
                s_preds.extend(torch.argmax(out, dim=1).tolist())
                s_targets.extend(labels.tolist())
                
        s_acc = sum(1 for p, t in zip(s_preds, s_targets) if p == t) / max(len(s_targets), 1) * 100.0
        
        # 2. Ensemble Training
        ensemble_models = []
        for i in range(self.ensemble_size):
            torch.manual_seed(42 + i * 100); np.random.seed(42 + i * 100); random.seed(42 + i * 100)
            e_model = MarketPredictorLSTM(input_size=12, hidden_size=32, num_layers=1, dropout=0.3, bidirectional=getattr(self, "seq_length", 10) > 10)
            opt_e = optim.Adam(e_model.parameters(), lr=0.001)
            for ep in range(epochs):
                e_model.train()
                for inputs, labels in train_loader:
                    opt_e.zero_grad()
                    out = e_model(inputs)
                    loss = criterion(out, labels)
                    loss.backward()
                    opt_e.step()
            e_model.eval()
            ensemble_models.append(e_model)
            
        e_preds, e_targets = [], []
        with torch.no_grad():
            for inputs, labels in val_loader:
                ens_out = torch.zeros(inputs.size(0), 3)
                for m in ensemble_models:
                    ens_out += torch.softmax(m(inputs), dim=1)
                ens_out /= self.ensemble_size
                e_preds.extend(torch.argmax(ens_out, dim=1).tolist())
                e_targets.extend(labels.tolist())
                
        e_acc = sum(1 for p, t in zip(e_preds, e_targets) if p == t) / max(len(e_targets), 1) * 100.0
        
        def calc_f1(preds, tgts):
            f1s = []
            for c in [0, 1, 2]:
                tp = sum(1 for p, t in zip(preds, tgts) if p == c and t == c)
                fp = sum(1 for p, t in zip(preds, tgts) if p == c and t != c)
                fn = sum(1 for p, t in zip(preds, tgts) if p != c and t == c)
                pr = tp/(tp+fp) if (tp+fp)>0 else 0.0
                re = tp/(tp+fn) if (tp+fn)>0 else 0.0
                f1s.append(2*pr*re/(pr+re) if (pr+re)>0 else 0.0)
            return (sum(f1s)/3.0)*100.0
            
        s_f1 = calc_f1(s_preds, s_targets)
        e_f1 = calc_f1(e_preds, e_targets)
        
        logger.info(f"Ensemble Backtest -> Single: {s_f1:.2f}% F1, {s_acc:.2f}% Acc | Ensemble: {e_f1:.2f}% F1, {e_acc:.2f}% Acc")
        
        return {
            "single": {"macro_f1": s_f1, "accuracy": s_acc},
            "ensemble": {"macro_f1": e_f1, "accuracy": e_acc},
            "verdict": "ENSEMBLE_BETTER" if e_f1 > s_f1 else "SINGLE_BETTER"
        }

    def optimize_architecture("""

if target_eval in content:
    content = content.replace(target_eval, replacement_eval)
else:
    print("Eval target not found")

with open("bot/learning/predictor.py", "w") as f:
    f.write(content)

print("Patch applied for init and eval")
