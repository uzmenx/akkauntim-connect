import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

target3 = """        self.model.eval()
        with torch.no_grad():
            output = self.model(input_tensor)
            probs = torch.softmax(output, dim=1)[0].numpy()
            
        pred_idx = np.argmax(probs)
        confidence = probs[pred_idx] * 100
        
        mapping = {0: "HOLD", 1: "UP", 2: "DOWN"}
        
        state = self.model.get_network_state()
        self._export_network_state(state)"""

replacement3 = """        
        probs = None
        state = {}
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
            
        pred_idx = np.argmax(probs)
        confidence = probs[pred_idx] * 100
            
        mapping = {0: "HOLD", 1: "UP", 2: "DOWN"}
        
        self._export_network_state(state)"""

if target3 in content:
    content = content.replace(target3, replacement3)
else:
    print("Target 3 not found")

with open("bot/learning/predictor.py", "w") as f:
    f.write(content)

print("Patch applied for predict logic")
