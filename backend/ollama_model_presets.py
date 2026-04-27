"""Default Ollama model try-order for chat (problem + solution + scoring). Keep in sync with Settings UI hints."""

# Strong general models; first match on the server is used if OLLAMA_MODEL is unset.
# User can set OLLAMA_MODEL explicitly or OLLAMA_MODEL_CANDIDATES=mod1,mod2 in .env
OLLAMA_RECOMMENDED_CHAT_MODELS: tuple[str, ...] = (
    "qwen2.5:7b",
    "qwen2.5:14b",
    "llama3.1:8b",
    "llama3.1:70b",
    "llama3.2:3b",
    "llama3",
    "mistral",
    "gemma2:9b",
    "phi3",
    "deepseek-r1:8b",
)
