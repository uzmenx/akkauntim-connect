import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

target1 = """        class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
        
        logger.info(f"LSTM tarmog'i o'rganishni boshladi (Symbol={target_symbol or 'GLOBAL'}, Train={len(train_dataset)}, Val={len(val_dataset)})...")
        
        best_val_loss = float('inf')"""

replacement1 = """        class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
        
        import copy
        baseline_state = None
        baseline_val_loss = float('inf')
        
        if self.is_trained and val_loader:
            self.model.eval()
            b_loss = 0.0
            with torch.no_grad():
                for inputs, labels in val_loader:
                    outputs = self.model(inputs)
                    loss = criterion(outputs, labels)
                    b_loss += loss.item() * len(labels)
            baseline_val_loss = b_loss / max(len(val_dataset), 1)
            baseline_state = copy.deepcopy(self.model.state_dict())
            logger.info(f"Mavjud (old) model validation loss: {baseline_val_loss:.4f}")
            
        logger.info(f"LSTM tarmog'i o'rganishni boshladi (Symbol={target_symbol or 'GLOBAL'}, Train={len(train_dataset)}, Val={len(val_dataset)})...")
        
        best_val_loss = float('inf')"""

if target1 in content:
    content = content.replace(target1, replacement1)
else:
    print("Target 1 not found")


target2 = """        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
            
        logger.info("O'qitish va Chronological Weighted Validation yakunlandi.")
        torch.save(self.model.state_dict(), self.model_path)
        self.is_trained = True"""

replacement2 = """        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
            
        if baseline_state is not None and best_val_loss > baseline_val_loss:
            logger.warning(f"Diqqat: Yangi train yomonroq natija berdi ({best_val_loss:.4f} > {baseline_val_loss:.4f}). Model oldingi (baseline) holatiga qaytarilmoqda.")
            self.model.load_state_dict(baseline_state)
        else:
            if baseline_state is not None:
                logger.info(f"Model update tasdiqlandi: Val loss {baseline_val_loss:.4f} dan {best_val_loss:.4f} ga yaxshilandi.")
            else:
                logger.info("O'qitish va Chronological Weighted Validation yakunlandi.")
                
        torch.save(self.model.state_dict(), self.model_path)
        
        # Orqaga qaytish (rollback) imkoniyati uchun alohida backup nusxa saqlash
        backup_path = self.model_path.replace('.pth', '_best_backup.pth')
        torch.save(self.model.state_dict(), backup_path)
        
        self.is_trained = True"""

if target2 in content:
    content = content.replace(target2, replacement2)
else:
    print("Target 2 not found")

with open("bot/learning/predictor.py", "w") as f:
    f.write(content)

print("Patch applied")
