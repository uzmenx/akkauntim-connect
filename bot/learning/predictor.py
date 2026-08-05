import os
import json
import logging
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

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

from bot.learning.features import compute_12_features, sanitize_market_dataframe, InstitutionalFeatureScaler



class TemporalCandleAttention(nn.Module if TORCH_AVAILABLE else object):
    """
    Temporal Candle Attention module over LSTM sequential outputs.
    Calculates dynamic scalar attention score alpha_t for each candle in the lookback sequence:
    e_t = tanh(W_attn * h_t) * v_attn
    alpha_t = softmax(e_t)
    context = sum(alpha_t * h_t)
    """
    def __init__(self, hidden_size: int):
        super(TemporalCandleAttention, self).__init__()
        if not TORCH_AVAILABLE:
            return
        self.attn_linear = nn.Linear(hidden_size, hidden_size)
        self.v_attn = nn.Linear(hidden_size, 1, bias=False)
        self.tanh = nn.Tanh()

    def forward(self, lstm_out):
        # lstm_out shape: (batch_size, seq_len, hidden_size)
        u = self.tanh(self.attn_linear(lstm_out))  # (batch_size, seq_len, hidden_size)
        scores = self.v_attn(u)  # (batch_size, seq_len, 1)
        weights = torch.softmax(scores, dim=1)  # (batch_size, seq_len, 1)
        context = torch.sum(weights * lstm_out, dim=1)  # (batch_size, hidden_size)
        return context, weights


class MarketPredictorLSTM(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self, input_size=12, hidden_size=64, num_layers=2, num_classes=3, dropout=0.3, use_attention=False, bidirectional=False):
        super(MarketPredictorLSTM, self).__init__()
        if not TORCH_AVAILABLE:
            return
            
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout_rate = dropout
        self.use_attention = use_attention
        self.bidirectional = bidirectional
        
        lstm_dropout = dropout if num_layers > 1 else 0.0
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=lstm_dropout, bidirectional=bidirectional)
        
        lstm_out_size = hidden_size * 2 if bidirectional else hidden_size
        if self.use_attention:
            self.attention = TemporalCandleAttention(lstm_out_size)
        else:
            self.attention = None
        
        # O'rta qatlam (vizualizatsiya uchun faollikni olish oson)
        self.fc1 = nn.Linear(lstm_out_size, 32)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        
        # Chiqish (UP, DOWN, HOLD)
        self.fc2 = nn.Linear(32, num_classes)
        
        # Faolliklarni (activations) saqlash uchun hook
        self.last_activations = {}
        self.last_attention_weights = None

    def forward(self, x):
        if not TORCH_AVAILABLE:
            return None
            
        # x shape: (batch, seq_len, input_size)
        num_dirs = 2 if self.bidirectional else 1
        h0 = torch.zeros(self.num_layers * num_dirs, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers * num_dirs, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0)) # (batch, seq_len, hidden_size * num_dirs)
        
        if self.use_attention and self.attention is not None:
            context, weights = self.attention(out)
            out = context
            self.last_attention_weights = weights.detach().cpu().numpy()
            self.last_activations['attention_weights'] = self.last_attention_weights
        else:
            out = out[:, -1, :]
            self.last_attention_weights = None
        
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
            
        res = {
            "status": "active",
            "use_attention": self.use_attention,
            "lstm_nodes": self.last_activations.get('lstm', np.array([])).flatten()[:32].tolist(),
            "hidden_nodes": self.last_activations.get('fc1', np.array([])).flatten()[:32].tolist(),
            "output_probabilities": self.last_activations.get('output', np.array([])).flatten().tolist()
        }
        if self.use_attention and 'attention_weights' in self.last_activations:
            raw_w = self.last_activations['attention_weights']
            w_flat = np.squeeze(raw_w).tolist()
            if isinstance(w_flat, (float, int)):
                w_flat = [float(w_flat)]
            res["attention_weights"] = w_flat
        return res


class ShadowDataset(Dataset if TORCH_AVAILABLE else object):
    """
    bot_learning.db dagi shadow_states jadvalidan ma'lumotlarni PyTorch uchun tayyorlash.
    Qat'iy vaqt bo'yicha (chronological) Train va Validation bo'linishi.
    Look-ahead bias va data leakage oldini oladi.
    """
    def __init__(self, db_path: str, seq_length: int = 10, split: str = 'train', train_ratio: float = 0.8, scaler: InstitutionalFeatureScaler = None, symbol: Optional[str] = None):
        self.seq_length = seq_length
        self.split = split
        self.train_ratio = train_ratio
        self.symbol = symbol
        self.data = []
        self.labels = []
        self.timestamps = []
        self.scaler = scaler
        
        if not TORCH_AVAILABLE:
            return
            
        self._load_data(db_path)

    def _load_data(self, db_path: str):
        if not os.path.exists(db_path):
            logger.warning(f"{db_path} topilmadi. LSTM uchun ma'lumot yo'q.")
            return
            
        try:
            conn = sqlite3.connect(db_path)
            # Qat'iy vaqt tartibida o'qish (Chronological order) hamda ixtiyoriy symbol süzgichi
            if self.symbol:
                query = "SELECT timestamp, price_open, price_high, price_low, price_close, tick_volume FROM shadow_states WHERE symbol = ? ORDER BY timestamp ASC"
                df = pd.read_sql_query(query, conn, params=(self.symbol,))
            else:
                query = "SELECT timestamp, price_open, price_high, price_low, price_close, tick_volume FROM shadow_states ORDER BY timestamp ASC"
                df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Institutional data sanitization: filter out NULL, zero, corrupt, flat dead bars
            df = sanitize_market_dataframe(df)
            
            if len(df) < self.seq_length * 2:
                logger.info("Yetarli toza ma'lumot yo'q (LSTM o'qitish uchun).")
                return
                
            # 12 ta xususiyatni hisoblaymiz
            features = compute_12_features(df)
            total_candles = len(features)
            total_seqs = total_candles - self.seq_length
            if total_seqs <= 0:
                return

            # Vaqt bo'yicha ajratish indeksi (Chronological split index)
            split_idx = int(total_seqs * self.train_ratio)
            
            # Scaler look-ahead bias berishining oldini olish uchun:
            # Scaler faqat o'tmishdagi Train oynasi ma'lumotlarida fit qilinadi!
            if self.scaler is None:
                self.scaler = InstitutionalFeatureScaler()
                train_feature_boundary = max(split_idx + self.seq_length, self.seq_length)
                self.scaler.fit(features[:train_feature_boundary])
            
            # Ma'lumotlarni normalizatsiya qilish
            features_scaled = self.scaler.transform(features)
            
            closes = df['price_close'].values
            timestamps = df['time'].values if 'time' in df.columns else np.arange(len(df))
            
            # Ehtiyotkorlik bilan dinamik threshold hisoblash
            train_closes = closes[:split_idx + self.seq_length] if split_idx > 0 else closes
            avg_price = np.mean(train_closes) if len(train_closes) > 0 else np.mean(closes)
            threshold = avg_price * 0.0002
            
            if self.split == 'train':
                start_i = 0
                end_i = split_idx
            elif self.split == 'val':
                start_i = split_idx
                end_i = total_seqs
            else: # 'all'
                start_i = 0
                end_i = total_seqs

            for i in range(start_i, end_i):
                seq = features_scaled[i : i + self.seq_length]
                current_close = closes[i + self.seq_length - 1]
                next_close = closes[i + self.seq_length]
                
                diff = next_close - current_close
                if diff > threshold: # UP
                    label = 1
                elif diff < -threshold: # DOWN
                    label = 2
                else: # HOLD
                    label = 0
                    
                self.data.append(seq)
                self.labels.append(label)
                self.timestamps.append(timestamps[i + self.seq_length])
                
        except Exception as e:
            logger.error(f"Shadow Dataset yuklashda xatolik: {e}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return torch.tensor(self.data[idx], dtype=torch.float32), torch.tensor(self.labels[idx], dtype=torch.long)

    def get_class_distribution(self) -> Dict[str, Any]:
        """
        Class imbalance analizi: counts, percentages, imbalance_ratio, va inverse class weights.
        Classes: 0: HOLD, 1: UP, 2: DOWN
        """
        total = len(self.labels)
        if total == 0:
            return {
                "total": 0,
                "counts": {0: 0, 1: 0, 2: 0},
                "percentages": {0: 0.0, 1: 0.0, 2: 0.0},
                "imbalance_ratio": 1.0,
                "has_critical_imbalance": False,
                "class_weights": [1.0, 1.0, 1.0]
            }

        counts = {
            0: self.labels.count(0),
            1: self.labels.count(1),
            2: self.labels.count(2)
        }
        percentages = {c: (counts[c] / total) * 100.0 for c in [0, 1, 2]}
        
        max_cnt = max(counts.values())
        min_cnt = min([c for c in counts.values() if c > 0] or [1])
        imbalance_ratio = float(max_cnt) / float(min_cnt) if min_cnt > 0 else 1.0
        
        has_critical_imbalance = (percentages[0] >= 75.0) or (imbalance_ratio >= 3.5)
        
        # Smooth inverse class weighting: w_c = N / (C * N_c)
        num_classes = 3
        class_weights = []
        for c in [0, 1, 2]:
            cnt = counts[c]
            if cnt > 0:
                w = total / (float(num_classes) * float(cnt))
            else:
                w = 1.0
            class_weights.append(float(w))

        # Normalize weights so mean is 1.0
        mean_w = sum(class_weights) / len(class_weights)
        if mean_w > 0:
            class_weights = [w / mean_w for w in class_weights]

        return {
            "total": total,
            "counts": counts,
            "percentages": percentages,
            "imbalance_ratio": round(imbalance_ratio, 2),
            "has_critical_imbalance": has_critical_imbalance,
            "class_weights": class_weights
        }


class PredictorEngine:
    def __init__(self, db_path: str = 'bot_learning.db', symbol: Optional[str] = None):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(root_dir, db_path)
        else:
            self.db_path = db_path
            
        self.symbol = symbol
        filename_suffix = f"_{symbol}" if symbol else ""
        self.model_path = os.path.join(root_dir, 'bot', 'learning', f'lstm_model{filename_suffix}.pth')
        # Explicit 12 input features alignment
        self.model = MarketPredictorLSTM(input_size=12) if TORCH_AVAILABLE else None
        
        self.scaler_path = os.path.join(root_dir, 'bot', 'learning', f'lstm_scaler{filename_suffix}.joblib')
        self.scaler = None
        if os.path.exists(self.scaler_path):
            try:
                import joblib
                scaler_obj = joblib.load(self.scaler_path)
                if hasattr(scaler_obj, 'n_features_in_') and scaler_obj.n_features_in_ == 12:
                    self.scaler = scaler_obj
                else:
                    logger.warning("Mavjud scaler 12 ta feature'ga mos kelmadi. Yangi InstitutionalFeatureScaler yaratiladi.")
                    self.scaler = InstitutionalFeatureScaler()
            except Exception as e:
                logger.warning(f"Scaler yuklashda xatolik: {e}")
                self.scaler = InstitutionalFeatureScaler()
        else:
            self.scaler = InstitutionalFeatureScaler()
        
        self.is_trained = False
        self.seq_length = 10
        self.use_ensemble = True
        self.ensemble_size = 3
        self.ensemble_models = []
        self.config_path = os.path.join(root_dir, 'bot', 'learning', f'lstm_config{filename_suffix}.json')
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    conf = json.load(f)
                    self.seq_length = conf.get("seq_length", 10)
            except Exception as e:
                logger.warning(f"Config o'qishda xatolik: {e}")

        if TORCH_AVAILABLE and os.path.exists(self.model_path):
            try:
                state_dict = torch.load(self.model_path, weights_only=True)
                if 'lstm.weight_ih_l0' in state_dict:
                    saved_input_size = state_dict['lstm.weight_ih_l0'].shape[1]
                    saved_hidden_size = state_dict['lstm.weight_ih_l0'].shape[0] // 4
                    layer_count = 0
                    while f'lstm.weight_ih_l{layer_count}' in state_dict:
                        layer_count += 1
                        
                    has_attention = any(k.startswith('attention.') for k in state_dict.keys())
                    is_bidirectional = 'lstm.weight_ih_l0_reverse' in state_dict
                        
                    if saved_input_size != 12:
                        logger.warning(f"Mavjud model input size ({saved_input_size}) 12 ga mos kelmadi. Model 12 input_size bilan qayta yaratiladi.")
                        state_dict = None
                    else:
                        self.model = MarketPredictorLSTM(
                            input_size=12,
                            hidden_size=saved_hidden_size,
                            num_layers=max(1, layer_count),
                            dropout=0.3,
                            use_attention=has_attention,
                            bidirectional=is_bidirectional
                        )
                    
                if state_dict is not None:
                    self.model.load_state_dict(state_dict)
                    self.is_trained = True
                    logger.info(
                        f"LSTM modeli (input_size=12, hidden_size={self.model.hidden_size}, "
                        f"num_layers={self.model.num_layers}, attention={self.model.use_attention}, "
                        f"bidirectional={getattr(self.model, 'bidirectional', False)}, "
                        f"symbol={symbol or 'GLOBAL'}) muvaffaqiyatli yuklandi."
                    )
            except Exception as e:
                logger.warning(f"LSTM modelini yuklashda xatolik: {e}")
                
    def evaluate_attention_readiness(self, db_path: str = None, min_samples: int = 150) -> dict:
        """
        Stage 2 Data Readiness Check for Temporal Attention Mechanism:
        Ensures sample size, class distribution, and feature quality are sufficient
        for learning temporal candle importance weights without overfitting.
        """
        target_db = db_path or self.db_path
        if not os.path.exists(target_db):
            return {
                "stage2_ready": False,
                "total_samples": 0,
                "min_samples_threshold": min_samples,
                "recommendation": "USE_STANDARD_LSTM_FALLBACK",
                "reason": f"Database fayli topilmadi: {target_db}"
            }

        try:
            conn = sqlite3.connect(target_db)
            query = "SELECT ai_decision, price_open, price_high, price_low, price_close, tick_volume FROM shadow_states"
            if self.symbol:
                query += f" WHERE symbol = '{self.symbol}'"
            df = pd.read_sql_query(query, conn)
            conn.close()

            total_samples = len(df)
            if total_samples < min_samples:
                return {
                    "stage2_ready": False,
                    "total_samples": total_samples,
                    "min_samples_threshold": min_samples,
                    "recommendation": "USE_STANDARD_LSTM_FALLBACK",
                    "reason": f"Yetarli namunalar mavjud emas: {total_samples}/{min_samples} (Stage 2 uchun kamida {min_samples} ta kerak)."
                }

            decisions = df['ai_decision'].fillna('HOLD').astype(str).tolist()
            counts = {
                "HOLD": sum(1 for d in decisions if d in ['HOLD', '0']),
                "UP": sum(1 for d in decisions if d in ['UP', 'BUY', '1']),
                "DOWN": sum(1 for d in decisions if d in ['DOWN', 'SELL', '2'])
            }
            valid_classes = [cat for cat, cnt in counts.items() if cnt > 0]
            min_class_pct = min(counts.values()) / max(total_samples, 1) if total_samples > 0 else 0
            has_balanced_classes = len(valid_classes) >= 2 and min_class_pct >= 0.05

            has_nan = df[['price_open', 'price_high', 'price_low', 'price_close', 'tick_volume']].isna().any().any()
            std_sum = df[['price_open', 'price_high', 'price_low', 'price_close', 'tick_volume']].std().sum()
            has_clean_features = not has_nan and std_sum > 0.00001

            stage2_ready = (total_samples >= min_samples) and has_balanced_classes and has_clean_features

            reason = (
                "Stage 2 ma'lumotlar sifati va hajmi etarli. Temporal Attention aktivlashtirildi."
                if stage2_ready
                else f"Ma'lumotlar yetarli emas yoki muvozanatsiz (Samples: {total_samples}, Min class share: {min_class_pct*100:.1f}%)."
            )

            return {
                "stage2_ready": stage2_ready,
                "total_samples": total_samples,
                "min_samples_threshold": min_samples,
                "class_counts": counts,
                "has_balanced_classes": has_balanced_classes,
                "has_clean_features": has_clean_features,
                "recommendation": "ENABLE_TEMPORAL_ATTENTION" if stage2_ready else "USE_STANDARD_LSTM_FALLBACK",
                "reason": reason
            }
        except Exception as e:
            logger.warning(f"evaluate_attention_readiness xatosi: {e}")
            return {
                "stage2_ready": False,
                "total_samples": 0,
                "min_samples_threshold": min_samples,
                "recommendation": "USE_STANDARD_LSTM_FALLBACK",
                "reason": f"Tahlil bajarishda xatolik: {str(e)}"
            }

    def train_incremental(self, train_ratio: float = 0.8, epochs: int = 5, symbol: Optional[str] = None, force_attention: Optional[bool] = None):
        """
        Yangi yig'ilgan shadow_states asosida modelni o'qitish.
        Qat'iy vaqt bo'yicha (chronological) Train/Validation bo'linishi.
        Stage 2 ma'lumot tayyorgarligi tekshirilib, mos ravishda Temporal Attention aktivlashtiriladi.
        Class imbalance'ni inobatga olgan holda Inverse Class Frequency Weighting ishlatadi.
        """
        if not TORCH_AVAILABLE or self.model is None:
            return
            
        target_symbol = symbol or self.symbol
        
        # Stage 2 Attention Readiness evaluation
        readiness = self.evaluate_attention_readiness(min_samples=80)
        use_attention = readiness["stage2_ready"] if force_attention is None else force_attention
        
        if getattr(self.model, "use_attention", False) != use_attention:
            logger.info(f"Model attention sozlamasi yangilandi (use_attention={use_attention}). Model qayta konfiguratsiya qilinmoqda.")
            self.model = MarketPredictorLSTM(
                input_size=12,
                hidden_size=self.model.hidden_size,
                num_layers=self.model.num_layers,
                dropout=self.model.dropout_rate,
                use_attention=use_attention
            )

        train_dataset = ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10), split='train', train_ratio=train_ratio, symbol=target_symbol)
        if len(train_dataset) < 80:
            logger.info(f"O'qitish uchun dataset juda kichik (<80, symbol={target_symbol or 'GLOBAL'}). Kutamiz...")
            return
            
        self.scaler = train_dataset.scaler
        self._save_scaler(train_dataset)
        
        train_dist = train_dataset.get_class_distribution()
        logger.info(
            f"Class Distribution [Train - {target_symbol or 'GLOBAL'}] Total={train_dist['total']} | "
            f"HOLD (0): {train_dist['counts'][0]} ({train_dist['percentages'][0]:.1f}%), "
            f"UP (1): {train_dist['counts'][1]} ({train_dist['percentages'][1]:.1f}%), "
            f"DOWN (2): {train_dist['counts'][2]} ({train_dist['percentages'][2]:.1f}%)"
        )
        if train_dist["has_critical_imbalance"]:
            logger.warning(
                f"CRITICAL CLASS IMBALANCE DETECTED (Ratio: {train_dist['imbalance_ratio']}x). "
                f"Applying Weighted CrossEntropyLoss with weights: {train_dist['class_weights']}"
            )

        val_dataset = ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10), split='val', train_ratio=train_ratio, scaler=self.scaler, symbol=target_symbol)
        
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False) if len(val_dataset) > 0 else None
        
        class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)
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
        
        best_val_loss = float('inf')
        patience = 5
        patience_counter = 0
        best_model_state = None
        
        # ENSEMBLE TRAINING LOGIC
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
            for inputs, labels in train_loader:
                optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * len(labels)
                
            avg_train_loss = train_loss / max(len(train_dataset), 1)
            
            if val_loader:
                self.model.eval()
                val_loss = 0.0
                all_preds = []
                all_targets = []
                with torch.no_grad():
                    for inputs, labels in val_loader:
                        outputs = self.model(inputs)
                        loss = criterion(outputs, labels)
                        val_loss += loss.item() * len(labels)
                        preds = torch.argmax(outputs, dim=1)
                        all_preds.extend(preds.tolist())
                        all_targets.extend(labels.tolist())

                avg_val_loss = val_loss / max(len(val_dataset), 1)
                
                # Evaluation Metrics: Accuracy, Precision, Recall, Macro F1
                val_total = max(len(all_targets), 1)
                val_correct = sum(1 for p, t in zip(all_preds, all_targets) if p == t)
                val_acc = (val_correct / val_total) * 100.0

                f1_scores = []
                recalls = []
                for c in [0, 1, 2]:
                    tp = sum(1 for p, t in zip(all_preds, all_targets) if p == c and t == c)
                    fp = sum(1 for p, t in zip(all_preds, all_targets) if p == c and t != c)
                    fn = sum(1 for p, t in zip(all_preds, all_targets) if p != c and t == c)
                    
                    prec = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
                    rec = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
                    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
                    f1_scores.append(f1)
                    recalls.append(rec * 100.0)

                macro_f1 = (sum(f1_scores) / len(f1_scores)) * 100.0
                logger.info(
                    f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | "
                    f"Val Acc: {val_acc:.1f}% | Macro F1: {macro_f1:.1f}% | Recalls (HOLD/UP/DOWN): {recalls[0]:.0f}%/{recalls[1]:.0f}%/{recalls[2]:.0f}%"
                )
                
                scheduler.step(avg_val_loss)
                
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
                logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}")
                
        if best_model_state is not None:
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
        
        self.is_trained = True

    def evaluate_ensemble_approach(self, train_ratio: float = 0.8, epochs: int = 5, symbol: Optional[str] = None) -> dict:
        """
        Ensemble yondashuvini izchil backtest bilan o'lchash:
        1 ta yirik model va 3 ta kichik model (turli seed) bilan o'qitilib,
        Validation dataset da Macro F1 va Accuracy natijalarini solishtiradi.
        """
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

    def optimize_architecture(
        self,
        candidate_hidden_sizes: List[int] = [32, 64, 128, 256],
        candidate_num_layers: List[int] = [1, 2],
        candidate_dropouts: List[float] = [0.2, 0.3, 0.4],
        candidate_seq_lengths: List[int] = [10, 15, 20, 30],
        candidate_bidirectional: List[bool] = [False, True],
        train_ratio: float = 0.8,
        epochs: int = 5,
        symbol: Optional[str] = None
    ) -> dict:
        """
        Hyperparameter Search / Architecture & Regularization Optimization:
        hidden_size, num_layers hamda dropout (0.2, 0.3, 0.4) kombinatsiyalarini o'qitib,
        validation loss, validation macro F1 va overfitting ko'rsatkichini (val_loss vs train_loss gap) solishtiradi.
        Kichik datasetlarda overfitting'ni kamaytiradigan eng yaxshi generalization beruvchi optimal modelni tanlaydi.
        """
        if not TORCH_AVAILABLE:
            return {"status": "error", "message": "PyTorch vertical unavailable"}

        target_symbol = symbol or self.symbol
        
        trials = []
        best_score = -999.0
        best_config = {"hidden_size": 64, "num_layers": 2, "dropout": 0.3, "seq_length": 10, "bidirectional": False}
        best_dataset = None
        
        for seq_len in candidate_seq_lengths:
            train_dataset = ShadowDataset(self.db_path, seq_length=seq_len, split='train', train_ratio=train_ratio, symbol=target_symbol)
            if len(train_dataset) < 80:
                continue
                
            val_dataset = ShadowDataset(self.db_path, seq_length=seq_len, split='val', train_ratio=train_ratio, scaler=train_dataset.scaler, symbol=target_symbol)
            if len(val_dataset) == 0:
                continue

            train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

            train_dist = train_dataset.get_class_distribution()
            class_weights_tensor = torch.tensor(train_dist["class_weights"], dtype=torch.float32)

            for h in candidate_hidden_sizes:
                for l in candidate_num_layers:
                    for dr in candidate_dropouts:
                        for is_bi in candidate_bidirectional:
                            cand_model = MarketPredictorLSTM(input_size=12, hidden_size=h, num_layers=l, dropout=dr, bidirectional=is_bi)
                            criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
                            optimizer = optim.Adam(cand_model.parameters(), lr=0.001)

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

                    loss_gap = avg_val_loss - final_train_loss
                    if loss_gap > 0.20 or (final_train_loss > 0 and avg_val_loss / final_train_loss > 1.4):
                        overfit_status = "HIGH_OVERFITTING_RISK"
                        overfit_penalty = 15.0
                    elif loss_gap > 0.08:
                        overfit_status = "MODERATE_OVERFITTING"
                        overfit_penalty = 5.0
                    else:
                        overfit_status = "STABLE_GENERALIZATION"
                        overfit_penalty = 0.0

                    selection_score = macro_f1 - overfit_penalty

                    trial_res = {
                        "seq_length": seq_len,
                        "bidirectional": is_bi,
                        "hidden_size": h,
                        "num_layers": l,
                        "dropout": dr,
                        "train_loss": round(final_train_loss, 4),
                        "val_loss": round(avg_val_loss, 4),
                        "loss_gap": round(loss_gap, 4),
                        "val_accuracy": round(val_acc, 2),
                        "val_macro_f1": round(macro_f1, 2),
                        "overfit_status": overfit_status,
                        "selection_score": round(selection_score, 2)
                    }
                    trials.append(trial_res)

                    if selection_score > best_score:
                        best_score = selection_score
                        best_config = {"hidden_size": h, "num_layers": l, "dropout": dr, "seq_length": seq_len, "bidirectional": is_bi}
                        best_dataset = train_dataset

        if best_dataset is None:
            return {"status": "error", "message": "No valid model configurations evaluated."}

        logger.info(
            f"Hyperparameter Search Yakunlandi ({target_symbol or 'GLOBAL'}). "
            f"Tanlangan Optimal Model: {best_config}"
        )

        self.model = MarketPredictorLSTM(
            input_size=12,
            hidden_size=best_config["hidden_size"],
            num_layers=best_config["num_layers"],
            dropout=best_config["dropout"],
            bidirectional=best_config["bidirectional"]
        )
        self.scaler = best_dataset.scaler
        self._save_scaler(best_dataset)
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump({"seq_length": best_config['seq_length'], "bidirectional": best_config['bidirectional']}, f)
            self.seq_length = best_config['seq_length']
        except Exception as e:
            logger.warning(f"Config saqlashda xatolik: {e}")

        self.train_incremental(train_ratio=train_ratio, epochs=epochs, symbol=target_symbol)

        return {
            "symbol": target_symbol or "GLOBAL",
            "best_config": best_config,
            "trials": trials,
            "summary": f"Optimal seq_len={best_config['seq_length']}, bi={best_config['bidirectional']}, hidden_size={best_config['hidden_size']}, num_layers={best_config['num_layers']}, dropout={best_config['dropout']} tanlandi (Val Macro F1 max va overfitting kamaytirildi)."
        }

    def evaluate_multi_symbol_strategy(self, db_path: str = None) -> dict:
        """
        Forex juftliklari (EURUSD, GBPUSD, AUDUSD va h.k.) bo'yicha ma'lumotlar statistikasini tahlil qilish:
        1) Har bir juftlikning narx shkalasi va volatilligini taqqoslash.
        2) Per-symbol model yoki unified global model tanlash bo'yicha qaror chiqarish.
        """
        target_db = db_path or self.db_path
        if not os.path.exists(target_db):
            return {"error": "Database not found", "recommendation": "USE_GLOBAL_MODEL"}

        try:
            conn = sqlite3.connect(target_db)
            df = pd.read_sql_query("SELECT symbol, price_open, price_high, price_low, price_close, tick_volume FROM shadow_states", conn)
            conn.close()

            if df.empty or 'symbol' not in df.columns:
                return {"symbols": [], "recommendation": "USE_GLOBAL_MODEL"}

            symbols_info = {}
            for sym, group in df.groupby('symbol'):
                if len(group) < 10:
                    continue
                closes = group['price_close'].values
                returns = np.diff(closes) / closes[:-1]
                volatility_std = float(np.std(returns) if len(returns) > 0 else 0.0)
                mean_price = float(np.mean(closes))
                
                symbols_info[sym] = {
                    "count": len(group),
                    "mean_price": round(mean_price, 5),
                    "volatility_std": round(volatility_std, 6)
                }

            if not symbols_info:
                return {"symbols": {}, "recommendation": "USE_GLOBAL_MODEL"}

            vols = [info['volatility_std'] for info in symbols_info.values()]
            max_vol = max(vols) if vols else 0.0
            min_vol = min([v for v in vols if v > 0] or [1.0])
            vol_ratio = max_vol / min_vol if min_vol > 0 else 1.0

            prices = [info['mean_price'] for info in symbols_info.values()]
            max_price = max(prices) if prices else 1.0
            min_price = min([p for p in prices if p > 0] or [1.0])
            price_ratio = max_price / min_price if min_price > 0 else 1.0

            should_use_per_symbol = (vol_ratio >= 1.5) or (price_ratio >= 2.0)
            recommendation = (
                "USE_PER_SYMBOL_MODELS (Juftliklar orasida volatillik/narx farqi katta — alohida per-symbol modellar o'rgatiladi)"
                if should_use_per_symbol
                else "USE_GLOBAL_MODEL (Juftliklar o'xshash volatillik profiliga ega)"
            )

            return {
                "symbols": symbols_info,
                "volatility_ratio": round(vol_ratio, 2),
                "price_scale_ratio": round(price_ratio, 2),
                "should_use_per_symbol": should_use_per_symbol,
                "recommendation": recommendation
            }
        except Exception as e:
            logger.error(f"Multi-symbol strategy tahlilida xatolik: {e}")
            return {"error": str(e), "recommendation": "USE_GLOBAL_MODEL"}

    def compare_models_ab(self, baseline_model_path: Optional[str] = None, symbol: Optional[str] = None) -> dict:
        """
        Institutional A/B Model Benchmark:
        Model A (baseline/eski checkpoint) va Model B (yangi 12-feature model) ni bir xil test to'plamida taqqoslash.
        Regressiya oldini oladi.
        """
        if not TORCH_AVAILABLE:
            return {"status": "error", "message": "PyTorch vertical not available"}

        target_symbol = symbol or self.symbol
        test_dataset = ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10), split='val', train_ratio=0.8, scaler=self.scaler, symbol=target_symbol)
        if len(test_dataset) == 0:
            return {"status": "insufficient_test_data", "samples": 0}

        test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
        criterion = nn.CrossEntropyLoss()

        # Model B (Current Model) evaluation
        self.model.eval()
        b_loss, b_preds, b_targets = 0.0, [], []
        with torch.no_grad():
            for inputs, labels in test_loader:
                out = self.model(inputs)
                loss = criterion(out, labels)
                b_loss += loss.item() * len(labels)
                b_preds.extend(torch.argmax(out, dim=1).tolist())
                b_targets.extend(labels.tolist())

        val_total = max(len(b_targets), 1)
        b_acc = sum(1 for p, t in zip(b_preds, b_targets) if p == t) / float(val_total)
        
        # Macro F1 for Model B
        b_f1s = []
        for c in [0, 1, 2]:
            tp = sum(1 for p, t in zip(b_preds, b_targets) if p == c and t == c)
            fp = sum(1 for p, t in zip(b_preds, b_targets) if p == c and t != c)
            fn = sum(1 for p, t in zip(b_preds, b_targets) if p != c and t == c)
            prec = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            b_f1s.append(f1)
        b_macro_f1 = sum(b_f1s) / 3.0

        # Model A evaluation (if baseline file specified and exists)
        a_acc, a_macro_f1, a_loss = 0.0, 0.0, 0.0
        has_model_a = False
        if baseline_model_path and os.path.exists(baseline_model_path):
            try:
                state_a = torch.load(baseline_model_path, weights_only=True)
                if 'lstm.weight_ih_l0' in state_a:
                    saved_h_a = state_a['lstm.weight_ih_l0'].shape[0] // 4
                    layer_count_a = 0
                    while f'lstm.weight_ih_l{layer_count_a}' in state_a:
                        layer_count_a += 1
                    model_a = MarketPredictorLSTM(input_size=12, hidden_size=saved_h_a, num_layers=max(1, layer_count_a))
                else:
                    model_a = MarketPredictorLSTM(input_size=12)
                model_a.load_state_dict(state_a)
                model_a.eval()
                a_preds = []
                with torch.no_grad():
                    for inputs, labels in test_loader:
                        out_a = model_a(inputs)
                        loss_a = criterion(out_a, labels)
                        a_loss += loss_a.item() * len(labels)
                        a_preds.extend(torch.argmax(out_a, dim=1).tolist())
                
                a_acc = sum(1 for p, t in zip(a_preds, b_targets) if p == t) / float(val_total)
                a_f1s = []
                for c in [0, 1, 2]:
                    tp = sum(1 for p, t in zip(a_preds, b_targets) if p == c and t == c)
                    fp = sum(1 for p, t in zip(a_preds, b_targets) if p == c and t != c)
                    fn = sum(1 for p, t in zip(a_preds, b_targets) if p != c and t == c)
                    prec = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
                    rec = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
                    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
                    a_f1s.append(f1)
                a_macro_f1 = sum(a_f1s) / 3.0
                a_loss = a_loss / float(val_total)
                has_model_a = True
            except Exception as e:
                logger.warning(f"Baseline Model A yuklashda xatolik: {e}")

        # Verdict determination
        if has_model_a:
            if b_macro_f1 > a_macro_f1:
                verdict = "ACCEPTED_OUTPERFORMS_BASELINE"
            elif b_macro_f1 == a_macro_f1:
                verdict = "ACCEPTED_EQUIVALENT_TO_BASELINE"
            else:
                verdict = "REJECTED_REGRESSION_DETECTED"
        else:
            verdict = "ACCEPTED_NO_BASELINE_SPECIFIED"

        return {
            "symbol": target_symbol or "GLOBAL",
            "test_samples": len(test_dataset),
            "model_b_new": {
                "accuracy": round(b_acc * 100.0, 2),
                "macro_f1": round(b_macro_f1 * 100.0, 2),
                "loss": round(b_loss / float(val_total), 4)
            },
            "model_a_baseline": {
                "accuracy": round(a_acc * 100.0, 2) if has_model_a else None,
                "macro_f1": round(a_macro_f1 * 100.0, 2) if has_model_a else None,
                "loss": round(a_loss, 4) if has_model_a else None,
                "available": has_model_a
            },
            "verdict": verdict
        }

    def calculate_feature_importance(self, symbol: Optional[str] = None, n_repeats: int = 5) -> dict:
        """
        Permutation Feature Importance Analyzer:
        12 ta institutional xususiyatning har birini alohida permute (shuffling) qilib,
        modelning Macro F1 ballidagi tushishini hisoblash. Qaysi xususiyat haqiqatan foydali, qaysi biri shovqin ekanini ko'rsatadi.
        """
        if not TORCH_AVAILABLE or self.model is None:
            return {"status": "error", "message": "PyTorch or model unavailable"}

        feature_names = [
            "1. Open Price Ratio",
            "2. High Price Ratio",
            "3. Low Price Ratio",
            "4. Close Return",
            "5. Volume Change",
            "6. RSI-14 Indicator",
            "7. ATR-14 Volatility Ratio",
            "8. MA-20 Spread",
            "9. Momentum (5-bar)",
            "10. Tick Volume Ratio",
            "11. Body Ratio",
            "12. Cyclic Time (Sin)"
        ]

        target_symbol = symbol or self.symbol
        test_dataset = ShadowDataset(self.db_path, seq_length=getattr(self, "seq_length", 10), split='val', train_ratio=0.8, scaler=self.scaler, symbol=target_symbol)
        if len(test_dataset) == 0:
            return {"status": "insufficient_data", "feature_importance": []}

        test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)
        self.model.eval()

        # Baseline Macro F1 score
        b_preds, b_targets = [], []
        with torch.no_grad():
            for inputs, labels in test_loader:
                out = self.model(inputs)
                b_preds.extend(torch.argmax(out, dim=1).tolist())
                b_targets.extend(labels.tolist())

        def calc_macro_f1(preds, targets):
            f1s = []
            for c in [0, 1, 2]:
                tp = sum(1 for p, t in zip(preds, targets) if p == c and t == c)
                fp = sum(1 for p, t in zip(preds, targets) if p == c and t != c)
                fn = sum(1 for p, t in zip(preds, targets) if p != c and t == c)
                prec = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
                rec = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
                f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
                f1s.append(f1)
            return (sum(f1s) / 3.0) * 100.0

        baseline_f1 = calc_macro_f1(b_preds, b_targets)

        # Collect full validation inputs tensor (N, seq_len, 12)
        all_inputs = []
        all_labels = []
        for inputs, labels in test_loader:
            all_inputs.append(inputs)
            all_labels.extend(labels.tolist())
        full_inputs = torch.cat(all_inputs, dim=0) # (N, 10, 12)

        importance_results = []
        num_features = full_inputs.shape[2]

        for feature_idx in range(num_features):
            f1_drops = []
            for _ in range(n_repeats):
                permuted_inputs = full_inputs.clone()
                # Permute feature values across batch dimension for all timesteps
                perm_idx = torch.randperm(permuted_inputs.shape[0])
                permuted_inputs[:, :, feature_idx] = permuted_inputs[perm_idx, :, feature_idx]

                with torch.no_grad():
                    out = self.model(permuted_inputs)
                    preds = torch.argmax(out, dim=1).tolist()
                    perm_f1 = calc_macro_f1(preds, all_labels)
                    f1_drops.append(baseline_f1 - perm_f1)

            mean_drop = float(np.mean(f1_drops))
            fname = feature_names[feature_idx] if feature_idx < len(feature_names) else f"Feature {feature_idx+1}"
            
            if mean_drop > 2.0:
                classification = "CRITICAL_SIGNAL"
            elif mean_drop > 0.3:
                classification = "USEFUL_FEATURE"
            else:
                classification = "NOISE_OR_REDUNDANT"

            importance_results.append({
                "feature_index": feature_idx + 1,
                "feature_name": fname,
                "importance_score": round(mean_drop, 2),
                "classification": classification
            })

        # Rank descending by importance score
        importance_results.sort(key=lambda x: x["importance_score"], reverse=True)

        return {
            "baseline_macro_f1": round(baseline_f1, 2),
            "samples_analyzed": len(all_labels),
            "feature_importance_ranking": importance_results
        }

    def check_class_imbalance(self, db_path: str = None) -> dict:
        """
        shadow_states ma'lumotlar bazasidagi class imbalance holatini audit qilish.
        """
        target_db = db_path or self.db_path
        dataset = ShadowDataset(target_db, seq_length=getattr(self, 'seq_length', 10), split='all', symbol=self.symbol)
        dist = dataset.get_class_distribution()
        return dist

    def evaluate_production_readiness(self, symbol=None) -> dict:
        """
        Model production uchun tayyorligini tekshirish.
        Returns: {"ready": bool, "reasons": [...], "metrics": {...}}
        """
        reasons = []
        metrics = {}
        
        target_symbol = symbol or self.symbol
        dataset = ShadowDataset(self.db_path, seq_length=getattr(self, 'seq_length', 10), split='all', symbol=target_symbol)
        total = len(dataset)
        metrics["total_samples"] = total
        
        min_samples = 500
        if total < min_samples:
            reasons.append(f"Kam dataset: {total}/{min_samples}")
            
        dist = dataset.get_class_distribution()
        for cls, count in dist.get("class_counts", {}).items():
            if count < total * 0.1:
                reasons.append(f"Class {cls} juda kam: {count} ({count/total*100:.0f}%)")
                
        if self.use_ensemble:
            for i in range(self.ensemble_size):
                p = self.model_path.replace('.pth', f'_ens_{i}.pth')
                if not os.path.exists(p):
                    reasons.append(f"Ensemble model {i} topilmadi: {p}")
        elif not os.path.exists(self.model_path):
            reasons.append(f"Model topilmadi: {self.model_path}")
            
        if self.model or getattr(self, 'ensemble_models', None):
            try:
                ab_result = self.compare_models_ab(target_symbol=target_symbol)
                macro_f1 = ab_result.get("model_b_new", {}).get("macro_f1", 0)
                metrics["macro_f1"] = macro_f1
                if macro_f1 < 45.0:
                    reasons.append(f"Macro F1 past: {macro_f1}% (min 45%)")
            except Exception:
                reasons.append("F1 hisoblashda xato, A/B taqqoslash o'tmadi")
        else:
            reasons.append("Model yuklanmagan")
            
        return {
            "ready": len(reasons) == 0,
            "reasons": reasons,
            "metrics": metrics
        }

    def predict(self, recent_candles: list) -> dict:
        """
        Oxirgi shamlarni (masalan, 10 ta) olib, 12 xususiyat asosida keyingi harakatni bashorat qilish.
        """
        if not TORCH_AVAILABLE or len(recent_candles) < self.seq_length:
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
                return {"prediction": "HOLD", "confidence": 0, "network_state": {}}
            
        features_np = compute_12_features(recent_candles)
        if len(features_np) < self.seq_length:
            return {"prediction": "HOLD", "confidence": 0, "network_state": {}}

        features_seq = features_np[-self.seq_length:] # Last seq_length candles
        
        if self.scaler is None:
            self.scaler = InstitutionalFeatureScaler()

        try:
            features_scaled = self.scaler.transform(features_seq)
        except Exception as e:
            logger.warning(f"Scaler transform xatosi: {e}. Fallback InstitutionalFeatureScaler scaling ishlatiladi.")
            fallback = InstitutionalFeatureScaler()
            features_scaled = fallback.fit_transform(features_seq)
        
        input_tensor = torch.tensor(np.array([features_scaled]), dtype=torch.float32)
        
        
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
        
        self._export_network_state(state)
        
        res = {
            "prediction": mapping[pred_idx],
            "confidence": round(float(confidence), 1),
            "network_state": state
        }

        if getattr(self.model, "use_attention", False) and getattr(self.model, "last_attention_weights", None) is not None:
            raw_attn = self.model.last_attention_weights
            flat_attn = np.squeeze(raw_attn).tolist()
            if isinstance(flat_attn, (float, int)):
                flat_attn = [float(flat_attn)]
            res["attention_weights"] = [round(float(w), 4) for w in flat_attn]
            res["most_important_candle_index"] = int(np.argmax(flat_attn))

        return res

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


