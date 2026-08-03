import numpy as np
from dataclasses import dataclass

@dataclass
class FanConfig:
    n_paths: int = 60          # nechta chiziq chizish (60-100 UI uchun yetarli)
    n_steps: int = 15          # necha sham oldinga (masalan M5 da = 75 daqiqa)
    seed: int | None = None
    drift_multiplier: float = 0.3 # drift kuchi (kalibratsiya uchun, optimal: 0.3)

def compute_volatility(closes: np.ndarray) -> float:
    """Oxirgi shamlar asosida log-return std dev (bar boshiga volatillik)."""
    # Xavfsizlik uchun qisqa ro'yxat yoki noto'g'ri qiymatlarni tekshiramiz
    if len(closes) < 2:
        return 0.001
        
    log_returns = np.diff(np.log(closes))
    # Nolinchi volatillikni oldini olish
    vol = float(np.std(log_returns))
    return vol if vol > 1e-8 else 0.001

def compute_drift(direction: str, confidence: float, base_vol: float, max_drift_multiplier: float = 0.3) -> float:
    """
    Voting engine signalidan markaziy og'ish (drift) hisoblanadi.
    confidence past bo'lsa -> drift kamayadi -> fan markazga yaqinroq (neytral)
    confidence yuqori bo'lsa -> drift kuchayadi -> fan aniq yo'nalishga egiladi
    """
    sign_map = {"BUY": 1, "SELL": -1, "NEUTRAL": 0, "HOLD": 0}
    # Normalize direction just in case
    direction = direction.upper()
    if "BUY" in direction:
        sign = 1
    elif "SELL" in direction:
        sign = -1
    else:
        sign = 0
        
    # confidence odatda 0-1 oralig'ida yoki 0-100 bo'lishi mumkin. Normallashtiramiz:
    norm_conf = confidence if confidence <= 1.0 else confidence / 100.0
    
    # drift miqyosini volatillikka bog'lash - haddan tashqari optimistik chiziq chizmaslik uchun
    return sign * norm_conf * base_vol * max_drift_multiplier

def simulate_fan(closes: np.ndarray, direction: str, confidence: float,
                  config: FanConfig = None) -> np.ndarray:
    """
    Qaytaradi: shape (n_paths, n_steps) - har bir yo'l uchun narx ketma-ketligi
    """
    if config is None:
        config = FanConfig()
        
    rng = np.random.default_rng(config.seed)
    
    # xavfsizlik:
    if len(closes) == 0:
        return np.zeros((config.n_paths, config.n_steps))
        
    last_price = closes[-1]
    vol = compute_volatility(closes)
    drift = compute_drift(direction, confidence, vol, max_drift_multiplier=config.drift_multiplier)

    # Har bir qadam uchun tasodifiy shok + bias'langan drift
    shocks = rng.normal(loc=drift, scale=vol, size=(config.n_paths, config.n_steps))
    log_paths = np.cumsum(shocks, axis=1)
    price_paths = last_price * np.exp(log_paths)

    return price_paths  # (n_paths, n_steps)
