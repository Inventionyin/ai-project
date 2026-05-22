from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_add_user_auth_fields"
down_revision = "0001_init_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("hashed_password", sa.String(length=255), nullable=False, server_default=""))
    op.add_column(
        "users",
        sa.Column(
            "roles_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_unique_constraint("uq_users_tenant_username", "users", ["tenant_id", "username"])


def downgrade() -> None:
    op.drop_constraint("uq_users_tenant_username", "users", type_="unique")
    op.drop_column("users", "roles_json")
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "username")
