# Redis Streams For Booking Queue

The one-day demo uses Redis Streams for asynchronous Booking Request processing instead of Strimzi-managed Kafka. The application needs queue-style worker processing rather than a long-lived event streaming platform, and Redis is already required for Saved Performances, so this reduces Kubernetes load and delivery risk.

**Consequences**

Redis now supports both Saved Performances and the Booking Queue. Strimzi/Kafka is deferred to a later infrastructure-learning track, and the application should keep the queue interface narrow enough that Kafka can replace Redis Streams later if that becomes a learning goal.
