import os
import time
import logfire

# Limit OpenMP threads to prevent CPU over-subscription and AVX crashes on containerized VMs
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

_ranker = None
_ranker_failed = False


def _get_ranker():
    """
    Initializes the FlashRank engine lazily. 
    If CPU/ONNX issues occur (e.g. SIGILL Status 132 on cloud VMs without AVX2), 
    it falls back cleanly without crashing the container.
    """
    global _ranker, _ranker_failed
    if _ranker_failed:
        return None

    if _ranker is None:
        logfire.info("🧠 Initializing FlashRank Model (TinyBERT) locally...")
        try:
            from flashrank import Ranker
            _ranker = Ranker(cache_dir="/tmp/flashrank")
        except Exception as e:
            logfire.warning(f"⚠️ FlashRank init failed on host CPU ({e}). Reranker will fallback to direct Qdrant ranking.")
            _ranker_failed = True
            _ranker = None
    return _ranker


def rerank_documents(query: str, documents: list[str], top_n: int = 5) -> list[str]:
    """
    Refines retrieval results by re-scoring documents against the query semantically.
    Falls back gracefully to Qdrant vector order if reranking is unavailable or fails.
    """
    if not documents:
        return []

    ranker = _get_ranker()
    if ranker is None:
        return documents[:top_n]

    start_time = time.time()
    try:
        from flashrank import RerankRequest
        passages = [{"id": i, "text": doc} for i, doc in enumerate(documents)]
        request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)
        
        reranked_docs = [res['text'] for res in results[:top_n]]
        duration = time.time() - start_time
        top_score = results[0]['score'] if results else 'N/A'
        logfire.info(f"✅ [Reranker] Done in {duration:.2f}s. Top score: {top_score}")
        return reranked_docs

    except Exception as e:
        logfire.error(f"❌ [Reranker] Reranking failed: {e}. Falling back to Qdrant order.")
        return documents[:top_n]
