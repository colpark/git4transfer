# Stage 3i preflight — blocked at model authentication

14 September 2026, 14:32 UTC. Codex CLI: `codex-cli 0.154.0`.

1. `codex login status` reported **Logged in using ChatGPT** before the required logout. `codex logout` reported **Successfully logged out**; a second status check reported **Not logged in**. A stored ChatGPT session therefore was present. Whether it affected any earlier custom-provider run is **unknown**; this preflight does not establish that it did.
2. Neither `OPENAI_API_KEY` nor `CODEX_API_KEY` is set in this shell. An unauthenticated `GET https://api.openai.com/v1/models` returned HTTP **401**. The models endpoint could not provide an available exact model ID, so no model was pinned. No name was substituted from memory.
3. The local feature listing shows `multi_agent=true`, `shell_tool=true`, `unified_exec=true`, and `apps=true` by default. No subject run was launched. An MCP-only, single-agent grant with these features disabled was **not verified**, so it is not reported as passed. Ultra/subagent behavior was likewise not tested. Any future cell must explicitly disable these features and verify the actual model-visible grant before execution.
4. The reported fallback-model-metadata warning was not observed or evaluated, because no frontier model request was made. It is **unknown** for this control, not a failure cause.

The [Codex authentication documentation](https://developers.openai.com/codex/auth) describes the login/logout behavior. The [Models API](https://developers.openai.com/api/reference/resources/models) requires an authenticated request to list exact model IDs. The [Codex configuration reference](https://developers.openai.com/codex/config-reference) documents the native-tool and multi-agent feature switches. No secret value was printed or written to these artifacts.
