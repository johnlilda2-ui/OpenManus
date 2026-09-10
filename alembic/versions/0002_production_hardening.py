from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "0002_production_hardening"
down_revision = "0001_platform_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tenants_created_at", "tenants", ["created_at"])

    op.create_table(
        "tenant_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_member"),
    )
    op.create_index("ix_tenant_members_tenant_id", "tenant_members", ["tenant_id"])
    op.create_index("ix_tenant_members_user_id", "tenant_members", ["user_id"])

    op.add_column("projects", sa.Column("tenant_id", sa.String(36), nullable=True))
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])
    op.create_foreign_key("fk_projects_tenant_id", "projects", "tenants", ["tenant_id"], ["id"], ondelete="SET NULL")

    projects = table(
        "projects",
        column("id", sa.String(36)),
        column("owner_id", sa.String(36)),
        column("name", sa.String(200)),
        column("created_at", sa.DateTime(timezone=True)),
    )
    tenants = table(
        "tenants",
        column("id", sa.String(36)),
        column("name", sa.String(200)),
        column("created_at", sa.DateTime(timezone=True)),
    )
    members = table(
        "tenant_members",
        column("id", sa.String(36)),
        column("tenant_id", sa.String(36)),
        column("user_id", sa.String(36)),
        column("role", sa.String(32)),
        column("created_at", sa.DateTime(timezone=True)),
    )

    # Existing projects become one-tenant-per-project. Using the project id as
    # the initial tenant id keeps the migration deterministic on Postgres and SQLite.
    op.execute(sa.text("INSERT INTO tenants (id, name, created_at) SELECT id, name, created_at FROM projects"))
    op.execute(sa.text("UPDATE projects SET tenant_id = id"))
    op.execute(sa.text("INSERT INTO tenant_members (id, tenant_id, user_id, role, created_at) SELECT id || '-owner', id, owner_id, 'owner', created_at FROM projects"))

    op.add_column("artifacts", sa.Column("sha256", sa.String(64), nullable=True))
    op.add_column("usage_records", sa.Column("usage_source", sa.String(32), nullable=False, server_default="estimated"))
    op.alter_column("usage_records", "usage_source", server_default=None)


def downgrade() -> None:
    op.drop_column("usage_records", "usage_source")
    op.drop_column("artifacts", "sha256")
    op.drop_constraint("fk_projects_tenant_id", "projects", type_="foreignkey")
    op.drop_index("ix_projects_tenant_id", table_name="projects")
    op.drop_column("projects", "tenant_id")
    op.drop_index("ix_tenant_members_user_id", table_name="tenant_members")
    op.drop_index("ix_tenant_members_tenant_id", table_name="tenant_members")
    op.drop_table("tenant_members")
    op.drop_index("ix_tenants_created_at", table_name="tenants")
    op.drop_table("tenants")
