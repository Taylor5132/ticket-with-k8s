---
status: superseded by ADR-0006
---

# Strimzi With Strict Resource Limits

The demo uses Strimzi-managed Kafka to support the asynchronous Booking Request flow, but it must run with a constrained single-node lab profile. The Kubernetes cluster is a learning lab and load tests should not allow Kafka to compete aggressively with application services, PostgreSQL, or node stability.

**Consequences**

Kafka should use one broker, replication factor `1`, small topic partition counts, short retention, small persistent volume claims, and explicit CPU and memory requests and limits. Production-style multi-broker Kafka, Kafka Connect, MirrorMaker, Kafka Bridge, and heavy metrics/logging integrations are outside the one-day scope.
