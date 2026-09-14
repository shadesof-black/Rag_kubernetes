from app.agents.state import AgentState
from app.gateway import get_langchain_llm
import logfire

# Portkey-backed LLM: fallback + cache + retry — same .invoke() interface as ChatGroq
def planner_node(state: AgentState):
    """
    The Planner determines if a search is needed based on the ENTIRE conversation.
    """
    llm = get_langchain_llm(feature="planner")

    # Get the conversation history (excluding the latest message)
    history = ""
    for msg in state["messages"][:-1]:
        role_val = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", "user")
        role = "User" if role_val in ("user", "human") else "Assistant"
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        history += f"{role}: {content}\n"
    
    user_message = ""
    if state["messages"]:
        last_msg = state["messages"][-1]
        user_message = last_msg.get("content") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")
    
    prompt = f"""
    You are an intelligent Assistant Planner. 
    Analyze the conversation history and the latest user message.
    
    CONVERSATION HISTORY:
    {history}
    
    LATEST MESSAGE:
    "{user_message}"
    
    Task:
    1. If the latest message is a greeting (hi, hello) or a question that can be answered using ONLY the conversation history above (e.g., "what is my name"), respond with 'CONVERSATIONAL'.
    2. If it is a technical question about Kubernetes, Intel, or Networking that requires fresh documentation, output a refined search query.
    
    Output ONLY 'CONVERSATIONAL' or the search query.
    """
    
    with logfire.span("🧠 Planner Decision"):
        decision = llm.invoke(prompt).content.strip()
        logfire.info(f"Intent identified: {decision}")
    
    if decision == "CONVERSATIONAL":
        return {
            "current_query": "CONVERSATIONAL",
            "status": "Handling conversationally (using memory)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped"]
        }
    
    return {
        "current_query": decision,
        "status": f"Technical research needed. Searching for: {decision}",
        "plan": ["Intent: Technical", f"Search Term: {decision}"]
    }
