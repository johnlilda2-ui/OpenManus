import re
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import KnowledgeDocument, MemoryEntry


def _terms(query: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9_]{2,}", query.lower()) if term]


def _score(text: str, terms: Sequence[str], importance: int = 0) -> int:
    haystack = text.lower()
    score = importance
    for term in terms:
        score += haystack.count(term) * 10
    return score


async def search_memory(session: AsyncSession, *, owner_id: str, project_id: str | None, query: str, limit: int = 8) -> list[MemoryEntry]:
    result = await session.scalars(
        select(MemoryEntry)
        .where(
            MemoryEntry.owner_id == owner_id,
            (MemoryEntry.project_id == project_id) | (MemoryEntry.project_id.is_(None)),
        )
        .order_by(MemoryEntry.updated_at.desc())
        .limit(max(limit * 8, 40))
    )
    rows = result.all()
    terms = _terms(query)
    ranked = sorted(
        rows,
        key=lambda row: _score(f"{row.key or ''} {row.content}", terms, row.importance),
        reverse=True,
    )
    return ranked[:limit]


async def search_knowledge(session: AsyncSession, *, owner_id: str, project_id: str, query: str, limit: int = 8) -> list[KnowledgeDocument]:
    result = await session.scalars(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.owner_id == owner_id, KnowledgeDocument.project_id == project_id)
        .order_by(KnowledgeDocument.updated_at.desc())
        .limit(max(limit * 8, 40))
    )
    rows = result.all()
    terms = _terms(query)
    ranked = sorted(rows, key=lambda row: _score(f"{row.title} {row.content}", terms), reverse=True)
    return ranked[:limit]


def build_context(*, prompt: str, recent_messages: Sequence, memories: Sequence[MemoryEntry], documents: Sequence[KnowledgeDocument], max_chars: int = 18000) -> str:
    sections: list[str] = []
    if recent_messages:
        conversation = "\n".join(f"{message.role}: {message.content}" for message in recent_messages[-12:])
        sections.append(f"RECENT CONVERSATION:\n{conversation}")
    if memories:
        memory_text = "\n".join(f"- [{memory.kind}] {memory.key or 'memory'}: {memory.content}" for memory in memories)
        sections.append(f"RELEVANT PERSISTENT MEMORY:\n{memory_text}")
    if documents:
        knowledge_text = "\n\n".join(f"### {document.title}\n{document.content[:4000]}" for document in documents)
        sections.append(f"PROJECT KNOWLEDGE:\n{knowledge_text}")
    if not sections:
        return prompt
    context = "\n\n".join(sections)
    return (
        "Use the following persisted context as background. Treat it as potentially stale "
        "and verify important claims before acting.\n\n"
        f"{context}\n\nCURRENT REQUEST:\n{prompt}"
    )[:max_chars]
