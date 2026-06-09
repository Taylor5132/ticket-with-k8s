# One Postgres Instance With Service Databases

The demo uses one PostgreSQL instance in Kubernetes with separate databases and credentials for each backend service. This preserves service data ownership for the one-day MSA demo while avoiding the operational overhead of running separate PostgreSQL pods per service.

**Consequences**

The system has logical database isolation rather than physical database isolation. A production version could split high-risk or high-load services into separate database instances later.
