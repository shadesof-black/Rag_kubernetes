import logfire
from app.agents.state import AgentState
from app.gateway import get_langchain_llm, portkey_client, extract_cache_status
from app.config import settings


def generate_node(state: AgentState):
    """
    Synthesizes a response using both Documentation Context AND Conversation History.
    Uses ChatGroq with Portkey fallback to guarantee response availability.
    """
    query = state["current_query"]

    history_str = ""
    for msg in state["messages"][:-1]:
        role_val = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", "user")
        role = "User" if role_val in ("user", "human") else "Assistant"
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        history_str += f"{role}: {content}\n"

    user_msg = ""
    if state["messages"]:
        last_msg = state["messages"][-1]
        user_msg = last_msg.get("content") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")

    if query == "CONVERSATIONAL":
        logfire.info("Generating conversational response using memory.")
        prompt = f"""
        You are a friendly and helpful Enterprise AI Assistant.
        Answer the user's latest message using the CONVERSATION HISTORY below.

        CONVERSATION HISTORY:
        {history_str}

        LATEST MESSAGE:
        "{user_msg}"
        """
    else:
        logfire.info("Generating technical RAG response.")
        max_context_chars = 25000
        full_context = ""

        for doc in state["documents"]:
            if len(full_context) + len(doc) < max_context_chars:
                full_context += doc + "\n\n"
            else:
                logfire.warning("Context truncated to fit Groq TPM limits.")
                break

        prompt = f"""
        You are a Senior Technical Architect.
        Answer the question using the TECHNICAL CONTEXT provided.

        TECHNICAL CONTEXT:
        {full_context}

        CONVERSATION HISTORY:
        {history_str}

        USER QUESTION:
        "{user_msg}"
        """

    with logfire.span("✍️ LLM Synthesis"):
        try:
            content = None
            is_cache_hit = False

            if portkey_client:
                try:
                    response = portkey_client.chat.completions.create(
                        model=settings.GROQ_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1
                    )
                    content = response.choices[0].message.content
                    cache_status = extract_cache_status(response)
                    is_cache_hit = cache_status == "HIT"
                except Exception:
                    pass

            if content is None:
                llm = get_langchain_llm(feature="responder")
                response = llm.invoke(prompt)
                content = response.content

            if is_cache_hit:
                logfire.info("⚡ Gateway Cache Hit — response served from Portkey cache.")
                plan_update = state["plan"] + ["Cache: Hit ⚡"]
                status = "Cache hit — instant response."
            else:
                logfire.info("✅ Response synthesised via LLM.")
                plan_update = state["plan"]
                status = "Response generated."

            return {
                "final_answer": content,
                "status": status,
                "plan": plan_update,
                "messages": [{"role": "assistant", "content": content}]
            }

        except Exception as e:
            logfire.error(f"LLM Generation failed: {e}")
            raise e

