from alembic import op
import sqlalchemy as sa


revision = "0003_user_phone_nullable_email"
down_revision = "0002_add_user_auth_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_users_tenant_phone", "users", ["tenant_id", "phone"])
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.drop_constraint("uq_users_tenant_phone", "users", type_="unique")
    op.drop_column("users", "phone")
