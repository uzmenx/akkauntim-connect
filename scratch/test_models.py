import os
import anthropic

def load_env():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

load_env()
api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

models = [
    "claude-3-5-sonnet-latest",
    "claude-sonnet-4-6",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-haiku-20240307",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229"
]

for model in models:
    try:
        print(f"Trying model: {model}...")
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        print(f"Success with {model}: {response.content[0].text}\n")
    except Exception as e:
        print(f"Failed with {model}: {str(e)}\n")
