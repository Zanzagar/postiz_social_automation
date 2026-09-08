# Claude on a Server — Auth, Terms, and Cost — Research

Date: 2026-09-07 (all URLs fetched 2026-09-07/08 UTC; local measurement 2026-09-08 UTC)
Sources: code.claude.com/docs (authentication, headless, github-actions, legal-and-compliance, agent-sdk overview/quickstart/hosting, costs, model-config), anthropic.com/legal (consumer-terms, commercial-terms, aup), support.claude.com (Agent SDK plan, Pro/Max + Claude Code, log-in, usage credits, API billing), platform.claude.com/docs (pricing, prompt-caching, batch-processing, rate-limits), claude.com/pricing, anthropic.com/news/claude-for-nonprofits, claude.com/solutions/nonprofits, academy.claude.com. Secondary (flagged where used): theregister.com. Local verification: `claude --version`, one `claude -p --output-format json` call, `grep` of `src/content_engine`.

Question: the FastAPI app shells out to `claude -p … --model sonnet` (`src/content_engine/generator.py`, `api/routes/media.py`, `api/routes/calendar_plan.py`) on the maintainer's laptop, authenticated by his personal Claude Max OAuth login, so generation costs $0 per call. If the app moves to a cloud server and other staff use it: (1) may the Max subscription's OAuth credentials (browser login, or a `claude setup-token` / `CLAUDE_CODE_OAUTH_TOKEN`) power that server-side app? (2) what are the sanctioned alternatives and what do they cost?

## TL;DR

| | Verdict |
|---|---|
| **Can the Max OAuth / `setup-token` run the server app for other staff?** | **No.** The Consumer Terms forbid sharing or making an Account available to anyone else and forbid automated access except via an API key "or where we otherwise explicitly permit it"; Claude Code's legal page says OAuth is "intended exclusively for purchasers of Claude … subscription plans" for "ordinary use of Claude Code and other native Anthropic applications", that developers "should use API key authentication", and that Anthropic "does not permit third-party developers to … route requests through Free, Pro, or Max plan credentials on behalf of their users". The June 2026 help-center article adds: "Teams running shared production automation should use Claude Platform with an API key". A one-person `claude -p` script on the maintainer's own machine is tolerated ("ordinary, individual usage"); a multi-user server is not. |
| **Sanctioned path** | A **Claude Console (Claude Platform) organization in the nonprofit's name + an API key** (Commercial Terms, prepaid pay-as-you-go). Call the Messages API directly with the `anthropic` Python SDK and put `cache_control` on the stable brand/knowledge prefix. `claude -p` and the Agent SDK also run headless with `ANTHROPIC_API_KEY` (documented, supported), but the CLI harness adds ~18.6k input tokens per call (measured), so the direct API is cheaper and simpler. |
| **Expected cost** | **Sonnet 5: ≈ $2–9/month** (mid case ≈ $4.73 with caching, $5.93 without). Opus 5 ≈ $5–22. Haiku 4.5 ≈ $1–4. Batch API halves the non-interactive jobs. Compare: Pro $20/mo, Max from $100/mo, nonprofit Team seat $8/user/mo — none of which may lawfully back a shared server app. |
| **Nonprofit discount?** | Claude for Nonprofits = up to 75% off **Team/Enterprise seats** ($8/user/mo Team). **No API/Console discount or credit program was found** on any Anthropic page; the pricing page only says "Academic and research discounts may be available" and new API users get "a small amount of free credits". |
| **Do not** | Put `CLAUDE_CODE_OAUTH_TOKEN` (or the laptop's `~/.claude/.credentials.json`) on the server; share the Max login; rely on a nonprofit Team seat's OAuth for automation (same "ordinary individual usage" language, credits "can't be shared or pooled"). |

## 1. Credential types Claude Code accepts (A)

From https://code.claude.com/docs/en/authentication (fetched 2026-09-07):

| Credential | How it is set | Billed to | Works for headless `claude -p` on a server with no browser? | Notes from the docs |
|---|---|---|---|---|
| Claude.ai subscription OAuth (`/login`) | Interactive browser flow; stored in `~/.claude/.credentials.json` (mode 0600) on Linux | Pro/Max/Team/Enterprise plan limits | Only if the file is copied/logged-in on that box; login expires and must be renewed with `/login` ("Once the stored login expires and can't be refreshed, each model request fails") | "This is the default for Claude Pro, Max, Team, and Enterprise users." |
| `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token` | One-year OAuth token printed to terminal | Subscription | Yes, except in `--bare` mode | "For CI pipelines, scripts, or other environments where interactive browser login isn't available … This token authenticates with your Claude subscription and requires a Pro, Max, Team, or Enterprise plan. It can only make model requests, so it can't establish Remote Control sessions or fetch claude.ai connectors." and "Bare mode does not read `CLAUDE_CODE_OAUTH_TOKEN`. If your script passes `--bare`, authenticate with `ANTHROPIC_API_KEY` or an `apiKeyHelper` instead." |
| `ANTHROPIC_API_KEY` (Console key) | Environment variable | Console org, per token | **Yes** — "In non-interactive mode (`-p`), the key is always used when present." | "Use this for direct Anthropic API access with a key from the Claude Console". Precedence #3, above `CLAUDE_CODE_OAUTH_TOKEN` (#5) and `/login` (#7). |
| `ANTHROPIC_AUTH_TOKEN` | Env var, sent as `Authorization: Bearer` | Whatever the gateway bills | Yes | "Use this when routing through an LLM gateway or proxy". |
| `apiKeyHelper` | Settings script returning a key | Console | Yes | "Use this for dynamic or rotating credentials, such as short-lived tokens fetched from a vault." |
| Console OAuth profile / Workload Identity Federation | `ant auth login` or WIF env vars | Console | Yes (not in `--bare`) | "Claude Code doesn't read profiles or federation variables in bare mode". |
| Bedrock / Vertex / Foundry | `CLAUDE_CODE_USE_BEDROCK` etc. | Cloud account | Yes | "No browser login is needed." |

Full precedence quoted from the page: "1. Cloud provider credentials … 2. `ANTHROPIC_AUTH_TOKEN` … 3. `ANTHROPIC_API_KEY` … 4. `apiKeyHelper` … 5. `CLAUDE_CODE_OAUTH_TOKEN` … 6. Anthropic profile and federation credentials … 7. Subscription OAuth credentials from `/login`."

Headless page, https://code.claude.com/docs/en/headless (fetched 2026-09-07): "`--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release." and "In bare mode, Claude Code never reads OAuth credentials or the system keychain. For the Anthropic API, set `ANTHROPIC_API_KEY` in the environment, with a key created in the Claude Console, or supply an `apiKeyHelper` in the `--settings` JSON." Without `--bare`, "`claude -p` loads the same context an interactive session would, including anything configured in the working directory or `~/.claude`" — which is why `generator.py` runs from `/tmp`. So: **`claude -p` with an API key on a server is a documented, supported configuration; the recommended form is `claude --bare -p … ` with `ANTHROPIC_API_KEY`.**

GitHub Actions page, https://code.claude.com/docs/en/github-actions (fetched 2026-09-07) — the only place the docs describe `CLAUDE_CODE_OAUTH_TOKEN` in automation, and its scope: "`CLAUDE_CODE_OAUTH_TOKEN`: an OAuth token that authenticates with your Claude subscription, available on Pro, Max, Team, and Enterprise plans. Generate one by running `claude setup-token` locally." … "If you authenticate with an OAuth token, runs use your Claude subscription instead of API billing." … "For a secret shared across repositories, authenticate with an API key from the Claude Console rather than an OAuth token, since an OAuth token is tied to the subscription of the person who ran `claude setup-token`." The docs never describe the token as a way to serve other users; the example is the subscriber's own repo workflow.

## 2. What the terms and Anthropic's own statements say (B)

### 2.1 Consumer Terms of Service — https://www.anthropic.com/legal/consumer-terms (fetched 2026-09-07; "Effective October 8, 2025")

- Scope: "These Terms of Service … govern your use of Claude.ai, Claude Pro, and other products and services that we may offer for individuals". Notice at top: "Our Commercial Terms of Service govern your use of any Anthropic API key, the Anthropic Console, or any other Anthropic offerings that reference the Commercial Terms of Service. For clarity, this does not include Claude.ai or Claude Pro use for individuals or entities."
- §2 Account: "You may not share your Account login information, Anthropic API key, or Account credentials with anyone else. You also may not make your Account available to anyone else. You are responsible for all activity occurring under your Account".
- §3 prohibited uses include: "Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it, to access the Services through automated or non-human means, whether through a bot, script, or otherwise." and "To develop any products or services that compete with our Services … or resell the Services."
- The live page contains **no** sentence mentioning "OAuth", "Claude Code", "Agent SDK" or "third-party harness" (verified by grepping the raw HTML). See 2.5 for where that language actually lives.

### 2.2 Usage Policy — https://www.anthropic.com/legal/aup (fetched 2026-09-07; "Effective September 15, 2025")

Relevant "Do Not Abuse our Platform" bullets: "Intentionally bypass capabilities, restrictions, or guardrails established within our products"; "Utilize automation in account creation or to engage in spammy behavior". Nothing specific to subscriptions, OAuth, credential sharing, or third-party harnesses ("Claude Code" appears only in the footer).

### 2.3 Claude Code "Legal and compliance" page — https://code.claude.com/docs/en/legal-and-compliance (fetched 2026-09-07) — **the primary policy statement**

- License: "Commercial Terms of Service - for Team, Enterprise, and Claude API users; Consumer Terms of Service - for Free, Pro, and Max users".
- "Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and the Agent SDK."
- Authentication and credential use, quoted in full:
  - "**OAuth authentication** is intended exclusively for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications."
  - "**Developers** building products or services that interact with Claude's capabilities, including those using the Agent SDK, should use API key authentication through Claude Console or a supported cloud provider. Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, or Max plan credentials on behalf of their users. Moreover, developers may not collect, store, or intermediate Claude.ai credentials or session tokens — sign-in to a Claude account must complete through Anthropic's own flow."
  - "This does not restrict how customers provision and manage their own API keys or third-party inference provider credentials — for example, configuring an API key in a development environment, secrets manager, or machine image for use by the customer's own authorized users — provided the resulting usage is billed to the key owner under their agreement with Anthropic".
  - "Anthropic reserves the right to take measures to enforce these restrictions and may do so without prior notice."
- Hosting Claude Code inside a product: "Customers may not pay for, resell, or intermediate Claude usage on their end users' behalf. Each end user must authenticate with their own Anthropic API key, Claude subscription plan credentials, or 3P inference provider credential".

### 2.4 Agent SDK docs — https://code.claude.com/docs/en/agent-sdk/overview and /quickstart (fetched 2026-09-07)

- Note on both pages: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Use the API key authentication methods described in the Quickstart instead."
- "Use of the Claude Agent SDK is governed by Anthropic's Commercial Terms of Service, including when you use it to power products and services that you make available to your own customers and end users".
- Quickstart setup step: "Get an API key from the Claude Console, then set it as an environment variable … `export ANTHROPIC_API_KEY=your-api-key`". Hosting page (https://code.claude.com/docs/en/agent-sdk/hosting): "**Anthropic API**: the subprocess reads `ANTHROPIC_API_KEY` from its environment. Supply it from your secret manager".

### 2.5 Help-center articles (support.claude.com)

| Article | Fetched | What it says |
|---|---|---|
| Log in to your Claude account — https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account | 2026-09-07 | "The preferred way to access Anthropic services using third-party software, tools, or services…is through API key authentication through Claude Console or a supported cloud provider." Anthropic "reserves discretion" to allow paid subscribers with usage credits enabled to use certain third-party tools, but "Use of third-party tools that misrepresent their identity to Anthropic's servers, attempt to route third-party traffic against subscription limits, or otherwise violate applicable terms or policies is prohibited." |
| Use the Claude Agent SDK with your Claude plan — https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan | 2026-09-08 (page dated June 16, 2026) | Announced (then paused) a separate monthly "Agent SDK credit" for subscribers covering "Claude Agent SDK usage in your own projects", "The `claude -p` command in Claude Code (non-interactive mode)", "The Claude Code GitHub Actions integration", "Third-party apps that authenticate with your Claude subscription through the Agent SDK". Banner: "Update June 15: We're pausing the changes … For now, nothing has changed: Claude Agent SDK, claude -p, and third-party app usage still draw from your subscription's usage limits." Key lines: "Per-user, not pooled. Credits belong to individual accounts. They can't be shared or pooled across teammates." and "**Production automation at scale.** The Agent SDK monthly credit is sized for individual experimentation and automation. Teams running shared production automation should use Claude Platform with an API key for predictable pay-as-you-go billing." and "API key users … Pay-as-you-go billing continues". |
| Use Claude Code with your Pro or Max plan — https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan | 2026-09-07 | "Both Pro and Max plans offer usage limits that are shared across Claude and Claude Code". Silent on multi-user or server use. |
| Why pay separately for API/Console — https://support.claude.com/en/articles/9876003-… | 2026-09-08 | "A paid Claude subscription enhances your chat experience but doesn't include access to the Claude API or Console." Console is "the developer platform … for building applications and integrations." |
| Manage usage credits for paid plans — https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans | 2026-09-08 | "Usage credits allow individuals subscribed to paid Claude plans (Pro, Max 5x, and Max 20x) to continue using Claude … after reaching their included usage limits." "Usage credits are billed at standard API rates". Applies to "Claude conversations and Claude Code terminal usage". |
| How do I pay for my Claude API usage — https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage | 2026-09-08 | "Prepaid usage credits" (or monthly invoicing via sales); "Credits expire one year from the purchase date"; "All credit purchases are non-refundable"; auto-reload available; "you're charged only for successful API calls". |

### 2.6 The Feb-2026 "third-party harness" enforcement — primary vs secondary

- The Register, 2026-02-20, https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/ (fetched 2026-09-07; **secondary**) quotes the then-current Claude Code legal page: "Using OAuth tokens obtained through Claude Free, Pro, or Max accounts in any other product, tool, or service — including the Agent SDK — is not permitted and constitutes a violation of the Consumer Terms of Service", and an Anthropic engineer's January X post: "Third-party harnesses using Claude subscriptions create problems for users and are prohibited by our Terms of Service". It attributes the sentence to "Consumer Terms of Service (Section 3.7)"; the live Consumer Terms contain no such sentence (see 2.1), and archive.org was unreachable from this environment, so **the February wording is unverified against a primary copy**. The *current* legal-and-compliance page (2.3) carries the same rule in softer words, and the June-2026 help article (2.5) shows Anthropic now expressly contemplating subscriber-owned `claude -p` / Agent SDK use while steering "shared production automation" to API keys.

### 2.7 Applying the terms to our scenarios

| Scenario | Permitted? | Why |
|---|---|---|
| Maintainer runs `claude -p` on his own laptop for content he is generating | Yes (tolerated) | "ordinary, individual usage of Claude Code and the Agent SDK"; help article: `claude -p` "still draw[s] from your subscription's usage limits". |
| Copy the laptop's OAuth login / `setup-token` to a server that only the maintainer triggers | Grey — not recommended | Same person, but a long-lived credential on a shared box; docs frame `setup-token` for the subscriber's own CI. Any other staff trigger converts it to the next row. |
| Server app used by other staff, backed by the maintainer's Max OAuth or `CLAUDE_CODE_OAUTH_TOKEN` | **No** | Consumer Terms §2 (Account "available to anyone else"), §3 (automated access outside an API key); legal page: no routing "through Free, Pro, or Max plan credentials on behalf of their users"; help article: "shared production automation should use Claude Platform with an API key". Enforcement "without prior notice". |
| Nonprofit Team seat ($8/user) + `setup-token` for org automation | Grey — not recommended | Team is under Commercial Terms, but OAuth is still for "ordinary use of Claude Code and other native Anthropic applications", limits "assume ordinary, individual usage", and per-user allowances "can't be shared or pooled across teammates". |
| Console org + API key in the server's secrets, used by the nonprofit's own staff | **Yes** | Explicitly allowed: "configuring an API key in a development environment, secrets manager, or machine image for use by the customer's own authorized users — provided the resulting usage is billed to the key owner". Commercial Terms: "permission to use the Services, including to power products and services Customer makes available to its own customers and end users". |

## 3. The sanctioned path and what it costs (C)

### 3.1 Console org mechanics (https://platform.claude.com/docs/en/api/rate-limits, fetched 2026-09-08)

- Prepaid credits, non-refundable, expire after one year; auto-reload optional (2.5). "New users receive a small amount of free credits to test the API" (pricing page FAQ; amount unstated).
- Tiers are automatic. Start tier: monthly spend cap $500; per-model limits 1,000 RPM / 2,000,000 input tokens per minute / 400,000 output tokens per minute for Sonnet 5, Opus 5 and Haiku 4.5 — orders of magnitude above this app's load. "New organizations … may start in the Evaluation tier, with limits below the standard limits". Cache reads do not count toward ITPM. You can set a lower spend limit yourself on the Billing page.
- Commercial Terms (https://www.anthropic.com/legal/commercial-terms, fetched 2026-09-07, "Effective June 17, 2025"): govern "Anthropic API keys and any other Anthropic offerings that references these Terms"; no entity-type restriction (a nonprofit may hold a Console org).

### 3.2 Model pricing — https://platform.claude.com/docs/en/about-claude/pricing (fetched 2026-09-07; `docs.anthropic.com/en/docs/about-claude/pricing` 301-redirects here)

| Model (API id) | Base input | 5-min cache write (1.25×) | 1-hour cache write (2×) | Cache read (0.1×) | Output | Batch input / output (−50%) |
|---|---|---|---|---|---|---|
| Claude Sonnet 5 (`claude-sonnet-5`) | $2 / MTok | $2.50 | $4 | $0.20 | $10 / MTok | $1 / $5 |
| Claude Opus 5 (`claude-opus-5`) | $5 / MTok | $6.25 | $10 | $0.50 | $25 / MTok | $2.50 / $12.50 |
| Claude Haiku 4.5 (`claude-haiku-4-5`) | $1 / MTok | $1.25 | $2 | $0.10 | $5 / MTok | $0.50 / $2.50 |

- Sonnet 5 note on the page: "The $2/$10 per million input/output token pricing for Claude Sonnet 5, announced at launch as introductory pricing through August 31, 2026, is now the standard price. The previously scheduled increase to $3/$15 … on September 1, 2026 will not occur."
- Caching multipliers: "5-minute cache write 1.25x base input price … 1-hour cache write 2x … Cache read (hit) 0.1x". "These multipliers stack with other pricing modifiers, including the Batch API discount". Minimum cacheable prefix (https://platform.claude.com/docs/en/build-with-claude/prompt-caching, fetched 2026-09-07): "512 tokens for … Claude Opus 5"; "1,024 tokens for … Claude Sonnet 5"; "**4,096 tokens for Claude Haiku 4.5**"; "Shorter prompts cannot be cached, even if marked with `cache_control` … no error is returned." **Our ~4,000-token prefix is below Haiku's floor** — pad it past 4,096 or accept no caching on Haiku.
- Batch API (https://platform.claude.com/docs/en/build-with-claude/batch-processing, fetched 2026-09-07): "All usage is charged at 50% of the standard API prices"; "most batches finishing in less than 1 hour"; "Batches expire if processing does not complete within 24 hours"; "The pricing discounts from prompt caching and Message Batches can stack" but "cache hits are provided on a best-effort basis". Suitable for the ~30 small background jobs, not for a staff member waiting on a caption.
- Tokenizer note: "Claude 4.7 and later models … use a newer tokenizer … approximately 30% more tokens for the same text" vs Sonnet 4.6 and earlier — Sonnet 5 / Opus 5 counts will run above what the app saw on older models; Haiku 4.5 uses the older tokenizer.
- Consumer plan prices for comparison (https://claude.com/pricing, fetched 2026-09-08): Pro "$20 if billed monthly", Max "From $100 / Per month", Team Standard "$25 if billed monthly", Premium "$125"; paid members can "turn on usage credits to keep working at standard API rates".

### 3.3 Three supported ways to run it on the server

| Option | Terms | Auth | Overhead | Fit |
|---|---|---|---|---|
| **Direct Messages API** via `anthropic` Python SDK (`client.messages.create(...)`) | Commercial | `ANTHROPIC_API_KEY` | None beyond your prompt; explicit `cache_control` on the prefix | **Recommended.** Captions are single-call generation with no tools; the CLI's agent loop, file tools and permission system add nothing. |
| **Claude Agent SDK** (`pip install claude-agent-sdk`, `query()`) | Commercial (overview page) | `ANTHROPIC_API_KEY` (quickstart, hosting page) | Spawns a `claude` subprocess per call; same harness overhead as `-p`; hosting page: 1 GiB RAM per agent starting point | Only if the app needs Claude to read files/run commands. |
| **Keep `claude -p`** with `ANTHROPIC_API_KEY` (+ `--bare`) | Commercial | `ANTHROPIC_API_KEY` | Harness overhead (below) | Supported ("In non-interactive mode (`-p`), the key is always used when present"); minimal code change (set env var, add `--bare`), but pays for the harness every call. |

**Measured `claude -p` harness overhead** (local, 2026-09-08 UTC, Claude Code 2.1.263, run from the scratchpad dir with the maintainer's `~/.claude` plugins loaded, Max OAuth): `claude -p "Reply with exactly the word OK and nothing else." --model sonnet --output-format json --max-turns 1` returned `usage.input_tokens: 2`, `cache_creation_input_tokens: 18578` (all `ephemeral_1h`), `output_tokens: 4`, `total_cost_usd: 0.074356`, `canonicalModel: claude-sonnet-5`. I.e. the CLI prepends ~18.6k tokens of system prompt / tool definitions / skill index before the app's prompt. On an API key the CLI's cache TTL "is five minutes by default" (costs page), so at Sonnet 5 rates that overhead is $0.046 per cache-write call and $0.0037 per cache-read call. A clean server home dir (no user plugins) and `--bare` would shrink it, but not to zero.

### 3.4 Nonprofit programs (fetched 2026-09-08)

- https://www.anthropic.com/news/claude-for-nonprofits (Dec 2, 2025): "Nonprofits are now eligible for a discount of up to 75% on Team and Enterprise plans." Includes connectors (Blackbaud, Candid, Benevity) and a free course. **No API / Console discount or credits mentioned.**
- https://claude.com/solutions/nonprofits: Team "$8 /user Per month"; Enterprise custom; eligibility "registered 501(c)(3) organizations and their international equivalents", K-12 schools, certain healthcare providers; Team verification "through Goodstack" (~2–3 minutes); Enterprise verified by sales. No API pricing on the page. https://academy.claude.com/tutorials/getting-started-with-claude-for-nonprofits adds "2 seats for teams under 150" minimum; API/Console "not addressed".
- https://www.anthropic.com/nonprofits → HTTP 404.
- Pricing page: "Academic and research discounts may be available"; "Volume discounts … negotiated on a case-by-case basis" — nothing nonprofit-specific for the API. **Mark as absent**; worth one email to sales@anthropic.com but do not plan on it.

## 4. Cost model (D)

Assumptions (from the brief plus two stated guesses): 5 posts/week → 5 × 52 / 12 = **21.67 posts/month**; 2–4 platforms per post; two-stage pipeline ≈ **3 calls per post per platform**; caption calls 6,000–12,000 input / 800–1,500 output tokens, of which a **stable 4,000-token prefix** is cacheable; **30 small jobs/month at an assumed 2,000 input / 200 output** (alt text, suggestions, classification). "Cached" assumes all calls for one post run inside the 5-minute cache window, so **1 cache write per post, all other calls read** (writes = 21.67; reads = calls − 21.67). Prices from §3.2. Script: `costmodel.py` in the session scratchpad; arithmetic reproduced below.

Worked example — Sonnet 5, mid case (3 platforms, 9k in / 1,150 out), cached:

```
calls          = 21.67 posts × 3 platforms × 3 calls        = 195
uncached input = 195 × (9,000 − 4,000) × $2 / 1M            = $1.95
cache writes   = 21.67 × 4,000 × $2.50 / 1M                 = $0.22
cache reads    = (195 − 21.67) × 4,000 × $0.20 / 1M         = $0.14
output         = 195 × 1,150 × $10 / 1M                     = $2.24
small jobs     = 30 × (2,000 × $2 + 200 × $10) / 1M         = $0.18
total                                                        = $4.73 / month
```

Uncached variant: 195 × 9,000 × $2/1M = $3.51 input + $2.24 output + $0.18 = **$5.93**.

### Claude Sonnet 5 ($2 in / $10 out)

| Scenario | Calls/mo | Caption input | Caption output | Small jobs | **Total/mo** | If everything went through Batch API |
|---|---|---|---|---|---|---|
| Low (2 platforms, 6k/800) — no cache | 130 | $1.56 | $1.04 | $0.18 | **$2.78** | $1.39 |
| Low — cached | 130 | $0.82 | $1.04 | $0.18 | **$2.04** | $1.02 |
| Mid (3 platforms, 9k/1,150) — no cache | 195 | $3.51 | $2.24 | $0.18 | **$5.93** | $2.97 |
| Mid — cached | 195 | $2.31 | $2.24 | $0.18 | **$4.73** | $2.36 |
| High (4 platforms, 12k/1,500) — no cache | 260 | $6.24 | $3.90 | $0.18 | **$10.32** | $5.16 |
| High — cached | 260 | $4.57 | $3.90 | $0.18 | **$8.65** | $4.32 |

### Claude Opus 5 ($5 in / $25 out)

| Scenario | Calls/mo | Caption input | Caption output | Small jobs | **Total/mo** | Batch |
|---|---|---|---|---|---|---|
| Low — no cache | 130 | $3.90 | $2.60 | $0.45 | **$6.95** | $3.48 |
| Low — cached | 130 | $2.06 | $2.60 | $0.45 | **$5.11** | $2.55 |
| Mid — no cache | 195 | $8.78 | $5.61 | $0.45 | **$14.83** | $7.42 |
| Mid — cached | 195 | $5.76 | $5.61 | $0.45 | **$11.82** | $5.91 |
| High — no cache | 260 | $15.60 | $9.75 | $0.45 | **$25.80** | $12.90 |
| High — cached | 260 | $11.42 | $9.75 | $0.45 | **$21.62** | $10.81 |

### Claude Haiku 4.5 ($1 in / $5 out) — caching only engages if the prefix is ≥ 4,096 tokens

| Scenario | Calls/mo | Caption input | Caption output | Small jobs | **Total/mo** | Batch |
|---|---|---|---|---|---|---|
| Low — no cache | 130 | $0.78 | $0.52 | $0.09 | **$1.39** | $0.70 |
| Low — cached | 130 | $0.41 | $0.52 | $0.09 | **$1.02** | $0.51 |
| Mid — no cache | 195 | $1.75 | $1.12 | $0.09 | **$2.97** | $1.48 |
| Mid — cached | 195 | $1.15 | $1.12 | $0.09 | **$2.36** | $1.18 |
| High — no cache | 260 | $3.12 | $1.95 | $0.09 | **$5.16** | $2.58 |
| High — cached | 260 | $2.28 | $1.95 | $0.09 | **$4.32** | $2.16 |

Add-on if the app keeps shelling out to `claude -p` on an API key (18,578 measured overhead tokens/call, Sonnet 5, 5-min TTL): mid case 21.67 writes × 18,578 × $2.50/1M = $1.01 + 173.3 reads × 18,578 × $0.20/1M = $0.64 → **≈ +$1.65/month** (≈ +$1.89 in the high case); worst case with every call more than 5 minutes apart (all writes): 195 × $0.0464 = **+$9.06** (high: +$12.08). Extra agent turns (tool calls) would add more. Direct API avoids all of it.

Sensitivity: output tokens are the largest line on every model once caching is on, so `max_tokens` discipline and shorter stage-1 drafts matter more than shaving input. Doubling volume doubles cost linearly; even 4× volume on Sonnet 5 stays under $40/month.

## 5. Verdict — recommended, terms-compliant configuration

1. **Create a Claude Console (platform.claude.com) organization owned by the temple/nonprofit** (not the maintainer's personal account), buy a small prepaid credit (credits last one year; enable auto-reload at a low threshold), set an org spend limit (e.g. $25/month) on the Billing page, and create one API key for the server. This is the path Anthropic's own documents name for "developers building products or services", for "shared production automation", and for keys "for use by the customer's own authorized users".
2. **Replace the `subprocess.run(["claude", "-p", …])` calls with the `anthropic` Python SDK** (`client.messages.create`, model `claude-sonnet-5` for generate/iterate/suggest/calendar and `claude-haiku-4-5` for classify — the same aliases `model_config.py` uses today, resolved per https://code.claude.com/docs/en/model-config: "Anthropic API: opus → Opus 5, sonnet → Sonnet 5"). Put the brand/knowledge prefix in `system` with `cache_control: {"type": "ephemeral"}`; keep it byte-stable (no timestamps) so it hits. Read `usage.cache_read_input_tokens` in logs to confirm. Use the Batch API for the ~30 non-interactive jobs if convenient (50% off), otherwise ignore it.
3. **Keep the maintainer's Max subscription for his own interactive Claude Code work** on the laptop; do not copy its credentials, `setup-token`, or `~/.claude/.credentials.json` to the server. If the team also wants chat seats, Claude for Nonprofits Team seats ($8/user/month via Goodstack) are the sanctioned way to give staff Claude — but they do not replace the API key for the app.
4. **Expected bill: ≈ $3–9/month on Sonnet 5 (mid ≈ $4.73 with caching)**, ≈ $5–22 on Opus 5, ≈ $1–4 on Haiku 4.5, plus the Console's first-year free credits. The API cost is a rounding error next to the $24/month VPS already planned in `postiz-hosting-migration.md`.
5. Interim (before the code change): `export ANTHROPIC_API_KEY=…` in the `gvsa-backend` unit and add `--bare` to the `claude -p` invocations. Supported by the docs; costs ≈ $1.65–9/month more than the direct API for the same work.

## Open items / uncertainty

- The February 2026 wording ("Using OAuth tokens obtained through Claude Free, Pro, or Max accounts in any other product, tool, or service — including the Agent SDK — is not permitted…") is quoted from The Register; archive.org was unreachable from this environment, so it is unverified against a primary copy. The live legal-and-compliance page (fetched 2026-09-07) states the same rule in different words; The Register's "Consumer Terms Section 3.7" attribution does not match the live Consumer Terms.
- Anthropic paused the "Agent SDK monthly credit" on June 15, 2026 and says "We're working to update the plan to better support how users build with Claude subscriptions." Subscriber-side rules for `claude -p` may change again; the API-key path is stable under the Commercial Terms.
- Whether a nonprofit **Team** seat's OAuth may back org-owned automation is not addressed anywhere explicitly; every relevant sentence points to individual use, so it is treated as not sanctioned here.
- Small-job token sizes (2,000 in / 200 out) and "3 calls per post per platform" are assumptions; if the pipeline is 3 calls per post regardless of platform count, divide the caption rows by the platform count.
- The 18,578-token harness overhead was measured on the maintainer's laptop with user-level plugins/skills loaded; a clean server (and `--bare`) will be lower. Re-measure after deployment with `--output-format json`.
- Free-credit amount for new Console orgs is "a small amount" (unstated); whether Anthropic grants nonprofit API credits on request is unknown — one email to sales@anthropic.com would settle it.
- Sonnet 5 / Opus 5 use a tokenizer that yields "approximately 30% more tokens" than Sonnet 4.6-era models; the 6k–12k figures should be re-baselined with `client.messages.count_tokens` on the real prompts.

## Sources

| Source | URL | Fetched | Type |
|---|---|---|---|
| Claude Code — Authentication | https://code.claude.com/docs/en/authentication | 2026-09-07 | Primary |
| Claude Code — Run programmatically / headless | https://code.claude.com/docs/en/headless | 2026-09-07 | Primary |
| Claude Code — GitHub Actions | https://code.claude.com/docs/en/github-actions | 2026-09-07 | Primary |
| Claude Code — Legal and compliance | https://code.claude.com/docs/en/legal-and-compliance | 2026-09-07 | Primary |
| Claude Code — Manage costs | https://code.claude.com/docs/en/costs | 2026-09-08 | Primary |
| Claude Code — Model configuration | https://code.claude.com/docs/en/model-config | 2026-09-08 | Primary |
| Agent SDK — Overview | https://code.claude.com/docs/en/agent-sdk/overview | 2026-09-07 | Primary |
| Agent SDK — Quickstart | https://code.claude.com/docs/en/agent-sdk/quickstart | 2026-09-07 | Primary |
| Agent SDK — Hosting | https://code.claude.com/docs/en/agent-sdk/hosting | 2026-09-08 | Primary |
| Consumer Terms of Service (eff. 2025-10-08) | https://www.anthropic.com/legal/consumer-terms | 2026-09-07 (raw HTML grepped) | Primary |
| Commercial Terms of Service (eff. 2025-06-17) | https://www.anthropic.com/legal/commercial-terms | 2026-09-07 | Primary |
| Usage Policy (eff. 2025-09-15) | https://www.anthropic.com/legal/aup | 2026-09-07 | Primary |
| Help — Log in to your Claude account | https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account | 2026-09-07 | Primary |
| Help — Use the Claude Agent SDK with your Claude plan (2026-06-16) | https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan | 2026-09-08 (raw HTML) | Primary |
| Help — Use Claude Code with your Pro or Max plan | https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan | 2026-09-07 | Primary |
| Help — Why pay separately for API and Console | https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-do-i-have-to-pay-separately-to-use-the-claude-api-and-console | 2026-09-08 | Primary |
| Help — Manage usage credits for paid plans | https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans | 2026-09-08 | Primary |
| Help — How do I pay for my Claude API usage | https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage | 2026-09-08 | Primary |
| Platform — Pricing | https://platform.claude.com/docs/en/about-claude/pricing (redirect from docs.anthropic.com) | 2026-09-07 | Primary |
| Platform — Prompt caching | https://platform.claude.com/docs/en/build-with-claude/prompt-caching | 2026-09-07 | Primary |
| Platform — Batch processing | https://platform.claude.com/docs/en/build-with-claude/batch-processing | 2026-09-07 | Primary |
| Platform — Rate limits | https://platform.claude.com/docs/en/api/rate-limits | 2026-09-08 | Primary |
| claude.com/pricing | https://claude.com/pricing | 2026-09-08 | Primary |
| Introducing Claude for Nonprofits (2025-12-02) | https://www.anthropic.com/news/claude-for-nonprofits | 2026-09-08 | Primary |
| Claude for Nonprofits solution page | https://claude.com/solutions/nonprofits | 2026-09-08 | Primary |
| Getting started with Claude for Nonprofits | https://academy.claude.com/tutorials/getting-started-with-claude-for-nonprofits | 2026-09-08 | Primary |
| anthropic.com/nonprofits | https://www.anthropic.com/nonprofits | 2026-09-07 — **404** | — |
| The Register — "Anthropic clarifies ban on third-party tool access to Claude" (2026-02-20) | https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/ | 2026-09-07 | **Secondary** (Feb-2026 wording; archive.org unreachable) |
| Local measurement | `claude -p … --output-format json`, Claude Code 2.1.263 | 2026-09-08 | Local |
