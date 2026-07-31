import os
import json
import logging
import sqlite3
import pandas as pd
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    from sklearn.preprocessing import StandardScaler
    import joblib
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch o'rnatilmagan! LSTM Predictor ishlamaydi. Iltimos, 'pip install torch scikit-learn' ni bajaring.")

logger = logging.getLogger(__name__)

class MarketPredictorLSTM(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self, input_size=12, hidden_size=64, num_layers=2, num_classes=3):
        super(MarketPredictorLSTM, self).__init__()
        if not TORCH_AVAILABLE:
            return
            
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        
        # O'rta qatlam (vizualizatsiya uchun faollikni olish oson)
        self.fc1 = nn.Linear(hidden_size, 32)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        
        # Chiqish (UP, DOWN, HOLD)
        self.fc2 = nn.Linear(32, num_classes)
        
        # Faolliklarni (activations) saqlash uchun hook
        self.last_activations = {}

    def forward(self, x):
        if not TORCH_AVAILABLE:
            return None
            
        # x shape: (batch, seq_len, input_size)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        
        # Faqat oxirgi vaqt qadamini olamiz
        out = out[:, -1, :]
        
        self.last_activations['lstm'] = out.detach().cpu().numpy()
        
        out = self.fc1(out)
        out = self.relu(out)
        self.last_activations['fc1'] = out.detach().cpu().numpy()
        
        out = self.dropout(out)
        out = self.fc2(out)
        
        self.last_activations['output'] = torch.softmax(out, dim=1).detach().cpu().numpy()
        
        return out

    def get_network_state(self) -> dict:
        """
        Frontend dagi "Tarmoq Vizualizatsiyasi" uchun tugunlar faolligini qaytaradi.
        """
        if not self.last_activations:
            return {"status": "empty"}
            
        return {
            "status": "active",
            "lstm_nodes": self.last_activations.get('lstm', np.array([])).flatten()[:32].tolist(),
            "hidden_nodes": self.last_activations.get('fc1', np.array([])).flatten()[:32].tolist(),
            "output_probabilities": self.last_activations.get('output', np.array([])).flatten().tolist()
        }


class ShadowDataset(Dataset if TORCH_AVAILABLE else object):
    """
    bot_learning.db dagi shadow_states jadvalidan ma'lumotlarni Pytorch uchun tayyorlash.
    """
    def __init__(self, db_path: str, seq_length=10):
        self.seq_length = seq_length
        self.data = []
        self.labels = []
        self.scaler = None
        
        if not TORCH_AVAILABLE:
            return
            
        self.scaler = StandardScaler()
        self._load_data(db_path)

    def _load_data(self, db_path):
        if not os.path.exists(db_path):
            logger.warning(f"{db_path} topilmadi. LSTM uchun ma'lumot yo'q.")
            return
            
        try:
            conn = sqlite3.connect(db_path)
            # Bizga eng kamida open, high, low, close, volume kerak
            query = "SELECT timestamp, price_open, price_high, price_low, price_close, tick_volume FROM shadow_states ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) < self.seq_length * 2:
                logger.info("Yetarli ma'lumot yo'q (LSTM o'qitish uchun).")
                return
                
            # Xususiyatlar (Features)
            features = df[['price_open', 'price_high', 'price_low', 'price_close', 'tick_volume']].values
            
            # Normalizatsiya
            features_scaled = self.scaler.fit_transform(features)
            
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            scaler_path = os.path.join(root_dir, 'bot', 'learning', 'lstm_scaler.joblib')
            import joblib
            joblib.dump(self.scaler, scaler_path)
            
            # Label (Bashorat) yaratish: 0=HOLD, 1=UP, 2=DOWN
            # Sodda misol: keyingi sham close'i hozirgi close'dan 5 pip (0.0005) yuqori bo'lsa UP
            # (Haqiqiy modelda SMC + Trend ham hisobga olinadi)
            closes = df['price_close'].values
            
            avg_price = np.mean(closes)
            # Use 0.02% of average price as threshold (works for all instruments)
            threshold = avg_price * 0.0002
            
            for i in range(len(features_scaled) - self.seq_length - 1):
                seq = features_scaled[i:i+self.seq_length]
                current_close = closes[i+self.seq_length - 1]
                next_close = closes[i+self.seq_length]
                
                diff = next_close - current_close
                if diff > threshold: # UP
                    label = 1
                elif diff < -threshold: # DOWN
                    label = 2
                else: # HOLD
                    label = 0
                    
                self.data.append(seq)
                self.labels.append(label)
                
        except Exception as e:
            logger.error(f"Shadow Dataset yuklashda xatolik: {e}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return torch.tensor(self.data[idx], dtype=torch.float32), torch.tensor(self.labels[idx], dtype=torch.long)


class PredictorEngine:
    def __init__(self, db_path: str = 'bot_learning.db'):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(root_dir, db_path)
        else:
            self.db_path = db_path
            
        self.model_path = os.path.join(root_dir, 'bot', 'learning', 'lstm_model.pth')
        self.model = MarketPredictorLSTM(input_size=5) if TORCH_AVAILABLE else None
        
        self.scaler_path = os.path.join(root_dir, 'bot', 'learning', 'lstm_scaler.joblib')
        self.scaler = None
        if os.path.exists(self.scaler_path):
            try:
                import joblib
                self.scaler = joblib.load(self.scaler_path)
            except Exception as e:
                logger.warning(f"Scaler yuklashda xatolik: {e}")
        
        self.is_trained = False
        if TORCH_AVAILABLE and os.path.exists(self.model_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, weights_only=True))
                self.is_trained = True
                logger.info("LSTM modeli muvaffaqiyatli yuklandi.")
            except Exception as e:
                logger.warning(f"LSTM modelini yuklashda xatolik: {e}")

    def train_incremental(self):
        """Yangi yig'ilgan shadow_states asosida modelni o'qitish."""
        if not TORCH_AVAILABLE or self.model is None:
            return
            
        dataset = ShadowDataset(self.db_path)
        self._save_scaler(dataset)
        if len(dataset) < 100:
            logger.info("O'qitish uchun dataset juda kichik (<100). Kutamiz...")
            return
            
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        
        self.model.train()
        total_loss = 0
        
        logger.info(f"LSTM tarmog'i o'rganishni boshladi (Data size: {len(dataset)})...")
        for epoch in range(5): # 5 epoxa (qisqa o'rganish)
            for inputs, labels in dataloader:
                optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                
        logger.info(f"O'qitish yakunlandi. Loss: {total_loss:.4f}")
        torch.save(self.model.state_dict(), self.model_path)
        self.is_trained = True

    def predict(self, recent_candles: list) -> dict:
        """
        Oxirgi shamlarni (masalan, 10 ta) olib, keyingi harakatni bashorat qilish.
        """
        if not TORCH_AVAILABLE or len(recent_candles) < 10:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}
            
        # recent_candles - bu dict'lar ro'yxati (open, high, low, close, tick_volume)
        features = [[c.get('open', 0), c.get('high', 0), c.get('low', 0), c.get('close', 0), c.get('tick_volume', 0)] for c in recent_candles[-10:]]
        
        features_np = np.array(features)
        if self.scaler is not None:
            features_scaled = self.scaler.transform(features_np)
        else:
            # Fallback to per-batch if no scaler saved yet
            mean = np.mean(features_np, axis=0)
            std = np.std(features_np, axis=0) + 1e-8
            features_scaled = (features_np - mean) / std
        
        input_tensor = torch.tensor(np.array([features_scaled]), dtype=torch.float32)
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(input_tensor)
            probs = torch.softmax(output, dim=1)[0].numpy()
            
        pred_idx = np.argmax(probs)
        confidence = probs[pred_idx] * 100
        
        mapping = {0: "HOLD", 1: "UP", 2: "DOWN"}
        
        state = self.model.get_network_state()
        self._export_network_state(state)
        
        return {
            "prediction": mapping[pred_idx],
            "confidence": round(float(confidence), 1),
            "network_state": state
        }

    def _export_network_state(self, state: dict):
        """Veb UI (ShadowLearningPage) o'qishi uchun tarmoq holatini public/network_state.json ga yozish"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            public_dir = os.path.join(root_dir, 'public')
            if not os.path.exists(public_dir):
                os.makedirs(public_dir, exist_ok=True)
                
            with open(os.path.join(public_dir, 'network_state.json'), 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.debug(f"Network state eksport qilishda xatolik: {e}")

    def _save_scaler(self, dataset):
        if dataset.scaler is not None:
            import joblib
            joblib.dump(dataset.scaler, self.scaler_path)
