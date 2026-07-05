from langchain_ollama import ChatOllama
from config import OLLAMA_BASE_URL, MODEL_NAME
from db import get_northwind_db
from logger import get_logger

logger = get_logger("generate_sql")

llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=MODEL_NAME)

def load_prompt():
    with open("prompts/generate_sql.txt", "r") as f:
        return f.read()

PROMPT_TEMPLATE = load_prompt()


def generate_sql_node(state: dict) -> dict:
    question = state["user_question"]
    history = state.get("conversation_history", [])
    logger.info(f"Generating SQL for: {question}")

    db = get_northwind_db()
    schema = db.get_table_info()

    history_str = "\n".join(history[-5:]) if history else "None"

    prompt = PROMPT_TEMPLATE.format(
        schema=schema,
        question=question,
        history=history_str
    )

    response = llm.invoke(prompt)
    sql = response.content.strip()
    # Clean markdown formatting
    sql = sql.replace("```sql", "").replace("```", "").strip()

    logger.info(f"Generated SQL: {sql}")
    return {"generated_sql": sql}
