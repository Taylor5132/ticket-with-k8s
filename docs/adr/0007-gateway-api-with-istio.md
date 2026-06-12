# Gateway API With Istio

The Kubernetes deployment uses Gateway API with Istio as the implementation for ingress routing. This keeps the routing model aligned with modern Kubernetes APIs while still using Istio for mesh-aware traffic management.

**Consequences**

Ingress manifests should use `GatewayClass`, `Gateway`, and `HTTPRoute` rather than Istio `Gateway` and `VirtualService` as the primary path. Istio `Gateway` and `VirtualService` remain fallback options only if the cluster's Gateway API support is unavailable.

> **2026-06-12 보정**: 실운영에서 한 가지 예외가 추가됐다 — `/api/performances/{id}/seat-availability`의 regex 캡처 경로 재작성은 Gateway API 표준으로 표현 불가해 Istio `EnvoyFilter` 1건을 병행 사용 중이다. VirtualService 없이 HTTPRoute + EnvoyFilter 조합이 현재 구성이다.
