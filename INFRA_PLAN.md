# Infrastructure Plan

This plan starts after the Docker Compose prototype passes the acceptance checklist. The Kubernetes cluster is a learning lab, so infrastructure choices should favor clear service wiring, safe resource usage, and fast iteration over production completeness.

## Starting Constraints

- Application is a monorepo with React frontend and FastAPI services.
- Docker Compose prototype is the first runtime target.
- Kubernetes work starts after the local prototype is clickable and reviewed.
- Day-one async processing uses Redis Streams, not Strimzi/Kafka.
- PostgreSQL runs as one instance with service-owned databases.
- Redis supports both Saved Performances and Booking Request processing.
- Raw Kubernetes manifests come before Helm migration.
- Istio is available for ingress/routing through Gateway API.
- Cilium is available for cluster networking.

## Infrastructure Scope

Included:
- Namespace layout.
- Image build and push strategy.
- PostgreSQL and Redis deployment shape.
- Application Deployments and Services.
- Gateway API routing implemented by Istio.
- ConfigMap/Secret strategy.
- Resource requests and limits.
- Health checks.
- Basic logs and smoke validation.

Deferred:
- Helm charts until raw manifests work.
- Strimzi/Kafka.
- Heavy observability stack.
- Production-grade backup/restore automation.
- GitOps automation unless the prototype has time left.

## Namespace Strategy

Use multiple namespaces for a more realistic lab deployment, especially because Cilium NetworkPolicy and Istio ambient may enforce default-deny behavior.

Namespaces:
- `ticket-web`: React frontend and ingress-facing web workload.
- `ticket-backend`: FastAPI application services and `booking-worker`.
- `ticket-data`: PostgreSQL and Redis.
- `ticket-ingress`: Gateway API resources if the cluster convention keeps gateways separate.

Initial rule:
- Keep application services in `ticket-backend` unless a later operational reason appears to split every service into its own namespace.
- Keep stateful dependencies in `ticket-data`.
- Keep namespace count small enough that policies remain understandable during the one-day deployment.

Deferred split:
- Per-service namespaces such as `ticket-auth`, `ticket-booking`, and `ticket-payment`.
- Separate observability namespace for app-specific monitoring.
