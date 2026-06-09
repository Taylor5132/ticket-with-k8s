# Booking Service Owns Asynchronous Booking

The booking-service owns Booking Requests, confirmed Bookings, and Redis Streams-based asynchronous booking processing. For one-day development, the HTTP API and queue worker run as separate Kubernetes workloads from the same service codebase so they can scale independently without introducing a separate queue-service boundary.

**Considered Options**

- Keep the Redis Streams producer and consumer inside booking-service, split into `booking-api` and `booking-worker` pods.
- Create a separate queue-service or orchestrator-service.

**Consequences**

Booking ownership stays clear and the demo remains small enough to finish in one day. The trade-off is that booking-service contains both HTTP and worker responsibilities, so the codebase should keep those entrypoints separated even though they share the same domain and database.
