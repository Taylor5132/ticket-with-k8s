# Gateway API With Istio

The Kubernetes deployment uses Gateway API with Istio as the implementation for ingress routing. This keeps the routing model aligned with modern Kubernetes APIs while still using Istio for mesh-aware traffic management.

**Consequences**

Ingress manifests should use `GatewayClass`, `Gateway`, and `HTTPRoute` rather than Istio `Gateway` and `VirtualService` as the primary path. Istio `Gateway` and `VirtualService` remain fallback options only if the cluster's Gateway API support is unavailable.
