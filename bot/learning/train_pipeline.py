"""
Training pipeline for the Shadow AI trading bot.
Handles LSTM ensemble training and PPO RL agent training.
Production-grade: error-handling, metrics, early stopping, and A/B benchmarking.
"""

import os
import json
import logging
import traceback
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader
    from sklearn.metrics import f1_score
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.error("PyTorch or scikit-learn not installed. Training features will be disabled.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.error("NumPy not installed.")

try:
    from bot.learning.predictor import PredictorEngine, ShadowDataset, MarketPredictorLSTM
    from bot.learning.features import InstitutionalFeatureScaler, compute_12_features
    from bot.learning.simulator import RLAgentRunner
except ImportError as e:
    logger.error(f"Failed to import internal modules: {e}")


class TrainPipeline:
    """
    Production-grade training pipeline for the Shadow AI trading bot.
    Manages both LSTM ensemble and PPO RL agent training.
    """

    def __init__(self, db_path='bot_learning.db', model_dir='bot/learning', symbol=None):
        self.db_path = db_path
        self.model_dir = model_dir
        self.symbol = symbol
        
        try:
            os.makedirs(self.model_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create model directory {self.model_dir}: {e}")

    def run_full_training(self, epochs=30, train_ratio=0.8, ensemble_size=3):
        """
        Run full training for LSTM ensemble with class weighting, early stopping, and A/B benchmark.
        """
        report = {
            "status": "failed",
            "message": "",
            "metrics": {},
            "timestamp": datetime.now().isoformat()
        }

        if not TORCH_AVAILABLE or not NUMPY_AVAILABLE:
            report["message"] = "PyTorch or NumPy not available."
            return report

        try:
            logger.info("Starting run_full_training for LSTM Ensemble.")

            # Load Dataset
            try:
                dataset_train = ShadowDataset(self.db_path, seq_length=10, split='train', train_ratio=train_ratio, symbol=self.symbol)
                dataset_val = ShadowDataset(self.db_path, seq_length=10, split='val', train_ratio=train_ratio, symbol=self.symbol)
            except Exception as e:
                report["message"] = f"Dataset loading failed: {e}"
                logger.error(report["message"])
                return report

            total_train = len(dataset_train)
            total_val = len(dataset_val)
            total_samples = total_train + total_val

            if total_samples < 500:
                msg = f"Insufficient data: {total_samples} samples. Need at least 500."
                logger.warning(msg)
                report["message"] = msg
                return report

            # Check class distribution
            labels = [dataset_train[i][1].item() for i in range(total_train)]
            class_counts = Counter(labels)
            logger.info(f"Class distribution: {class_counts}")
            
            for cls in range(3):
                if class_counts.get(cls, 0) < total_samples * 0.05:
                    logger.warning(f"Class {cls} is severely imbalanced or missing.")

            # Calculate class weights for weighted CrossEntropyLoss
            num_classes = 3
            weights = []
            for i in range(num_classes):
                count = class_counts.get(i, 0)
                if count > 0:
                    weights.append(total_train / (num_classes * count))
                else:
                    weights.append(1.0)
            
            tensor_weights = torch.FloatTensor(weights)
            criterion = nn.CrossEntropyLoss(weight=tensor_weights)

            # Ensemble Settings
            seeds = [42, 142, 242][:ensemble_size]
            hidden_size = 32
            use_attention = True if total_samples > 2000 else False
            
            train_loader = DataLoader(dataset_train, batch_size=64, shuffle=True, drop_last=False)
            val_loader = DataLoader(dataset_val, batch_size=64, shuffle=False, drop_last=False)

            best_models_f1 = []
            
            # Train each model in ensemble
            for idx, seed in enumerate(seeds):
                logger.info(f"Training ensemble model {idx+1}/{ensemble_size} with seed {seed}")
                torch.manual_seed(seed)
                np.random.seed(seed)
                
                model = MarketPredictorLSTM(
                    input_size=12,
                    hidden_size=hidden_size,
                    num_layers=2,
                    num_classes=num_classes,
                    dropout=0.3,
                    use_attention=use_attention,
                    bidirectional=False
                )
                
                optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
                scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=3, factor=0.5)
                
                best_val_f1 = 0.0
                patience_counter = 0
                early_stop_patience = 5
                best_model_state = None
                
                for epoch in range(epochs):
                    model.train()
                    train_loss = 0.0
                    for X_batch, y_batch in train_loader:
                        optimizer.zero_grad()
                        outputs = model(X_batch)
                        loss = criterion(outputs, y_batch)
                        loss.backward()
                        optimizer.step()
                        train_loss += loss.item()
                        
                    # Validation
                    model.eval()
                    val_preds, val_targets = [], []
                    val_loss = 0.0
                    with torch.no_grad():
                        for X_batch, y_batch in val_loader:
                            outputs = model(X_batch)
                            loss = criterion(outputs, y_batch)
                            val_loss += loss.item()
                            
                            _, predicted = torch.max(outputs.data, 1)
                            val_preds.extend(predicted.cpu().numpy())
                            val_targets.extend(y_batch.cpu().numpy())
                            
                    val_macro_f1 = f1_score(val_targets, val_preds, average='macro', zero_division=0)
                    scheduler.step(val_macro_f1)
                    
                    logger.debug(f"Model {idx+1} Epoch {epoch+1}: Train Loss {train_loss:.4f}, Val F1 {val_macro_f1:.4f}")
                    
                    if val_macro_f1 > best_val_f1:
                        best_val_f1 = val_macro_f1
                        best_model_state = model.state_dict().copy()
                        patience_counter = 0
                    else:
                        patience_counter += 1
                        
                    if patience_counter >= early_stop_patience:
                        logger.info(f"Early stopping model {idx+1} at epoch {epoch+1}")
                        break
                        
                # Save best state for this model
                if best_model_state:
                    model.load_state_dict(best_model_state)
                
                model_path = os.path.join(self.model_dir, f"ensemble_model_{idx}.pth")
                torch.save(model.state_dict(), model_path)
                best_models_f1.append(best_val_f1)
                
            avg_f1 = sum(best_models_f1) / len(best_models_f1) if best_models_f1 else 0
            
            # Use PredictorEngine for A/B benchmark
            try:
                engine = PredictorEngine(model_dir=self.model_dir)
                ab_result = engine.compare_models_ab()
            except Exception as e:
                logger.warning(f"A/B benchmarking failed or not implemented in engine: {e}")
                ab_result = {"status": "skipped", "reason": str(e)}

            report["status"] = "success"
            report["message"] = "LSTM ensemble training completed successfully."
            report["metrics"] = {
                "val_macro_f1_avg": avg_f1,
                "model_f1s": best_models_f1,
                "samples": total_samples
            }
            report["ab_benchmark"] = ab_result

            self._save_history("lstm_training", report)
            return report

        except Exception as e:
            logger.error(f"Error in run_full_training: {e}")
            logger.debug(traceback.format_exc())
            report["message"] = str(e)
            return report

    def train_rl_agent(self, total_timesteps=500000):
        """
        Train PPO agent using existing RLAgentRunner interface.
        """
        report = {
            "status": "failed",
            "message": "",
            "metrics": {},
            "timestamp": datetime.now().isoformat()
        }

        try:
            logger.info(f"Starting RL Agent training for {total_timesteps} timesteps.")
            runner = RLAgentRunner(db_path=self.db_path, symbol=self.symbol)
            stats = runner.train_agent(total_timesteps=total_timesteps)

            report["status"] = "success"
            report["message"] = "RL agent training completed."
            report["metrics"] = stats if stats else {}

            self._save_history("rl_training", report)
            return report

        except Exception as e:
            logger.error(f"Error in train_rl_agent: {e}")
            logger.debug(traceback.format_exc())
            report["message"] = str(e)
            return report

    def evaluate_production_readiness(self, symbol=None):
        """
        Evaluate if the current setup and models are ready for production.
        """
        report = {
            "ready": False,
            "reasons": [],
            "metrics": {}
        }
        sym = symbol or self.symbol

        try:
            # Check dataset
            dataset_all = ShadowDataset(self.db_path, seq_length=10, split='all', symbol=sym)
            total_samples = len(dataset_all)

            report["metrics"]["total_samples"] = total_samples

            if total_samples < 500:
                report["reasons"].append(f"Insufficient total samples: {total_samples} < 500")

            # Check class distribution
            labels = [dataset_all[i][1].item() for i in range(total_samples)]
            class_counts = Counter(labels)
            
            for cls in range(3):
                count = class_counts.get(cls, 0)
                pct = (count / total_samples) * 100 if total_samples > 0 else 0
                report["metrics"][f"class_{cls}_pct"] = pct
                
                if pct < 10.0:
                    report["reasons"].append(f"Class {cls} has < 10% samples ({pct:.1f}%)")

            # Check model files
            for i in range(3):
                model_path = os.path.join(self.model_dir, f"ensemble_model_{i}.pth")
                if not os.path.exists(model_path):
                    report["reasons"].append(f"Missing ensemble model file: {model_path}")
                    
            rl_model_path = os.path.join(self.model_dir, "ppo_agent.zip")
            if not os.path.exists(rl_model_path):
                report["reasons"].append(f"Missing RL model file: {rl_model_path}")

            history_path = os.path.join(self.model_dir, "lstm_training_history.json")
            if os.path.exists(history_path):
                with open(history_path, 'r') as f:
                    history = json.load(f)
                    if history and history[-1].get("metrics", {}).get("val_macro_f1_avg", 0) < 0.45:
                         report["reasons"].append("Latest val_macro_f1_avg is < 45%")
            else:
                 report["reasons"].append("No training history found to verify F1 score.")

            if len(report["reasons"]) == 0:
                report["ready"] = True

        except Exception as e:
            report["reasons"].append(f"Error during evaluation: {str(e)}")
            logger.error(f"Evaluation error: {e}")

        return report

    def run_scheduled_retrain(self):
        """
        Convenience method for periodic_retrain thread.
        Runs full training + RL training.
        """
        logger.info("Running scheduled retrain sequence.")
        
        lstm_report = self.run_full_training()
        logger.info(f"Scheduled LSTM Retrain status: {lstm_report['status']}")
        
        rl_report = self.train_rl_agent(total_timesteps=100000)
        logger.info(f"Scheduled RL Retrain status: {rl_report['status']}")
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "lstm_status": lstm_report["status"],
            "rl_status": rl_report["status"],
            "ready_for_prod": self.evaluate_production_readiness()["ready"]
        }
        
        return summary

    def _save_history(self, name, report):
        """Save training history to JSON for UI display."""
        filepath = os.path.join(self.model_dir, f"{name}_history.json")
        try:
            history = []
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    history = json.load(f)
            history.append(report)
            if len(history) > 50:
                history = history[-50:]
            with open(filepath, 'w') as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save history for {name}: {e}")
