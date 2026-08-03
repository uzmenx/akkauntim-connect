import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

target1 = """        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0
            for inputs, labels in train_loader:"""

replacement1 = """        # ENSEMBLE TRAINING LOGIC
        if self.use_ensemble:
            logger.info(f"Ensemble training boshlandi. Modellar soni: {self.ensemble_size}")
            self.ensemble_models = []
            import random
            
            # Agar mavjud modellar bo'lsa ularni o'chirib yangidan yaratamiz
            # Sababi: Har safar butunlay yangi kichik modellar to'plami train qilinishi barqarorroq
            
            ensemble_val_loss = 0.0
            
            for i in range(self.ensemble_size):
                torch.manual_seed(42 + i * 100); np.random.seed(42 + i * 100); random.seed(42 + i * 100)
                e_model = MarketPredictorLSTM(input_size=12, hidden_size=32, num_layers=2, dropout=0.3, bidirectional=getattr(self, "seq_length", 10) > 10)
                opt_e = optim.Adam(e_model.parameters(), lr=0.001)
                sched_e = optim.lr_scheduler.ReduceLROnPlateau(opt_e, mode='min', factor=0.5, patience=2)
                
                best_e_val = float('inf')
                best_e_state = None
                pat_counter = 0
                
                for ep in range(epochs):
                    e_model.train()
                    for inputs, labels in train_loader:
                        opt_e.zero_grad()
                        out = e_model(inputs)
                        loss = criterion(out, labels)
                        loss.backward()
                        opt_e.step()
                        
                    if val_loader:
                        e_model.eval()
                        v_loss = 0.0
                        with torch.no_grad():
                            for inputs, labels in val_loader:
                                v_loss += criterion(e_model(inputs), labels).item() * len(labels)
                        avg_v_loss = v_loss / max(len(val_dataset), 1)
                        sched_e.step(avg_v_loss)
                        
                        if avg_v_loss < best_e_val:
                            best_e_val = avg_v_loss
                            pat_counter = 0
                            best_e_state = copy.deepcopy(e_model.state_dict())
                        else:
                            pat_counter += 1
                            if pat_counter >= 5:
                                break
                
                if best_e_state:
                    e_model.load_state_dict(best_e_state)
                ensemble_val_loss += best_e_val
                
                self.ensemble_models.append(e_model)
                torch.save(e_model.state_dict(), self.model_path.replace('.pth', f'_ens_{i}.pth'))
                
            logger.info(f"Ensemble tayyor. O'rtacha model val loss: {ensemble_val_loss / self.ensemble_size:.4f}")
            self.is_trained = True
            return

        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0
            for inputs, labels in train_loader:"""

if target1 in content:
    content = content.replace(target1, replacement1)
else:
    print("Target 1 not found")

target2 = """        if not TORCH_AVAILABLE or self.model is None or len(recent_candles) < self.seq_length:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}"""

replacement2 = """        if not TORCH_AVAILABLE or len(recent_candles) < self.seq_length:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}
        if not self.use_ensemble and self.model is None:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}
        if self.use_ensemble and not self.ensemble_models:
            # Try to load ensemble models
            self.ensemble_models = []
            for i in range(self.ensemble_size):
                p = self.model_path.replace('.pth', f'_ens_{i}.pth')
                if os.path.exists(p):
                    m = MarketPredictorLSTM(input_size=12, hidden_size=32, num_layers=2, dropout=0.3, bidirectional=getattr(self, "seq_length", 10) > 10)
                    m.load_state_dict(torch.load(p, weights_only=True))
                    self.ensemble_models.append(m)
            if not self.ensemble_models:
                return {"prediction": "HOLD", "confidence": 0, "network_state": {}}"""

if target2 in content:
    content = content.replace(target2, replacement2)
else:
    print("Target 2 not found")

target3 = """        self.model.eval()
        with torch.no_grad():
            output = self.model(input_tensor)
            probs = torch.softmax(output, dim=1)[0].numpy()
            
            pred_idx = int(np.argmax(probs))
            
        mapping = {0: "HOLD", 1: "UP", 2: "DOWN"}
        
        state = self.model.get_network_state()
        self._export_network_state(state)"""

replacement3 = """        
        probs = None
        if self.use_ensemble and self.ensemble_models:
            ens_out = torch.zeros(1, 3)
            with torch.no_grad():
                for m in self.ensemble_models:
                    m.eval()
                    ens_out += torch.softmax(m(input_tensor), dim=1)
            ens_out /= len(self.ensemble_models)
            probs = ens_out[0].numpy()
            state = self.ensemble_models[0].get_network_state()
        else:
            self.model.eval()
            with torch.no_grad():
                output = self.model(input_tensor)
                probs = torch.softmax(output, dim=1)[0].numpy()
            state = self.model.get_network_state()
            
        pred_idx = int(np.argmax(probs))
            
        mapping = {0: "HOLD", 1: "UP", 2: "DOWN"}
        
        self._export_network_state(state)"""

if target3 in content:
    content = content.replace(target3, replacement3)
else:
    print("Target 3 not found")

with open("bot/learning/predictor.py", "w") as f:
    f.write(content)

print("Patch applied for ensemble logic")
