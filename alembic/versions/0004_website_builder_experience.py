from alembic import op
import sqlalchemy as sa

revision = "0004_website_builder_experience"
down_revision = "0003_normalize_policy_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "website_design_systems",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_run_id", sa.String(36), sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tokens", sa.JSON(), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("guidelines", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", name="uq_website_design_system_project_id"),
    )
    op.create_index("ix_website_design_systems_project_id", "website_design_systems", ["project_id"], unique=False)
    op.create_index("ix_website_design_systems_source_run_id", "website_design_systems", ["source_run_id"], unique=False)

    op.create_table(
        "website_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_run_id", sa.String(36), sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_id", sa.String(120), nullable=False),
        sa.Column("page", sa.String(300), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("anchor", sa.String(200), nullable=True),
        sa.Column("selector", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "section_id", name="uq_website_section_project_id"),
    )
    op.create_index("ix_website_sections_project_id", "website_sections", ["project_id"], unique=False)
    op.create_index("ix_website_sections_source_run_id", "website_sections", ["source_run_id"], unique=False)

    op.create_table(
        "website_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_run_id", sa.String(36), sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_id", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("path", sa.String(1000), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("alt_text", sa.String(1000), nullable=True),
        sa.Column("usage", sa.String(500), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "asset_id", name="uq_website_asset_project_id"),
    )
    op.create_index("ix_website_assets_project_id", "website_assets", ["project_id"], unique=False)
    op.create_index("ix_website_assets_source_run_id", "website_assets", ["source_run_id"], unique=False)

    op.create_table(
        "website_visual_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("viewport", sa.String(120), nullable=True),
        sa.Column("visual_hash", sa.String(128), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("diff_score", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_website_visual_snapshots_project_id", "website_visual_snapshots", ["project_id"], unique=False)
    op.create_index("ix_website_visual_snapshots_run_id", "website_visual_snapshots", ["run_id"], unique=False)

    op.create_table(
        "website_iterations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_run_id", sa.String(36), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_run_id", sa.String(36), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.String(120), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_website_iterations_project_id", "website_iterations", ["project_id"], unique=False)
    op.create_index("ix_website_iterations_parent_run_id", "website_iterations", ["parent_run_id"], unique=False)
    op.create_index("ix_website_iterations_workflow_run_id", "website_iterations", ["workflow_run_id"], unique=False)
    op.create_index("ix_website_iterations_section_id", "website_iterations", ["section_id"], unique=False)
    op.create_index("ix_website_iterations_status", "website_iterations", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_website_iterations_status", table_name="website_iterations")
    op.drop_index("ix_website_iterations_section_id", table_name="website_iterations")
    op.drop_index("ix_website_iterations_workflow_run_id", table_name="website_iterations")
    op.drop_index("ix_website_iterations_parent_run_id", table_name="website_iterations")
    op.drop_index("ix_website_iterations_project_id", table_name="website_iterations")
    op.drop_table("website_iterations")

    op.drop_index("ix_website_visual_snapshots_run_id", table_name="website_visual_snapshots")
    op.drop_index("ix_website_visual_snapshots_project_id", table_name="website_visual_snapshots")
    op.drop_table("website_visual_snapshots")

    op.drop_index("ix_website_assets_source_run_id", table_name="website_assets")
    op.drop_index("ix_website_assets_project_id", table_name="website_assets")
    op.drop_table("website_assets")

    op.drop_index("ix_website_sections_source_run_id", table_name="website_sections")
    op.drop_index("ix_website_sections_project_id", table_name="website_sections")
    op.drop_table("website_sections")

    op.drop_index("ix_website_design_systems_source_run_id", table_name="website_design_systems")
    op.drop_index("ix_website_design_systems_project_id", table_name="website_design_systems")
    op.drop_table("website_design_systems")
