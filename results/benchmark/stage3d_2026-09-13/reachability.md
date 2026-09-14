# Stage 3d sequential remount ladder

The source tool block includes Codex wrapper definitions; the forwarded block is the actual function set sent to the model. First, maximum and summed prompt tokens include both the call and post-tool model requests; headroom uses the maximum single request. A no-call outcome is not a success.

| Servers | Added | Forwarded tool bytes | Functions | First prompt | Max prompt | Sum prompt | Min 32K headroom | MCP attempts/successes | Verdict |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | probe | 233 | 1 | 6299 | 6577 | 12876 | 26191 | 1/1 | PASS |
| 2 | record | 840 | 3 | 6475 | 6753 | 13228 | 26015 | 1/1 | PASS |
| 3 | classical | 3241 | 10 | 7209 | 7495 | 14704 | 25273 | 1/1 | PASS |
| 4 | analysis | 3826 | 12 | 7381 | 7667 | 15048 | 25101 | 1/1 | PASS |
| 5 | predictive | 4451 | 14 | 7571 | 7851 | 15422 | 24917 | 1/1 | PASS |
| 6 | generative | 4774 | 15 | 7671 | 7947 | 15618 | 24821 | 1/1 | PASS |
| 7 | physics | 5640 | 18 | 7947 | 8235 | 16182 | 24533 | 1/1 | PASS |
| 8 | lit | 5921 | 19 | 8032 | 8316 | 16348 | 24452 | 1/1 | PASS |

No server count failed; all eight mounted grants passed the real echo receipt audit.
