import re

with open("bot/learning/predictor.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def train_incremental" in line:
        start_idx = i
        break

for i in range(start_idx, len(lines)):
    if "def optimize_architecture" in lines[i]:
        end_idx = i
        break

old_block = "".join(lines[start_idx:end_idx])

# We'll replace the old block with one that has early stopping.
# Let's extract everything inside train_incremental
target_loop_start = "        for epoch in range(epochs):"

if target_loop_start in old_block:
    # insert before loop
    new_loop_start = """        best_val_loss = float('inf')
        patience = 5
        patience_counter = 0
        best_model_state = None
        
        for epoch in range(epochs):"""
    old_block = old_block.replace(target_loop_start, new_loop_start)
    
    # After macro_f1 log, add the check
    log_end = """                )
            else:
                logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}")"""
                
    early_stop_logic = """                )
                
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    patience_counter = 0
                    import copy
                    best_model_state = copy.deepcopy(self.model.state_dict())
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        logger.info(f"Early stopping triggered at epoch {epoch+1}. Val loss {avg_val_loss:.4f} did not improve from {best_val_loss:.4f} for {patience} epochs.")
                        break
            else:
                logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}")"""
    
    old_block = old_block.replace(log_end, early_stop_logic)
    
    # At the end, load best state if we have it
    end_save = """        logger.info("O'qitish va Chronological Weighted Validation yakunlandi.")
        torch.save(self.model.state_dict(), self.model_path)
        self.is_trained = True"""
        
    new_end_save = """        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
            
        logger.info("O'qitish va Chronological Weighted Validation yakunlandi.")
        torch.save(self.model.state_dict(), self.model_path)
        self.is_trained = True"""
        
    old_block = old_block.replace(end_save, new_end_save)

with open("bot/learning/predictor.py", "w") as f:
    f.writelines(lines[:start_idx])
    f.write(old_block)
    f.writelines(lines[end_idx:])
    
print("Early stopping patched")
