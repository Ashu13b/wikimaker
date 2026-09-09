---
name: migration-safety
description: Audit database schema migrations for zero-downtime safety, non-blocking DDL, table lock risks, backfill strategies, and verified rollback procedures. Use before creating or modifying SQL migrations, ORM schemas (Prisma, Alembic, Django, Drizzle), or table structures.
---

# Database Migration & Schema Safety Guard

Perform an exhaustive safety audit on database migrations before applying them to production or staging databases.

The goal is to prevent exclusive table locks, downtime during deployments, data corruption, and irreversible schema changes.

---

## ⚡ Non-Negotiable Safety Rules

1. **No Table-Locking Operations on Populated Tables:**
   - Adding a column with `NOT NULL` without a default or in a blocking DDL pass is forbidden in PostgreSQL/MySQL.
   - Adding indexes without `CONCURRENTLY` (Postgres) or `ALGORITHM=INPLACE` (MySQL) is blocked.
2. **The Expand / Contract Pattern:**
   - **Phase 1 (Expand):** Add the new column/table as optional; deploy code that writes to both old and new columns.
   - **Phase 2 (Backfill):** Backfill existing rows in small, rate-limited batches.
   - **Phase 3 (Contract):** Deploy code reading only from the new column; drop the old column in a subsequent release.
3. **Mandatory Rollback Script:**
   Every `UP` migration must have a tested, non-destructive `DOWN` migration script.
4. **No Destructive Drops:**
   Never `DROP TABLE` or `DROP COLUMN` in the same deployment where application code is updated.

---

## 🔍 Migration Risk Checklist

- [ ] **Locking Risk:** Does the migration acquire an exclusive `ACCESS EXCLUSIVE` table lock?
- [ ] **Column Addition:** Is `ADD COLUMN` nullable or does it use fast metadata defaults (Postgres 11+)?
- [ ] **Index Creation:** Are indexes created concurrently without blocking writes?
- [ ] **Enum / Type Modification:** Are enum additions safe and non-locking?
- [ ] **Rollback Verified:** Can the down-migration be executed cleanly without data loss?

---

## 📋 Required Migration Audit Output

```markdown
### 🗄️ Database Migration Safety Report

- **Migration File:** `migrations/20260827_add_user_settings.sql`
- **Locking Assessment:** [Low / Safe | High - Table Lock Risk]
- **Expand/Contract Compliance:** [Compliant | Multi-phase required]
- **Rollback Safety:** [Verified | Missing Down Migration]
- **Verdict:** [APPROVED | BLOCK - REQUIRE CONCURRENT / EXPAND-CONTRACT]
```
