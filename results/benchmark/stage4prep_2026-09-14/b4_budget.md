# B4 frontier budget, authenticated-account check

14 September 2026, account probed read-only through the signed-in Codex app-server at **17:59:31 UTC**; the redacted machine-readable response is [account_limits.json](account_limits.json). No API key, credit purchase, reset credit, model call, or account mutation was used for this probe.

The account's rate-limit response reported plan code `prolite`, a `codex` primary window of **10,080 minutes (one week)**, **41% used**, no secondary window in that bucket, no available credit balance, and next reset **19 September 2026 15:30:29 UTC**. It did **not** report an absolute message, request, or token cap. `account/usage/read` reported 397,456,621 lifetime tokens and 185,440,562 peak daily tokens, but those are usage history, not a remaining quota. [Official Codex documentation](https://learn.chatgpt.com/docs/app-server) defines `usedPercent`, window duration and `resetsAt` as the live account-rate fields. [Official plan guidance](https://learn.chatgpt.com/docs/pricing) says local-message estimates vary with model and task complexity, plan windows reset, and weekly limits may apply; it does not turn this account's 41% into a token allowance.

The single Stage 3i-d B4 cell used 858.744 seconds, 1,442,752 summed input/context tokens (1,319,680 cached; 123,072 uncached), and 10,460 output tokens. At **one sample per 146 items** and identical per-item behavior, the mechanical projection is:

| Quantity | Projection |
|---|---:|
| Serial wall clock | 125,376.624 s = **34.83 h** |
| Input/context tokens, summed | **210,641,792** |
| Of those, cached input if the observed cache ratio persists | 192,673,280 |
| Uncached input if the observed cache ratio persists | 17,968,512 |
| Output tokens | 1,527,160 |

This is a **projection**, not a measured cohort cost. Other sequences, response counts, tool errors and cache behavior can change it. All observed Stage 3i-d per-response prompts were below 272,000 input tokens, so the published >272K per-request API surcharge would not have applied to that cell; this is not guaranteed for every future item.

The authenticated ChatGPT plan is already paid for, so its **marginal dollar charge within available allowance is not an API token bill**, but the service did not expose a per-cell dollar cost or an absolute remaining allowance. The 146-cell/210.6M-token sweep **cannot be certified as reachable within the current 59% weekly remainder** from this account response alone. The absolute plan quota, weighted consumption per 14-minute B4 cell, effects of other account activity, and credit price remain unknown. A calendar schedule is therefore conditional: 34.83 serial compute hours could fit across several days, but no guaranteed completion date or number of weekly resets is defensible. Do not commit the cohort on a 41%-used percentage alone.

For a separately authorized **API-key path**, the [official GPT-5.6 Sol rates](https://developers.openai.com/api/docs/models/gpt-5.6-sol) on this date are $4 per million uncached input tokens, $0.40 per million cached input tokens, and $20 per million output tokens, before any other billable service fees. Applying those rates to the measured cell gives **$1.22936 per cell** and **$179.49 for 146** if its cache ratio and token counts repeat. With **no cache discount**, the same tokens cost **$5.980208 per cell / $873.11 for 146**. Cache writes, if any, have their own published charge; none were observed in the cell. This is a price estimate, not an API bill: no OpenAI API key was available in the environment, account API tier/access was not verified, and the API route could change the harness or caching. The API is **not proven cheaper** than the included ChatGPT allowance, but it is priceable; once the plan is exhausted, the credit-versus-API comparison is unknown without the actual credit offer.

**Budget disposition: B4 is technically reachable for one sealed cell, but cohort-scale account reachability and cheapest paid route remain UNDEMONSTRATED.** The panel should require an absolute quota or a measured marginal `usedPercent` change per matched B4 cell and an account billing decision before opening 146-item B4.
