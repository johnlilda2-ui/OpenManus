from alembic import op
import sqlalchemy as sa

revision = "0005_workflow_approval_targets"
down_revision = "0004_website_builder_experience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("approval_requests") as batch_op:
        batch_op.alter_column(
            "task_id",
            existing_type=sa.String(36),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("workflow_run_id", sa.String(36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_approval_requests_workflow_run_id",
            "workflow_runs",
            ["workflow_run_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_approval_requests_workflow_run_id",
            ["workflow_run_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("approval_requests") as batch_op:
        batch_op.drop_index("ix_approval_requests_workflow_run_id")
        batch_op.drop_constraint(
            "fk_approval_requests_workflow_run_id", type_="foreignkey"
        )
        batch_op.drop_column("workflow_run_id")
        batch_op.alter_column(
            "task_id",
            existing_type=sa.String(36),
            nullable=False,
        )
