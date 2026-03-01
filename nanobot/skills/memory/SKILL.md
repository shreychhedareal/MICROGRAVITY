---
name: memory
description: Two-layer memory system with grep-based recall.
always: true
---

# Memory

## Structure

- **Long-term memory**: Stores facts, preferences, project context, and relationships. It is always loaded into your context.
- **History log**: An append-only event log. NOT loaded into context. Search it when you need to recall past events.

## Search Past Events

Use the `search_history` tool to query the log:
- Search for specific keywords or phrases: `search_history(query="deadline")`

## Semantic Search (Vector Similarity)

Use the `semantic_search` tool for **conceptual** searches that go beyond exact keyword matching:
- `semantic_search(query="conversations about performance", collection="history")` — finds related history entries
- `semantic_search(query="user preferences", collection="memory")` — finds related long-term memory chunks

Semantic search is best when you need to find related content that may not use the exact same words.

## When to Update Memory

Write important facts immediately using the `update_memory` tool. Ensure you keep existing facts when updating!
- User preferences ("I prefer dark mode")
- Project context ("The API uses OAuth2")
- Relationships ("Alice is the project lead")

## Auto-consolidation

Old conversations are automatically summarized and appended to the history log when the session grows large. Long-term facts are extracted to the long-term memory. You don't need to manage this consolidation process.
