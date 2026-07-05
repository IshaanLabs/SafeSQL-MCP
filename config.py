import os

# --- LLM ---
OLLAMA_BASE_URL = "http://localhost:11434"
# MODEL_NAME = "codegemma:7b-instruct-v1.1-q4_K_S"
MODEL_NAME = "qwen2.5-coder:7b-instruct-q5_K_M"

# --- Databases ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NORTHWIND_DB_PATH = os.path.join(BASE_DIR, "database", "northwind.db")
AUDIT_DB_PATH     = os.path.join(BASE_DIR, "database", "audit.db")

NORTHWIND_DB_URI = f"sqlite:///{NORTHWIND_DB_PATH}"
AUDIT_DB_URI     = f"sqlite:///{AUDIT_DB_PATH}"

# --- Risk Thresholds ---
RISK_LEVELS = {
    "SELECT": "SAFE",
    "UPDATE": "MEDIUM",
    "DELETE": "HIGH",
    "INSERT": "LOW",
    "ALTER":  "HIGH",
    "DROP":   "BLOCKED",
    "TRUNCATE": "BLOCKED",
}

# --- Approval ---
APPROVAL_EXPIRY_SECONDS = 300   # approval token expires in 5 minutes

# --- Dry Run ---
DRY_RUN_ENABLED = True          # always do COUNT(*) before write ops
