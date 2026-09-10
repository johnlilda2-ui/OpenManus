import os

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_postgres_schema_is_migrated_in_ci():
    if not os.getenv("CI") or not os.getenv("DATABASE_URL", "").startswith("postgresql"):
        pytest.skip("PostgreSQL integration test runs in CI")
    from platform_core.database import engine

    expected = {
        "users",
        "projects",
        "tenants",
        "tenant_members",
        "project_policies",
        "approval_requests",
        "memory_entries",
        "knowledge_documents",
        "workflows",
        "workflow_runs",
        "workflow_step_runs",
        "artifacts",
        "project_quotas",
        "usage_records",
    }
    async with engine.begin() as connection:
        result = await connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
        tables = {row[0] for row in result}
    assert expected.issubset(tables)
