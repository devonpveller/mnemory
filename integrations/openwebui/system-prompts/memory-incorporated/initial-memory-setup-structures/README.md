# Initial Memory Setup

One-time setup to seed your mnemory instance with the behavioral protocol that all agents follow. After running this, any agent with the compact **Part A** memory section in its system prompt (see `memory-system-prompt-template.md`) will automatically receive these instructions via the recall pipeline.

## Files

| File               | Purpose                                                                                                                |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| `system-prompt.md` | System prompt for the setup agent — a minimal "Memory Administrator" persona that executes `add_memory` calls verbatim |
| `chat-prompt.md`   | User message to paste into the conversation — contains the 3 seed memories with exact parameters                       |

## How to use

1. **Create a temporary agent** (or use any agent with mnemory MCP tools available).
2. **Set the system prompt** to the contents of `system-prompt.md`.
3. **Paste the contents of `chat-prompt.md`** as your first message.
4. The agent will create 3 pinned procedural memories, confirming each one.
5. **Verify** by running `get_core_memories` in any conversation — the protocol memories should appear.
6. You can delete the temporary agent afterward; the memories persist.

## What gets created

| #   | Title                                   | Size       | Purpose                                                                  |
| --- | --------------------------------------- | ---------- | ------------------------------------------------------------------------ |
| 1   | Memory Protocol: What to Store          | ~930 chars | 6-category guide for proactive memory storage                            |
| 2   | Memory Protocol: Boundaries and Search  | ~690 chars | What not to store, search-before-asking rule, short-term memory guidance |
| 3   | Memory Protocol: Recalled Context Rules | ~600 chars | How to treat recalled memories and behavioral instructions               |

All three are stored as: `memory_type=procedural`, `importance=critical`, `pinned=true`, `infer=false`, `categories=["preferences"]`.

## Prerequisites

- mnemory instance running with MCP tools accessible
- `ALLOW_CLIENT_INFER` not set to `false` (defaults to `true`) — required for `infer=False` in `add_memory`
- `MAX_CORE_CONTEXT_LENGTH` should be at least 4000 (default) to accommodate the protocol memories plus user memories

## Notes

- **Run once per mnemory instance.** The memories persist across all conversations and agents.
- **Idempotent:** mnemory deduplicates, so running again won't create duplicates (though with `infer=False` dedup is not applied — check for existing protocol memories first with `find_memories("Memory Protocol")`).
- **Customizable:** edit `chat-prompt.md` to adjust the behavioral rules before running. For example, remove the Fileshed/short-term memory paragraph if you don't use Fileshed.
- **Total footprint:** ~2,220 chars across 3 memories, well within the 4,000-char core context default.
