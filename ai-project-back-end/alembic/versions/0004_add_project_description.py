from alembic import op
import sqlalchemy as sa


revision = "0004_project_description"
down_revision = "0003_user_phone_nullable_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "description")
