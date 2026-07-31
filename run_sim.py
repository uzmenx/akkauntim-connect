import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.learning.simulator import RLAgentRunner

runner = RLAgentRunner('bot_learning.db')
runner.train_agent(total_timesteps=2000)
print("Simulator run complete!")
