# Monorepo For One-Day Demo

The demo uses a monorepo containing the React frontend, FastAPI backend services, and Kubernetes manifests. This keeps local development and deployment coordination simple while still allowing each backend service to run as an independent container and Kubernetes workload.

**Consequences**

Service boundaries are enforced by APIs, databases, and deployments rather than by separate repositories. A production version could split services into separate repositories if independent release ownership becomes more important.
