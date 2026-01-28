# Operational Playbooks

Index of operational playbooks for the Holiday Peak Hub accelerator.

| Playbook | Area | Trigger |
|---|---|---|
| [Agent latency spikes](playbook-agent-latency-spikes.md) | Agents | P95 latency breach or timeouts |
| [Tool call failures](playbook-tool-call-failures.md) | Agents/Tools | Tool error rate > threshold |
| [Model degradation](playbook-model-degradation.md) | Agents/Models | Quality regression or increased hallucinations |
| [Adapter failure](playbook-adapter-failure.md) | Adapters | Upstream API errors/outage |
| [Adapter latency spikes](playbook-adapter-latency-spikes.md) | Adapters | P95 adapter latency breach |
| [Adapter schema changes](playbook-adapter-schema-changes.md) | Adapters | Contract mismatch or parsing errors |
| [Redis OOM](playbook-redis-oom.md) | Memory/Hot | Evictions or OOM errors |
| [Cosmos high RU consumption](playbook-cosmos-high-ru.md) | Memory/Warm | 429s or RU saturation |
| [Blob throttling](playbook-blob-throttling.md) | Memory/Cold | 503s or slow downloads/uploads |
| [Connection pool exhaustion](playbook-connection-pool-exhaustion.md) | Memory | Connection timeouts/too many connections |
| [TTL not expiring](playbook-ttl-not-expiring.md) | Memory | Stale data or unbounded growth |
