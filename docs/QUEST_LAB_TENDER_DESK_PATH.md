# Quest Lab: Tender Desk learning path

## Product boundary

This is a new learning campaign inside Diddy Dungeon / Quest Lab. It uses the existing Bounty Office, Hunt combat, Forge, Monaco editor, PYR grading, Codex notes, XP, coins, and campaign boss.

The first campaign is `Tender Desk: The First Build`. The learner creates a fictional service-request application from an empty folder. It progresses from a browser page to an authenticated, database-backed app and a deployment runbook. The examples are original and use a made-up service desk; the lessons borrow learning structure and authoritative references from MDN, React, Node.js, PostgreSQL, Supabase and Vercel rather than copying another course.

## How a lesson becomes a fight

- A chapter is an existing campaign act, shown as a chapter board.
- Each bounty is an existing campaign mob. Its contract explains the problem and its resources point to the most relevant official reading.
- Objectives use the current battle types: set up a file, build code, diagnose a bug, predict behavior, or explain a decision. One objective is one combat submission; the established Resolve, HP, PYR, equipment, XP and reward rules still own the outcome.
- The six chapters contain 20 contracts and 94 authored objectives. This is a substantial first course, not a promise of expertise after a fixed number of short lessons. The objective count also does not imply a fixed number of hours; learners should repeat tasks, change requirements, test failures, and revisit weak Codex concepts.
- Chapter-end elites ask for more complete work. The existing campaign boss has a six-phase audit: required behavior, reading the learner's code, edge cases, a multi-office twist, a second system change, and a code interview.
- The learner remains the author. PYR can grade, hint and question; it must not generate a finished campaign solution. The normal Quest Lab editor and current AI provider remain in use.

## Campaign I: Tender Desk: The First Build

| Chapter | Main learning | Project milestone |
| --- | --- | --- |
| I. A Desk on the Web | Project files, browser mental model, semantic HTML, forms, accessible labels, CSS cascade/box model/responsive layout, first browser script and events | A small page that responds to a form submission |
| II. JavaScript with Intent | Values and conversion, missing values, function contracts, scope, arrays/objects/references, map/filter/reduce, control flow, input boundaries, tests | Small pure request rules and a request collection with edge cases |
| III. The Working App | Form lifecycle and accessible feedback, async/await, fetch/JSON/statuses, loading/error states, React components, props, state, stable keys, ES modules and a Vite toolchain | A maintainable React interface with an API client boundary |
| IV. The Backend Contract | Client/server boundaries, HTTP methods and status codes, Node's built-in server, JSON validation, trust boundaries, REST, idempotency and CORS | A documented local API that the interface can call |
| V. The PostgreSQL Ledger | Relational modeling, keys, normalization, SELECT/filter/order, joins, aggregation, constraints, transactions, indexes and migration discipline | A relational request/office schema and versioned migration |
| VI. Secure Release | Supabase CLI/local development, migrations and seed data, Auth versus authorization, RLS policies, Edge Functions/secrets, Vercel preview/production, logs and recovery | A secured, deployable request desk with a release and operations runbook |

The local Supabase stack is taught as an explicit, optional environment setup. Its current official workflow requires the CLI and a compatible container runtime for the default local stack; the campaign must tell the learner to check resources before starting containers. It should not start Docker, Supabase, a remote database or a deployment on the learner's behalf.

## Deliberate teaching pattern

Every concept should recur in more than one form:

1. Read a focused explanation or official guide section.
2. Predict what a small snippet or user action will do.
3. Build or change a real project file.
4. Diagnose a plausible failure, including a boundary case.
5. Explain the reasoning in plain language.
6. Transfer the same principle to a different requirement in the boss twist.

The campaign must revisit old skills. For example, the HTML form introduced in Chapter I becomes a React form in Chapter III, a server validation boundary in Chapter IV, a constrained relational record in Chapter V, and an RLS-protected user-owned record in Chapter VI. That repetition is intentional: it makes the data path visible across layers instead of presenting unrelated syntax drills.

## After this campaign: backend depth

The first campaign introduces practical backend foundations; it does not cover all production backend work. It uses JavaScript before React/Vite and Node, then PostgreSQL SQL, HTML and CSS throughout. TypeScript is deliberately deferred until the learner has a working model of JavaScript and the browser/server boundary. A follow-up campaign should deepen:

- TypeScript and runtime validation, API versioning, authentication/session design, authorization and secure file handling.
- Database query plans, indexing, concurrency, isolation, locks, idempotency and safe schema evolution at scale.
- Caching, background jobs/queues, retries, rate limits, observability, structured logs and incident response.
- Integration/contract tests, CI, code review, threat modeling, backups, restore drills, privacy and operational cost.

## Later campaign: AI engineering

AI engineering should be a separate Quest Lab campaign sequence after the Python, JavaScript, SQL and backend foundations. It must not be squeezed into the first Tender Desk boss. The proposed path is:

1. **Data and Python bridge:** Python collections/functions, notebooks/scripts, CSV/JSON, cleaning, reproducible environments and SQL-backed data access. Reuse the existing Diddy Dungeon Python campaign as prerequisite practice rather than duplicating its beginner lessons.
2. **Math and evaluation:** vectors/matrices at an applied level, probability, distributions, sampling, train/validation/test splits, leakage, baselines and choosing metrics for a product task.
3. **Machine learning:** supervised and unsupervised tasks, feature engineering, model fitting, overfitting, regularization, cross-validation and error analysis.
4. **Neural networks and transformers:** tensors, gradients at a conceptual and practical level, tokenization, attention, context windows, model limits and when an LLM is the wrong tool.
5. **LLM application engineering:** provider APIs, structured outputs, tool calls, prompt/version management, embeddings, retrieval-augmented generation and citations.
6. **Trust and production:** prompt injection, permissions, privacy, evaluation sets, regression tests, human review, latency/cost budgets, monitoring and failure handling.
7. **Capstone:** ship a narrow AI feature behind an existing backend with a measured quality target, a non-AI fallback, access controls, evaluation report and deployment/rollback plan.

Each would become a separate campaign project with its own chapter files and boss contract. The learning loop would remain the Diddy Dungeon Hunt/Forge flow.

## Source map

These official resources inform topic order and further reading. The in-game bounty links are intentionally narrower and tell the learner what question to bring to each resource.

- [MDN Curriculum](https://developer.mozilla.org/en-US/curriculum/) and [MDN Learn Web Development](https://developer.mozilla.org/en-US/docs/Learn_web_development) provide beginner learning outcomes, core modules, skill checks and further resources for web fundamentals.
- [React Learn](https://react.dev/learn) supplies the official component, interactivity and state concepts used after JavaScript foundations.
- [Node.js Learn](https://nodejs.org/en/learn/getting-started/introduction-to-nodejs) and the [Node.js HTTP API](https://nodejs.org/api/http.html) support the visible client/server chapter without hiding the protocol behind a framework first.
- The [PostgreSQL tutorial](https://www.postgresql.org/docs/current/tutorial.html) introduces relational concepts and SQL; later chapters use the wider official references for constraints, transactions, indexes and query structure.
- [Supabase local development](https://supabase.com/docs/guides/local-development), [CLI workflows](https://supabase.com/docs/guides/local-development/cli-workflows), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security) and [Edge Functions](https://supabase.com/docs/guides/functions) inform the local, security and backend lessons. Policies must express the actual row-ownership or office-membership rule; `authenticated` alone is not authorization.
- [Vercel getting started](https://vercel.com/docs/getting-started-with-vercel) and [deployment docs](https://vercel.com/docs/deployments) inform preview/production promotion and release operations.

## Current implementation boundary

The source campaign is split under `ide/server/campaigns/06-tender-desk/manifest.json` and `chapters/`, while the existing campaign loader assembles the files for the game. The project uses safe, bounded relative paths and explicitly supports web/database languages in the Forge submission and PYR grading boundary. A sandboxed HTML preview supports local linked CSS and classic JavaScript; module/bundler preview belongs to the later React/Vite toolchain.
