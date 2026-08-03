import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

target = """        class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        
        logger.info(f"LSTM tarmog'i o'rganishni boshladi (Symbol={target_symbol or 'GLOBAL'}, Train={len(train_dataset)}, Val={len(val_dataset)})...")"""

replacement = """        class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
        
        logger.info(f"LSTM tarmog'i o'rganishni boshladi (Symbol={target_symbol or 'GLOBAL'}, Train={len(train_dataset)}, Val={len(val_dataset)})...")"""

if target in content:
    content = content.replace(target, replacement)
else:
    print("Target 1 not found")

target2 = """                logger.info(
                    f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | "
                    f"Val Acc: {val_acc:.1f}% | Macro F1: {macro_f1:.1f}% | Recalls (HOLD/UP/DOWN): {recalls[0]:.0f}%/{recalls[1]:.0f}%/{recalls[2]:.0f}%"
                )
                
                if avg_val_loss < best_val_loss:"""

replacement2 = """                logger.info(
                    f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | "
                    f"Val Acc: {val_acc:.1f}% | Macro F1: {macro_f1:.1f}% | Recalls (HOLD/UP/DOWN): {recalls[0]:.0f}%/{recalls[1]:.0f}%/{recalls[2]:.0f}%"
                )
                
                scheduler.step(avg_val_loss)
                
                if avg_val_loss < best_val_loss:"""

if target2 in content:
    content = content.replace(target2, replacement2)
else:
    print("Target 2 not found")

with open("bot/learning/predictor.py", "w") as f:
    f.write(content)

print("Patch applied")
