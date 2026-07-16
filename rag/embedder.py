from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from config.settings import LMSTUDIO_BASE_URL, LMSTUDIO_EMBEDDING_MODEL


def get_embedder() -> OpenAILikeEmbedding:
    """
    Returns an embedding client pointed at LM Studio's local server.
    Uses the OpenAI-compatible API that LM Studio exposes on port 1234.
    The api_key value is required by the client library but not validated
    by LM Studio — any non-empty string works.
    """
    return OpenAILikeEmbedding(
        model_name=LMSTUDIO_EMBEDDING_MODEL,
        api_base=LMSTUDIO_BASE_URL,
        api_key="lmstudio",
    )
