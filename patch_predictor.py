import re

with open("bot/learning/predictor.py", "r") as f:
    content = f.read()

target = """        self.is_trained = False
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
                        
                    if saved_input_size != 12:
                        logger.warning(f"Mavjud model input size ({saved_input_size}) 12 ga mos kelmadi. Model 12 input_size bilan qayta yaratiladi.")
                        state_dict = None
                    else:
                        self.model = MarketPredictorLSTM(
                            input_size=12,
                            hidden_size=saved_hidden_size,
                            num_layers=max(1, layer_count),
                            dropout=0.3,
                            use_attention=has_attention
                        )
                    
                if state_dict is not None:
                    self.model.load_state_dict(state_dict)
                    self.is_trained = True
                    logger.info(
                        f"LSTM modeli (input_size=12, hidden_size={self.model.hidden_size}, "
                        f"num_layers={self.model.num_layers}, attention={self.model.use_attention}, "
                        f"symbol={symbol or 'GLOBAL'}) muvaffaqiyatli yuklandi."
                    )
            except Exception as e:
                logger.warning(f"LSTM modelini yuklashda xatolik: {e}")"""

replacement = """        self.is_trained = False
        self.seq_length = 10
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
                logger.warning(f"LSTM modelini yuklashda xatolik: {e}")"""

if target in content:
    with open("bot/learning/predictor.py", "w") as f:
        f.write(content.replace(target, replacement))
    print("Patched successfully")
else:
    print("Target not found")
