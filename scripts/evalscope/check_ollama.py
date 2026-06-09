import yaml
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLLAMA_BASE = "http://127.0.0.1:11434"

def load_models():
    path = ROOT / "configs" / "models.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["models"]

def get_ollama_models():
    resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=10)
    resp.raise_for_status()
    return [item["name"] for item in resp.json().get("models", [])]

def test_model(model_name):
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "请只回复：测试成功"}],
        "stream": False
    }
    resp = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]

def main():
    local_models = get_ollama_models()
    print(f"Ollama 本地模型列表: {local_models}\n")
    for model in load_models():
        if not model.get("enabled", True):
            continue
        name = model["name"]
        if name not in local_models:
            print(f"[缺失] {name} 不在 Ollama 本地列表中")
        else:
            print(f"[存在] {name}")
            try:
                reply = test_model(name)
                print(f"[测试输出] {reply}\n")
            except Exception as e:
                print(f"[测试失败] {e}\n")

if __name__ == "__main__":
    main()
