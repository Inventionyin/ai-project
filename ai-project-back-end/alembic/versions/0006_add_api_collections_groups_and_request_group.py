from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_api_collection_groups"
down_revision = "0005_runs_idempotency_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_collection_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_collections.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_api_collection_groups_tenant_id", "api_collection_groups", ["tenant_id"])
    op.create_index("ix_api_collection_groups_collection_id", "api_collection_groups", ["collection_id"])

    op.add_column(
        "api_requests",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_collection_groups.id"), nullable=True),
    )
    op.create_index("ix_api_requests_group_id", "api_requests", ["group_id"])

    op.add_column(
        "api_requests",
        sa.Column(
            "auth_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("api_requests", "auth_json")
    op.drop_index("ix_api_requests_group_id", table_name="api_requests")
    op.drop_column("api_requests", "group_id")

    op.drop_index("ix_api_collection_groups_collection_id", table_name="api_collection_groups")
    op.drop_index("ix_api_collection_groups_tenant_id", table_name="api_collection_groups")
    op.drop_table("api_collection_groups")
