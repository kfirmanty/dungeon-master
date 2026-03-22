"""
RAG retrieval pipeline — the "read" side of the system.

    Question → Embed → Vector Search → Build Prompt → LLM → Answer

WHAT IS RAG (Retrieval-Augmented Generation)?

The problem: LLMs have knowledge from training data, but they don't know about
YOUR specific books. If you ask "What did Elizabeth think of Darcy?", the LLM
might answer from general knowledge or hallucinate details.

The solution: RAG is like giving the LLM an open-book exam:
1. RETRIEVE relevant passages from our vector database
2. AUGMENT the prompt by pasting those passages as context
3. GENERATE an answer grounded in the actual text

This way, the LLM answers FROM the book, not from memory. It can cite specific
chapters and quote actual text.
"""

from uuid import UUID

import psycopg

from bookworm.config import Settings
from bookworm.embeddings.base import EmbeddingProvider
from bookworm.llm.base import LLMProvider
from bookworm.retrieval.search import find_similar_chunks
from bookworm.models import ChunkResult, QueryResult


# The system prompt constrains the LLM's behavior for our specific use case.
# Each instruction serves a purpose — see comments inline.
SYSTEM_PROMPT2 = """You are a helpful literary assistant that answers questions about books.
Use ONLY the provided context passages to answer the question.
If the answer cannot be found in the context, say "I don't have enough context to answer that question."
Always reference which chapter the information comes from when possible."""
# "Use ONLY the provided context" → prevents hallucination from training data
# "If the answer cannot be found"  → gives the LLM an escape hatch instead of
#                                     making up an answer when context is insufficient
# "Reference which chapter"        → encourages source attribution for verifiability

SYSTEM_PROMPT = """You are a helpful literary assistant that answers questions about books.
You are also expert comedian so all your response are funny.
Use ONLY the provided context passages to answer the question.
If the answer cannot be found in the context, say "I don't have enough context to answer that question."
Always reference which chapter the information comes from when possible."""


def _build_user_prompt(question: str, sources: list[ChunkResult], book_title: str) -> str:
    """Assemble the user prompt with retrieved context passages.

    PROMPT STRUCTURE MATTERS:
    - Context passages come FIRST, before the question
    - Each passage is labeled with its chapter for attribution
    - Passages are separated by "---" for clear visual boundaries
    - The question comes LAST

    Why question last? LLMs attend most strongly to the beginning and end
    of their input (the "lost in the middle" phenomenon, Liu et al. 2023).
    Placing the question at the end ensures the model focuses on it.
    """
    context_parts = []
    for source in sources:
        chapter_label = ""
        if source.chapter_number is not None:
            chapter_label = f"Chapter {source.chapter_number}"
            if source.chapter_title:
                chapter_label += f": {source.chapter_title}"
        elif source.chapter_title:
            chapter_label = source.chapter_title

        header = f"[{chapter_label}]" if chapter_label else "[Unknown section]"
        context_parts.append(f"{header}\n{source.content}")

    context = "\n---\n".join(context_parts)

    return f"""Context passages from "{book_title}":

{context}

Question: {question}"""


def query(
    question: str,
    settings: Settings,
    conn: psycopg.Connection,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    book_id: UUID | None = None,
    book_title: str = "Unknown",
) -> QueryResult:
    """Execute the full RAG pipeline: embed → search → prompt → generate.

    This is where all the pieces come together:
    1. The question is embedded using the SAME model that embedded the chunks.
       This is critical — vectors from different models live in different
       spaces and can't be meaningfully compared.
    2. pgvector finds the chunks whose embeddings are closest to the question's.
    3. Those chunks become the "context" in our prompt to the LLM.
    4. The LLM generates an answer grounded in that context.
    """
    # Step 1: Embed the question
    # The question embedding lives in the same 384-dim space as the chunk
    # embeddings, so cosine similarity between them is meaningful.
    query_embedding = embedding_provider.embed_query(question)

    # Step 2: Vector search — find the most relevant chunks
    sources = find_similar_chunks(
        conn,
        query_embedding,
        top_k=settings.top_k,
        book_id=book_id,
    )

    if not sources:
        return QueryResult(
            answer="No relevant passages found. Have you ingested a book yet?",
            sources=[],
        )

    # Step 3: Build the prompt with retrieved context
    user_prompt = _build_user_prompt(question, sources, book_title)

    # Step 4: Call the LLM
    answer = llm_provider.generate(SYSTEM_PROMPT, user_prompt)

    return QueryResult(answer=answer, sources=sources)
