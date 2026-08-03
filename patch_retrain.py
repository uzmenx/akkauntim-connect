import sys

with open("bot/main.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "logger.info(\"🔄 Davriy o'qitish boshlandi (LSTM + PPO)...\")" in line:
        new_lines.append(line)
        new_lines.append(line.replace("logger.info(\"🔄 Davriy o'qitish boshlandi (LSTM + PPO)...\")", "import time\n                    start_time = time.time()"))
    elif "self.rl_agent.train_agent(total_timesteps=1000000)" in line:
        new_lines.append(line.replace("1000000", "200000")) # Reduced to 200,000 for faster training
    elif "logger.info(\"✅ Davriy o'qitish yakunlandi. Keyingisi 4 soatdan keyin.\")" in line:
        new_lines.append(line.replace("logger.info(\"✅ Davriy o'qitish yakunlandi. Keyingisi 4 soatdan keyin.\")", "elapsed = time.time() - start_time\n                    logger.info(f\"✅ Davriy o'qitish yakunlandi ({elapsed:.2f} soniya). Keyingisi 4 soatdan keyin.\")"))
    else:
        new_lines.append(line)

with open("bot/main.py", "w") as f:
    f.writelines(new_lines)
print("Patched bot/main.py")
