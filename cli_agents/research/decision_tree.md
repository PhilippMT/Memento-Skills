# Research & Decision Trees: Adapting Memento-Skills to CLI Coding Agents

## 1. Executive Summary

This document presents the research analysis and decision trees for adapting
the Memento-Skills self-evolving agent framework to CLI coding agents
(GitHub Copilot CLI and Kiro). The goal is a **fully automatic** integration
that brings Memento's skill discovery, execution, and reflective learning
capabilities to these platforms via hooks, skills, and an ACP wrapper tool.

---

## 2. Problem Decomposition

```
GOAL: Adapt Memento-Skills → CLI Coding Agents (Copilot CLI, Kiro)
│
├── Q1: What concepts from Memento-Skills are transferable?
│   ├── Skill discovery & retrieval (hybrid search)
│   ├── Skill execution (ReAct loop with tool bridge)
│   ├── Reflective learning (success/failure feedback)
│   ├── Self-evolution (skill creation & improvement)
│   └── Safety policies (tool gate, path validation)
│
├── Q2: What integration points do CLI agents offer?
│   ├── Copilot CLI: hooks.json, .github/skills/, .github/agents/
│   ├── Kiro: agent hooks, steering files, .kiro/ directory
│   └── Both: shell command execution, stdin/stdout JSON protocol
│
├── Q3: How should Memento-Skills be exposed?
│   ├── Option A: Direct Python integration (subprocess calls)
│   ├── Option B: ACP server + wrapper tool (REST API)
│   ├── Option C: MCP server (stdio protocol)
│   └── Option D: Hybrid (ACP server + hook scripts)
│
└── Q4: How to make it fully automatic?
    ├── Auto-detection of CLI agent environment
    ├── Auto-installation of hooks and skills
    ├── Auto-skill discovery on every tool call
    └── Auto-reflection after every session
```

---

## 3. Decision Tree 1: Integration Architecture

```
START: Choose integration architecture
│
├─[D1] Can the CLI agent call external APIs?
│  ├── YES (via hooks shell scripts + curl/httpx)
│  │   ├─[D2] Should Memento run as a persistent server?
│  │   │  ├── YES → ACP Server Mode
│  │   │  │   ├── PRO: Standard protocol, multi-client support
│  │   │  │   ├── PRO: Session persistence, skill caching
│  │   │  │   ├── PRO: ACP ecosystem compatibility
│  │   │  │   ├── CON: Requires daemon process management
│  │   │  │   └── ★ CHOSEN: Best balance of power and standardization
│  │   │  │
│  │   │  └── NO → Subprocess Per-Call Mode
│  │   │      ├── PRO: Simpler, no daemon needed
│  │   │      ├── CON: Slow startup (bootstrap each call)
│  │   │      ├── CON: No session persistence
│  │   │      └── REJECTED: Too slow for interactive use
│  │   │
│  │   └─[D3] Which protocol for the server?
│  │      ├── ACP (Agent Connect Protocol)
│  │      │   ├── PRO: Open standard for agent-to-agent communication
│  │      │   ├── PRO: OpenAPI/REST-based (easy to call from shell)
│  │      │   ├── PRO: Python SDK available (agntcy-acp)
│  │      │   └── ★ CHOSEN: Best fit for agent interoperability
│  │      │
│  │      ├── MCP (Model Context Protocol)
│  │      │   ├── PRO: Already in Memento dependencies
│  │      │   ├── CON: stdio-based (harder from hook scripts)
│  │      │   └── REJECTED: Not ideal for hook→server communication
│  │      │
│  │      └── Custom HTTP API
│  │          ├── PRO: Full flexibility
│  │          ├── CON: Non-standard, maintenance burden
│  │          └── REJECTED: Reinventing the wheel
│  │
│  └── NO
│      └── FALLBACK: Embed skills as static markdown documents
│          (Limited capability, no dynamic execution)
│
└── RESULT: ACP Server + Hook Scripts + Skill Format Conversion
```

---

## 4. Decision Tree 2: Hook Strategy

```
START: How to wire Memento into CLI agent hooks?
│
├─[D1] Which hook points are most valuable?
│  │
│  ├── sessionStart
│  │   ├── PURPOSE: Initialize Memento connection, warm caches
│  │   ├── ACTION: Start ACP server if not running
│  │   ├── ACTION: Load workspace skills into memory
│  │   └── ★ ESSENTIAL: Foundation for all other hooks
│  │
│  ├── preToolUse
│  │   ├── PURPOSE: Intercept tool calls for skill routing
│  │   ├── ACTION: Search Memento skills for relevant expertise
│  │   ├── ACTION: Inject skill context into agent prompts
│  │   ├── ACTION: Validate tool calls against safety policies
│  │   └── ★ ESSENTIAL: Core skill integration point
│  │
│  ├── postToolUse
│  │   ├── PURPOSE: Reflective learning from tool results
│  │   ├── ACTION: Record execution outcomes
│  │   ├── ACTION: Update skill utility scores
│  │   ├── ACTION: Trigger skill improvement on failures
│  │   └── ★ ESSENTIAL: Enables self-evolution
│  │
│  ├── sessionEnd
│  │   ├── PURPOSE: Persist learning, cleanup
│  │   ├── ACTION: Save session metrics
│  │   ├── ACTION: Trigger skill reflection
│  │   └── ★ IMPORTANT: Completes the learning loop
│  │
│  ├── userPromptSubmitted
│  │   ├── PURPOSE: Pre-analyze intent for skill matching
│  │   ├── ACTION: Warm skill cache based on prompt
│  │   └── NICE-TO-HAVE: Optimization only
│  │
│  └── errorOccurred
│      ├── PURPOSE: Error recovery via skill knowledge
│      ├── ACTION: Suggest recovery based on skill history
│      └── NICE-TO-HAVE: Enhanced error handling
│
├─[D2] How should hooks communicate with Memento?
│  │
│  ├── Option A: HTTP/REST via curl (in hook scripts)
│  │   ├── PRO: Universal, no dependencies
│  │   ├── PRO: Works on all platforms
│  │   └── ★ CHOSEN: Most portable
│  │
│  ├── Option B: Python subprocess (direct import)
│  │   ├── PRO: Full access to Memento APIs
│  │   ├── CON: Slow startup, Python version dependency
│  │   └── REJECTED: Too slow for synchronous hooks
│  │
│  └── Option C: Named pipe / Unix socket
│      ├── PRO: Fast, low-latency
│      ├── CON: Platform-specific
│      └── REJECTED: Not portable enough
│
└── RESULT: All 6 hooks implemented, HTTP/REST communication via ACP
```

---

## 5. Decision Tree 3: Skill Format Adaptation

```
START: How to make Memento skills available to CLI agents?
│
├─[D1] Are the skill formats compatible?
│  │
│  ├── Memento SKILL.md Format:
│  │   ├── YAML frontmatter: name, description, metadata.dependencies
│  │   ├── Markdown body: workflows, code examples, references
│  │   └── Optional: scripts/, references/ directories
│  │
│  ├── Copilot CLI SKILL.md Format:
│  │   ├── YAML frontmatter (optional)
│  │   ├── Markdown body: instructions for the agent
│  │   ├── Location: .github/skills/{name}/SKILL.md
│  │   └── Auto-loaded based on relevance
│  │
│  └── Kiro Skills Format:
│      ├── Markdown-based instructions
│      ├── Location: .kiro/ directory
│      └── Event-triggered activation
│  │
│  └── FINDING: Formats are structurally similar (YAML + Markdown)
│      but differ in metadata and activation semantics
│
├─[D2] Should we convert or wrap?
│  │
│  ├── Option A: Static Conversion (generate compatible files)
│  │   ├── PRO: Skills work natively in each platform
│  │   ├── PRO: No runtime dependency on Memento server
│  │   ├── CON: Loses dynamic skill discovery
│  │   ├── CON: No reflective learning
│  │   └── PARTIAL: Good for base skills, but insufficient alone
│  │
│  ├── Option B: Dynamic Wrapper (skill calls Memento at runtime)
│  │   ├── PRO: Full Memento capabilities at runtime
│  │   ├── PRO: Reflective learning preserved
│  │   ├── CON: Requires running Memento server
│  │   └── PARTIAL: Best for complex skills
│  │
│  └── Option C: Hybrid (static + dynamic)
│      ├── Convert simple skills to native format
│      ├── Complex skills use wrapper that calls ACP server
│      ├── Hook system enables dynamic skill discovery
│      └── ★ CHOSEN: Best of both worlds
│
└── RESULT: Hybrid approach - static conversion + dynamic wrapper skills
```

---

## 6. Decision Tree 4: Automation Strategy

```
START: How to make the entire process fully automatic?
│
├─[D1] How does the user install the integration?
│  │
│  ├── Option A: CLI command (`memento adapt --target copilot-cli`)
│  │   ├── PRO: Single command, discoverable
│  │   ├── PRO: Can detect environment automatically
│  │   └── ★ CHOSEN: Clean UX, fits existing CLI pattern
│  │
│  ├── Option B: Configuration file (add to config.json)
│  │   ├── PRO: Declarative
│  │   ├── CON: Requires manual file editing
│  │   └── REJECTED: Not "fully automatic" enough
│  │
│  └── Option C: Auto-detect on memento start
│      ├── PRO: Zero configuration
│      ├── CON: May surprise users
│      └── COMPLEMENTARY: Use with Option A
│
├─[D2] What should auto-setup include?
│  │
│  ├── 1. Detect target CLI agent (Copilot CLI vs Kiro)
│  ├── 2. Generate hooks configuration (hooks.json / .kiro hooks)
│  ├── 3. Generate hook scripts (shell scripts for each hook)
│  ├── 4. Convert builtin skills to target format
│  ├── 5. Start ACP server daemon (background process)
│  ├── 6. Verify connectivity
│  └── 7. Output success message with instructions
│
├─[D3] How to keep skills in sync?
│  │
│  ├── Option A: File watcher (daemon watches skill directory)
│  │   ├── PRO: Real-time sync
│  │   ├── CON: Resource overhead
│  │   └── COMPLEMENTARY: Use with periodic sync
│  │
│  ├── Option B: Hook-triggered sync (on sessionStart)
│  │   ├── PRO: Only syncs when needed
│  │   ├── PRO: Lightweight
│  │   └── ★ CHOSEN: Efficient and reliable
│  │
│  └── Option C: Manual sync command
│      ├── PRO: User control
│      ├── CON: Not automatic
│      └── REJECTED: Breaks "fully automatic" requirement
│
└── RESULT: CLI command triggers auto-setup, hooks keep sync at session start
```

---

## 7. Decision Tree 5: ACP Wrapper Tool Design

```
START: How to design the ACP wrapper tool?
│
├─[D1] What operations should the wrapper expose?
│  │
│  ├── /discover  → Search skills by query (maps to SkillGateway.discover)
│  ├── /execute   → Execute a skill (maps to SkillGateway.execute)
│  ├── /reflect   → Record execution outcome (maps to reflection phase)
│  ├── /health    → Check server status
│  ├── /skills    → List all available skills
│  └── /sync      → Sync skills to target platform format
│
├─[D2] How should the ACP server be managed?
│  │
│  ├── Lifecycle:
│  │   ├── Start: `memento serve` (background daemon)
│  │   ├── Stop:  `memento serve --stop`
│  │   ├── Status: `memento serve --status`
│  │   └── Auto-start: Hook scripts start if not running
│  │
│  ├── Configuration:
│  │   ├── Port: configurable (default 47200)
│  │   ├── Host: localhost only (security)
│  │   └── Auth: optional token-based
│  │
│  └── ★ CHOSEN: Daemon with auto-start from hooks
│
├─[D3] How should the wrapper handle skill execution?
│  │
│  ├── Flow:
│  │   1. Hook script receives tool call context (JSON stdin)
│  │   2. Script extracts tool name and arguments
│  │   3. Script calls ACP server /discover with context
│  │   4. If relevant skill found:
│  │   │   a. Inject skill knowledge into agent context
│  │   │   b. Optionally execute skill directly
│  │   │   c. Return enhanced context to agent
│  │   5. If no skill found:
│  │   │   a. Pass through (allow default behavior)
│  │   6. After execution (postToolUse):
│  │   │   a. Record outcome via /reflect
│  │   │   b. Update skill utility scores
│  │
│  └── ★ CHOSEN: Discovery-first approach with optional execution
│
└── RESULT: ACP server with 6 endpoints, daemon lifecycle, discovery-first flow
```

---

## 8. Final Architecture (Chosen Path)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Coding Agent                              │
│              (GitHub Copilot CLI / Kiro)                         │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ sessionStart │  │ preToolUse  │  │ postToolUse             │ │
│  │    Hook      │  │    Hook     │  │    Hook                 │ │
│  └──────┬───────┘  └──────┬──────┘  └──────┬──────────────────┘ │
│         │                 │                 │                    │
└─────────┼─────────────────┼─────────────────┼────────────────────┘
          │                 │                 │
          │ HTTP/REST       │ HTTP/REST       │ HTTP/REST
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ACP Wrapper Server                             │
│                   (memento serve)                                 │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ /health  │  │/discover │  │ /execute │  │  /reflect      │  │
│  └──────────┘  └────┬─────┘  └────┬─────┘  └────┬───────────┘  │
│                     │             │              │               │
└─────────────────────┼─────────────┼──────────────┼───────────────┘
                      │             │              │
                      ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Memento-Skills Core                            │
│                                                                  │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────┐  │
│  │ SkillGateway │  │ SkillExecutor  │  │ Reflection Engine   │  │
│  │  .discover() │  │  .execute()    │  │  .assess()          │  │
│  └──────────────┘  └────────────────┘  └─────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────┐  │
│  │ SkillStore   │  │ ToolBridge     │  │ ContextManager      │  │
│  │ (file+db+vec)│  │ (safe exec)    │  │ (token-aware)       │  │
│  └──────────────┘  └────────────────┘  └─────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Components

| Component | Purpose | Files |
|-----------|---------|-------|
| **ACP Wrapper Server** | Expose Memento via REST API | `cli_agents/wrapper/acp_server.py` |
| **ACP Client Library** | Call server from hook scripts | `cli_agents/wrapper/acp_client.py` |
| **Copilot Hooks** | Integration with Copilot CLI | `cli_agents/hooks/copilot/` |
| **Kiro Hooks** | Integration with Kiro IDE/CLI | `cli_agents/hooks/kiro/` |
| **Skill Converter** | Transform Memento → platform format | `cli_agents/skills/converter.py` |
| **Auto Bootstrap** | One-command setup | `cli_agents/auto/bootstrap.py` |
| **Agent Detector** | Detect CLI agent environment | `cli_agents/auto/detector.py` |
| **Configuration** | Settings for CLI integration | `cli_agents/config/settings.py` |

---

## 10. Key Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | ACP Server + Hooks | Standard protocol, persistent sessions |
| Protocol | ACP (REST/OpenAPI) | Open standard, curl-friendly for hooks |
| Hook Communication | HTTP via curl | Universal, no dependencies in scripts |
| Skill Adaptation | Hybrid (static + dynamic) | Native skills + runtime enhancement |
| Automation | CLI command + auto-detect | Single command setup, zero config after |
| Server Lifecycle | Daemon with auto-start | Always available, hooks start if needed |
| Sync Strategy | Session-start triggered | Efficient, only when needed |
