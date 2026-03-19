from alembic import op
import sqlalchemy as sa


revision = "0005_runs_idempotency_key"
down_revision = "0004_project_description"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_unique_constraint(
        "uq_runs_tenant_project_idempotency_key",
        "runs",
        ["tenant_id", "project_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_runs_tenant_project_idempotency_key", "runs", type_="unique")
    op.drop_column("runs", "idempotency_key")
