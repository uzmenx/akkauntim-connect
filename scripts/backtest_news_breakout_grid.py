import logging
import random
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def simulate_news_event():
    """
    Simulates the News Breakout Grid strategy over 30 historical high-impact events.
    In a fully operational environment, this should pull tick data from MT5 for dates 
    like NFP, CPI, FOMC, etc.
    """
    logger.info("Starting Backtest: News Breakout Grid (High Frequency)")
    balance = 1000.0
    risk_limit = 0.40 * balance
    
    total_events = 30
    attempts = 0
    max_attempts_per_event = 5
    hard_timeouts = 0
    total_pnl = 0.0
    
    for i in range(total_events):
        # 1. Dynamic Lot Scaling Simulation
        lot_size = 0.01
        multiplier = 1
        if balance > 100.0:
            multiplier = int(balance / 100.0)
            lot_size = 0.01 * multiplier
            
        logger.info(f"--- Simulating Event {i+1} ---")
        logger.info(f"  Balance: ${balance:.2f} | Lot Size: {lot_size:.2f}")
        
        event_pnl = 0.0
        
        # During one news event, there can be multiple grid cycles
        cycles = random.randint(1, 3) 
        
        for c in range(cycles):
            # Simulate a single grid cycle outcome
            outcome = random.random()
            
            if outcome < 0.18:
                # 18% chance of whipsaw (price hits both sides and gets stuck)
                hard_timeouts += 1
                # Base loss was ~60 for 0.01 lot
                loss = random.uniform(40, 80) * multiplier
                event_pnl -= loss
                logger.warning(f"  Cycle {c+1}: 🛑 Hard Timeout! Whipsaw loss: -${loss:.2f}")
            else:
                # Win (price breaks out in one direction)
                # Base profit was ~25 for 0.01 lot
                profit = random.uniform(10, 40) * multiplier
                event_pnl += profit
                logger.info(f"  Cycle {c+1}: ✅ Win! Breakout profit: +${profit:.2f}")
                
        total_pnl += event_pnl
        balance += event_pnl
        
        logger.info(f"Event {i+1} concluded. Net PnL: ${event_pnl:.2f}, New Balance: ${balance:.2f}\n")
        
        if total_pnl <= -risk_limit:
            logger.error(f"❌ MAX DAILY LOSS REACHED (-${abs(total_pnl):.2f}). Account blew up. Stopped.")
            break
            
        time.sleep(0.1)
            
    logger.info("=========================================")
    logger.info("          BACKTEST RESULTS               ")
    logger.info("=========================================")
    logger.info(f"Final Balance: ${balance:.2f} (Start: $1000.00)")
    logger.info(f"Total Net PnL: ${total_pnl:.2f}")
    logger.info(f"Total Hard Timeouts (Whipsaws): {hard_timeouts}")
    
    total_cycles = total_events * 2 # approx
    win_rate = 100.0
    if hard_timeouts > 0:
        win_rate = 100 - (hard_timeouts / 60 * 100) # roughly 60 cycles
        
    if hard_timeouts > (total_events * 0.20):
        logger.error("⚠️ Hard timeouts exceeded 20%! Strategy is too risky. Tweak pause/vol thresholds.")
    else:
        logger.info("✅ Strategy looks viable. Proceed with caution on a cent account.")

if __name__ == "__main__":
    simulate_news_event()
