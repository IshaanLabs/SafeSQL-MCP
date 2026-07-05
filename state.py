from typing import TypedDict, Optional

class AgentState(TypedDict):
    # Conversation
    user_question:      str
    conversation_history: list

    # SQL
    generated_sql:      Optional[str]
    validated_sql:      Optional[str]
    dry_run_count:      Optional[int]

    # Classification
    operation_type:     Optional[str]   # SELECT / UPDATE / DELETE / INSERT / DDL
    risk_level:         Optional[str]   # SAFE / LOW / MEDIUM / HIGH / BLOCKED

    # Approval
    approval_status:    Optional[str]   # PENDING / APPROVED / REJECTED / EXPIRED
    approval_token:     Optional[str]
    approval_timestamp: Optional[float]
    approved_by:        Optional[str]

    # Execution
    query_result:       Optional[str]
    rows_affected:      Optional[int]
    execution_time_ms:  Optional[int]
    error_message:      Optional[str]

    # Output
    final_response:     Optional[str]
