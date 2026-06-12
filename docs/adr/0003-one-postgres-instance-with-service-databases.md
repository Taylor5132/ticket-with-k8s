# One Postgres Instance With Service Databases

The demo uses one PostgreSQL instance in Kubernetes with separate databases and credentials for each backend service. This preserves service data ownership for the one-day MSA demo while avoiding the operational overhead of running separate PostgreSQL pods per service.

**Consequences**

The system has logical database isolation rather than physical database isolation. A production version could split high-risk or high-load services into separate database instances later.

> **2026-06-12 보정**: 결정문의 "separate credentials for each backend service"는 구현되지 않았다 — 현재 모든 서비스가 postgres 슈퍼유저 계정을 공유한다. 논리적 DB 분리는 결정대로 유지 중이며, 서비스별 계정 분리는 향후 보안 강화 항목으로 남는다.
