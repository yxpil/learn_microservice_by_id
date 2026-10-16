# Analysis: Why Cloud Drives Use This Architecture

> Companion notes for the `learn_microservice_by_id` demo. Explains why cloud-drive
> (网盘) products adopt one-DB-per-service + ID-chained microservices, what "glue" buys
> you, and what its costs are and how to avoid them.

---

## 1. Why cloud drives use this framework

A cloud drive is not one system — it is a bundle of capabilities with completely
different rhythms:

| Domain | Characteristics |
|---|---|
| Account / login | Strong consistency, low frequency, security-sensitive |
| File metadata (who owns what, where, size) | Extremely high read concurrency, write amplification |
| Block storage (raw bytes) | Massive small IO, lots of cold data |
| Folder / directory tree | Nested queries, move/rename transactions |
| Share / links | High frequency, leak risk, revocable |
| Search | Inverted index, CPU/memory heavy |
| Preview / transcoding | Video transcode is CPU-heavy batch work |
| Recycle bin / versions | Delayed delete, GC jobs |
| Quota / billing | Strong consistency, reconciliation |

They have different concurrency models, data volumes, tech stacks, and release cadences.
Squeezing them into one DB / one service means file listing can drag down login, and
changing share logic requires regressing the whole system.

**One service one DB buys:**
- Independent scaling — scale metadata when listing is hot, leave login alone.
- Independent tech selection — metadata on KV/document DB, search on ES, blocks on object storage.
- Failure isolation — share service down, download still works.
- Clean data boundary — physically prevents "join files table inside users table".

**Why chain by ID instead of sharing tables / foreign keys:**
- Shared DB = two teams racing on one table, coupled releases = no real decoupling.
- Foreign keys don't exist cross-service (no DB-level constraint across services).
- An ID is the cheapest contract: order stores `user_id`; when it needs user info it
  calls the user service over HTTP, or subscribes to events and keeps a read-only copy.
  Adding a feature never requires changing the old DB schema.

---

## 2. What "glue" buys you

"Glue" = don't build one big system. Build many tiny, single-responsibility components
that don't know each other, then an orchestration layer (gateway / API composition /
event bus) sticks them into complex behaviors.

1. **Components are trivial.** Each service knows one thing. File service just serves
   bytes by `file_id`; it doesn't know about watermarks, virus scanning, or AI summaries.
   Complexity lives in the glue, not in the parts.
2. **Business changes concentrate in the glue.** "Before download, run virus scan" —
   the download flow changes from `get block -> output` to `get block -> scan -> output`.
   Parts untouched. Business flows become a pipeline in one place, not scattered if-else.
3. **Replaceable / pluggable.** Swap object storage A for B? As long as "get bytes by
   file_id" holds, the glue doesn't care. Strangler-fig migration: new component takes
   1% traffic, then 100%, old one retires.
4. **Combinatorial reuse.** The same "get file" component is reused by download, preview,
   search indexing, AV scan, AI summary, share link. New component instantly usable by
   all flows; new flow instantly reuses all components.
5. **Parallel work.** Teams own components, agree on interfaces, ship independently.
6. **Fault tolerance in one place.** Glue retries / degrades / caches; components stay
   "idiot" and don't each reinvent timeouts and circuit breakers.
7. **Evolution without rewrite.** Decade-old systems can swap tech stacks incrementally
   because glue routes traffic between old and new parts.

---

## 3. Downsides and how to avoid them

| Downside | How to avoid |
|---|---|
| Distributed complexity (no cross-service local txn; lost events; duplicate retries) | Idempotency keys on every op; at-least-once events with idempotent consumers; eventual consistency + compensation, only saga/state-machine for the truly atomic bits (see `learn_distributed_txn`) |
| Glue layer grows into a new distributed monolith | Make flows explicit (state machine / workflow engine); glue only decides "who to call, order, on-failure"; merge a service when a flow outgrows N steps |
| Debugging a black box (one request across 6 services) | Mandatory trace-id propagated through every HTTP call; central logs + metrics + alerts; every service exposes /health and /metrics |
| Redundant copies drift out of sync | Treat copies as read-only caches, source of truth stays original service; event-driven sync + offline reconciliation; prefer one RPC over a stale copy |
| RPC latency kills P99 (online joins) | Parallel calls, batch endpoints, pre-aggregated read models for hot pages, local caching |
| N× ops cost (deploy/monitor/cert per service) | Containerize with one template; merge tiny services; platform CI/CD shared by all |
| Interface changes break all consumers | Backward-compatible additions, versioned breaks (/v2/), contract tests, published schemas |
| Glue layer itself is a single point | Stateless + replicated; edge/client degradation for critical flows |
| Premature decomposition (the worst) | Start monolith; split only when you feel real pain (two teams blocking each other, a component needing independent scale). Split high-churn / different-load parts first |

**Bottom line:** glue is not silver bullet. Its price is distributed complexity + ops +
observability. The three rules to survive: **idempotency everywhere, trace-id end to end,
don't split until it hurts.**
