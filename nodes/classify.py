from langchain_ollama import ChatOllama
from config import OLLAMA_BASE_URL, MODEL_NAME
from logger import get_logger

logger = get_logger("classify")

llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=MODEL_NAME)

def load_prompt():
    with open("prompts/classify.txt", "r") as f:
        return f.read()

PROMPT_TEMPLATE = load_prompt()

VALID_TYPES = {"SELECT", "INSERT", "UPDATE", "DELETE", "DDL", "UNSAFE"}


def classify_node(state: dict) -> dict:
    question = state["user_question"]
    logger.info(f"Classifying question: {question}")

    prompt = PROMPT_TEMPLATE.format(question=question)
    response = llm.invoke(prompt)
    classification = response.content.strip().upper()

    # Fallback if LLM returns unexpected value
    if classification not in VALID_TYPES:
        logger.warning(f"Unexpected classification '{classification}', defaulting to UNSAFE")
        classification = "UNSAFE"

    logger.info(f"Classification result: {classification}")
    return {"operation_type": classification}
