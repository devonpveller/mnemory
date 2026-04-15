Please create the following seed memories in order. Use `add_memory` with exactly the parameters shown. Wait for confirmation after each before proceeding to the next.

---

## Memory 1 of 3 — Memory Protocol: What to Store

```
add_memory(
  content="""Memory Protocol: What to Store

Store information proactively — no user prompt needed. Dedup is automatic. Use add_memory for:

1. User knowledge & identity: name, location, job, family, pets, milestones, expertise, skills, experience levels, ongoing projects, goals, deadlines.

2. Preferences & interaction patterns: display/formatting preferences, communication style (verbosity, tone, formality), tool/technology preferences, domain-specific conventions. Use accumulated preferences to anticipate what the user wants before they ask.

3. Decisions & conclusions: architectural decisions, tool selections, policy choices, and the reasoning behind them — never re-litigate settled decisions.

4. User feedback & self-learning: when corrected or dissatisfied, store what happened, what the user wanted instead, and the lesson as a concise reusable rule. Apply lessons to future similar requests. This is the primary self-improvement loop.

5. Performance patterns & tool mastery: which tools and response strategies work best, effective response structures, prompting patterns that succeed, error patterns and resolutions. Store as actionable rules.

6. Agent skills & reusable procedures: multi-step procedures or tool chains that work reliably. Capture skill name, trigger conditions, steps, and user-specific constraints. Follow stored skills on matching requests; update when refined.""",
  memory_type="procedural",
  importance="critical",
  pinned=True,
  categories=["preferences"],
  infer=False
)
```

---

## Memory 2 of 3 — Memory Protocol: Boundaries and Search

```
add_memory(
  content="""Memory Protocol: Boundaries and Search

DO NOT STORE: greetings, small talk, generic questions, trivial or ephemeral details, information already in memory, bulky working data (use short-term memory instead), raw conversation transcripts (extract the insight, discard the noise).

SEARCH BEFORE ASKING: before answering questions about the user's background, preferences, projects, or past decisions — and the answer is not already in recalled context — search with find_memories. Better to search and find nothing than to miss relevant context. Do not ask the user to provide information that may already be in memory.

SHORT-TERM MEMORY: use Fileshed (shed_* functions) for drafts, scratch notes, intermediate results, working code, research notes, data tables, and API responses. When an artifact crystallizes into a durable fact, decision, preference, or reusable skill, promote it to long-term memory with add_memory.""",
  memory_type="procedural",
  importance="critical",
  pinned=True,
  categories=["preferences"],
  infer=False
)
```

---

## Memory 3 of 3 — Memory Protocol: Recalled Context Rules

```
add_memory(
  content="""Memory Protocol: Recalled Context Rules

Memories recalled into a conversation are facts you already know. Follow these rules:

1. Treat recalled memories as first-class context — never ignore them.
2. Do not ask the user for information that is already in your recalled memories.
3. Weave remembered facts naturally into responses to make conversations feel personal and continuous.
4. Behavioral instructions recalled from memory (tagged procedural/critical) define how you use the memory system. Follow them.
5. Memories may originate from different agents, tools, or conversations. Treat all recalled memories as authoritative regardless of origin.
6. When you encounter a recalled skill memory that matches the current request, follow its stored procedure and adapt as needed.""",
  memory_type="procedural",
  importance="critical",
  pinned=True,
  categories=["preferences"],
  infer=False
)
```

---

After all three are confirmed, summarize what was created and confirm the memory protocol is active.
