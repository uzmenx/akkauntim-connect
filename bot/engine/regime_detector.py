import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, Any, List

class MarketRegime(Enum):
    TREND = "TREND"
    RANGE = "RANGE"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"

class RegimeDetector:
    """
    Bozor rejimini aniqlovchi modul.
    
    Qabul qilinadigan rejimlari:
    - TREND: Bozor aniq yo'nalishga ega (ADX > 25)
    - RANGE: Bozor tor diapazonda (ADX < 25, past volatilite)
    - VOLATILE: Yuqori volatilite, ehtimol yangiliklar ta'sirida
    
    Eslatma: _update_regime_confidence haqiqiy HMM emas, 
    balki oddiy exponential smoothing (eksponensial tekislash) hisoblanadi.
    """
    
    def __init__(self, lookback: int = 100):
        self.lookback = lookback
        self.history: List[MarketRegime] = []
        self.confidence = {
            MarketRegime.TREND: 0.0,
            MarketRegime.RANGE: 0.0,
            MarketRegime.VOLATILE: 0.0,
            MarketRegime.UNKNOWN: 1.0
        }
        
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """ADX ni hisoblash. Agar yetarli ma'lumot bo'lmasa, 0 qaytaradi."""
        if len(df) < period * 2:
            return 0.0
            
        df = df.copy()
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        df['up_move'] = df['high'] - df['high'].shift()
        df['down_move'] = df['low'].shift() - df['low']
        
        df['+dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['-dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
        
        # Wilder's Smoothing
        df['tr_roll'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
        df['+dm_roll'] = df['+dm'].ewm(alpha=1/period, adjust=False).mean()
        df['-dm_roll'] = df['-dm'].ewm(alpha=1/period, adjust=False).mean()
        
        df['+di'] = 100 * (df['+dm_roll'] / df['tr_roll'])
        df['-di'] = 100 * (df['-dm_roll'] / df['tr_roll'])
        
        df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
        df['adx'] = df['dx'].ewm(alpha=1/period, adjust=False).mean()
        
        return df['adx'].iloc[-1]
        
    def _volatility_percentile(self, df: pd.DataFrame) -> float:
        """Oxirgi lookback qiymat ichida joriy volatility percentile ni hisoblash."""
        if len(df) < 10:
            return 50.0
        # ATR ga o'xshash sodda volatility (High - Low)
        volatilities = df['high'] - df['low']
        current_vol = volatilities.iloc[-1]
        lookback_vols = volatilities.iloc[-self.lookback:]
        percentile = (lookback_vols < current_vol).mean() * 100
        return percentile
        
    def _spread_percentile(self, df: pd.DataFrame) -> float:
        """Oxirgi lookback qiymat ichida joriy spread percentile ni hisoblash."""
        if 'spread' not in df.columns or len(df) < 10:
            return 50.0
        current_spread = df['spread'].iloc[-1]
        lookback_spreads = df['spread'].iloc[-self.lookback:]
        percentile = (lookback_spreads < current_spread).mean() * 100
        return percentile
        
    def _volume_percentile(self, df: pd.DataFrame) -> float:
        """Oxirgi lookback qiymat ichida joriy volume percentile ni hisoblash."""
        if 'tick_volume' not in df.columns and 'volume' not in df.columns:
            return 50.0
            
        vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
        if len(df) < 10:
            return 50.0
            
        current_vol = df[vol_col].iloc[-1]
        lookback_vols = df[vol_col].iloc[-self.lookback:]
        percentile = (lookback_vols < current_vol).mean() * 100
        return percentile

    def _update_regime_confidence(self, new_regime: MarketRegime, alpha: float = 0.2):
        """
        Confidence'ni eksponensial tekislash (avvalgi HMM deb nomlangan).
        """
        for regime in self.confidence:
            if regime == new_regime:
                self.confidence[regime] = (1 - alpha) * self.confidence[regime] + alpha * 1.0
            else:
                self.confidence[regime] = (1 - alpha) * self.confidence[regime]
                
        # Normalize
        total = sum(self.confidence.values())
        if total > 0:
            for regime in self.confidence:
                self.confidence[regime] /= total

    def update(self, df: pd.DataFrame) -> MarketRegime:
        """
        Bozor rejimini aniqlaydi va qaytaradi.
        """
        if df.empty or len(df) < 20:
            self._update_regime_confidence(MarketRegime.UNKNOWN)
            return MarketRegime.UNKNOWN

        adx = self._calculate_adx(df)
        vol_pct = self._volatility_percentile(df)
        
        # Soddalashtirilgan logika
        if vol_pct > 80.0:
            detected_regime = MarketRegime.VOLATILE
        elif adx > 25.0:
            detected_regime = MarketRegime.TREND
        else:
            detected_regime = MarketRegime.RANGE
            
        self._update_regime_confidence(detected_regime)
        self.history.append(detected_regime)
        
        return detected_regime
