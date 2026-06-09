# Redis-Backed Saved Performances

Saved Performances are stored in Redis for the one-day demo instead of a dedicated PostgreSQL table. This keeps the My Page wishlist feature small, demonstrates Redis in the architecture, and avoids adding persistence complexity to data that does not affect bookings or payments.

**Consequences**

Saved Performances are intentionally lower durability than Bookings and Point Payments. A production version should move Saved Performances to PostgreSQL and use Redis as a cache rather than the source of truth.
