import json

from alembic import op
import sqlalchemy as sa

revision = "0003_normalize_policy_defaults"
down_revision = "0002_production_hardening"
branch_labels = None
depends_on = None


def _as_list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return list(value)


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, allowed_tool_patterns, denied_tool_patterns FROM project_policies")
    ).fetchall()
    policy_table = sa.table(
        "project_policies",
        sa.column("id", sa.String(36)),
        sa.column("allowed_tool_patterns", sa.JSON()),
        sa.column("denied_tool_patterns", sa.JSON()),
    )
    for row in rows:
        allowed = _as_list(row.allowed_tool_patterns)
        denied = _as_list(row.denied_tool_patterns)
        for pattern in ("python_execute", "sandbox*"):
            if pattern not in allowed:
                allowed.append(pattern)
            denied = [item for item in denied if item != pattern]
        connection.execute(
            policy_table.update().where(policy_table.c.id == row.id).values(
                allowed_tool_patterns=allowed,
                denied_tool_patterns=denied,
            )
        )


def downgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, allowed_tool_patterns, denied_tool_patterns FROM project_policies")
    ).fetchall()
    policy_table = sa.table(
        "project_policies",
        sa.column("id", sa.String(36)),
        sa.column("allowed_tool_patterns", sa.JSON()),
        sa.column("denied_tool_patterns", sa.JSON()),
    )
    for row in rows:
        allowed = [item for item in _as_list(row.allowed_tool_patterns) if item not in {"python_execute", "sandbox*"}]
        denied = _as_list(row.denied_tool_patterns)
        for pattern in ("python_execute", "sandbox*"):
            if pattern not in denied:
                denied.append(pattern)
        connection.execute(
            policy_table.update().where(policy_table.c.id == row.id).values(
                allowed_tool_patterns=allowed,
                denied_tool_patterns=denied,
            )
        )
