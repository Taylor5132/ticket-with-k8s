# Infrastructure Plan

> **2026-06-12 현행화**: 이 계획의 대부분은 실행 완료됐다. 네임스페이스는 `ticket-*` 대신 `frontend`/`backend`/`db`로 채택됐고, "보류"였던 관측 스택과 GitOps는 모두 가동 중이다. 상세 설계·현재 상태는 `docs/ops/K8S_STACK.md` 참조.

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

Deferred (→ 이후 진행 상태):
- Helm charts until raw manifests work. (여전히 예정)
- Strimzi/Kafka. (여전히 예정 — ADR-0005/0006 참조)
- Heavy observability stack. → **구현됨**: monitoring NS에 VictoriaMetrics·Loki·Grafana·Alertmanager·Alloy·Tempo·OTel Collector 가동, 서비스에 telemetry.py 계측.
- Production-grade backup/restore automation. (여전히 예정)
- GitOps automation unless the prototype has time left. → **구현됨**: ArgoCD가 GitLab team6/manifest를 동기화하는 것이 기본 배포 경로.

## Namespace Strategy

Use multiple namespaces for a more realistic lab deployment, especially because Cilium NetworkPolicy and Istio ambient may enforce default-deny behavior.

Namespaces (계획 명칭 → **실제 채택 명칭**):
- `ticket-web` → **`frontend`**: React frontend + Gateway(booking-gw) + cloudflared (별도 ingress NS 없이 통합).
- `ticket-backend` → **`backend`**: FastAPI application services and `booking-worker`.
- `ticket-data` → **`db`**: PostgreSQL and Redis.
- `ticket-ingress`: 채택 안 됨 — Gateway 리소스는 frontend NS에 함께 배치.

Initial rule:
- Keep application services in `ticket-backend` unless a later operational reason appears to split every service into its own namespace.
- Keep stateful dependencies in `ticket-data`.
- Keep namespace count small enough that policies remain understandable during the one-day deployment.

Deferred split:
- Per-service namespaces such as `ticket-auth`, `ticket-booking`, and `ticket-payment`.
- Separate observability namespace for app-specific monitoring.
