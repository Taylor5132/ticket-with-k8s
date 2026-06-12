# Monorepo For One-Day Demo

The demo uses a monorepo containing the React frontend, FastAPI backend services, and Kubernetes manifests. This keeps local development and deployment coordination simple while still allowing each backend service to run as an independent container and Kubernetes workload.

**Consequences**

Service boundaries are enforced by APIs, databases, and deployments rather than by separate repositories. A production version could split services into separate repositories if independent release ownership becomes more important.

> **2026-06-12 보정**: 결정문 중 "Kubernetes manifests를 모노레포에 포함" 부분은 변경됐다 — GitOps 도입에 따라 매니페스트는 별도 repo(GitLab `team6/manifest`)로 분리됐고 ArgoCD가 이를 동기화한다 (app repo + manifest repo 2-repo 패턴). 앱 코드의 모노레포 결정 자체는 유지 중이다.
