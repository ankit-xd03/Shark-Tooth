import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PORTAL_HOST = "127.0.0.1"
PORTAL_PORT = int(os.getenv("PORTAL_PORT", "8765"))
PORTAL_URL = f"http://{PORTAL_HOST}:{PORTAL_PORT}/"
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
SLOW_MO = int(os.getenv("PLAYWRIGHT_SLOW_MO_MS", "0"))
TIMEOUT_MS = int(os.getenv("BROWSER_TIMEOUT_MS", "8000"))

DEFAULT_MODELS = {"anthropic": "claude-haiku-5-5", "gemini": "gemini-3.6-flash",
                  "openai_compat": "llama-3.3-70b-versatile"}
DEFAULT_AGENT_MODELS = {"anthropic": "claude-sonnet-5-5"}


def llm_provider() -> str:
    p = os.getenv("LLM_PROVIDER", "").strip().lower()
    if p:
        return p
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"):
        return "openai_compat"
    return ""


def llm_model(role: str = "extract") -> str:
    p = llm_provider()
    if role == "agent" and os.getenv("LLM_AGENT_MODEL"):
        return os.getenv("LLM_AGENT_MODEL")
    if os.getenv("LLM_MODEL"):
        return os.getenv("LLM_MODEL")
    if role == "agent":
        return DEFAULT_AGENT_MODELS.get(p) or DEFAULT_MODELS.get(p, "")
    return DEFAULT_MODELS.get(p, "")


def llm_available() -> bool:
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        return False
    p = llm_provider()
    if p == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if p == "gemini":
        return bool(os.getenv("GEMINI_API_KEY"))
    if p == "openai_compat":
        return bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"))
    return False
