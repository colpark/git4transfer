# Stage 3i-b preflight

14 September 2026 UTC. `codex login` was started as specified. It printed a local browser callback URL and awaited account authentication. A subsequent `codex login status` returned `Not logged in`; the callback listener was still waiting. The login process was then interrupted rather than left running. No credential was recovered or substituted.

| Check | Result |
|---|---|
| Stored ChatGPT session restored | No |
| Authenticated models endpoint HTTP 200 | Not demonstrated; no active session |
| Exact model ID / reasoning effort / date pinned | None / none / 14 September 2026 |
| Native-tool and multi-agent flags for a subject run | Not configured; no subject run |
| Fallback metadata warning | Not observed; no model request |

The Stage 3i logout correction is accepted: the ChatGPT session is the intended frontier path. This attempt did not chase an API key. [Codex authentication documentation](https://developers.openai.com/codex/auth) describes the browser flow required after `codex login`.
