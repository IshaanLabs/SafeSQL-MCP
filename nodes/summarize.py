from langchain_ollama import ChatOllama
from config import OLLAMA_BASE_URL, MODEL_NAME
from logger import get_logger

logger = get_logger("summarize")

llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=MODEL_NAME)

def load_prompt():
    with open("prompts/summarize.txt", "r") as f:
        return f.read()

PROMPT_TEMPLATE = load_prompt()


def summarize_node(state: dict) -> dict:
    question = state["user_question"]
    sql = state.get("validated_sql", "")
    result = state.get("query_result", "")
    error = state.get("error_message")

    if error:
        logger.info(f"Summarizing error: {error}")
        return {"final_response": f"I couldn't complete that operation. Error: {error}"}

    if state.get("risk_level") == "BLOCKED":
        return {"final_response": f"This operation is blocked for safety reasons. {error or ''}"}

    if state.get("approval_status") == "REJECTED":
        return {"final_response": "Operation was rejected. No changes were made."}

    logger.info("Generating natural language summary")
    prompt = PROMPT_TEMPLATE.format(question=question, sql=sql, result=result)
    response = llm.invoke(prompt)

    final = response.content.strip()
    logger.info(f"Summary generated: {final[:100]}...")
    return {"final_response": final}
