# AI module: DeepSeek-V2-7B integration

This folder contains helper scripts to integrate a local DeepSeek-V2-7B model into the MT5 trading bot for signal generation.

Important notes
- This repository does NOT include model weights. You must provide the model files locally or point to a Hugging Face repo that you have access to.
- Verify DeepSeek-V2 license and distribution terms before using in production or redistributing.

Quick start
1. Install dependencies in a virtual environment:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r ai/requirements.txt

2. Place model files locally or set DEEPSEEK_MODEL_PATH env var to a Hugging Face repo id (if you have access). Example:

   export DEEPSEEK_MODEL_PATH="/path/to/deepseek-v2-7b"

3. Test inference:

   python ai/deepseek_inference.py --test

4. Integrate into MT5 bot: see ai/integrate_with_bot.py — adapt get_market_context() to your bot's data.

Files in this folder:
- requirements.txt — minimal Python deps
- deepseek_inference.py — model loading + generate wrapper
- prompt_templates.py — JSON-output prompt template(s)
- integrate_with_bot.py — example hook to call the inference from your trading loop
- docker/Dockerfile — optional container for running inference

If you want, I can open a PR with these files and then you can git pull and test locally. If you already have a preferred model path (Hugging Face id or local path) tell me and I'll update the defaults.
