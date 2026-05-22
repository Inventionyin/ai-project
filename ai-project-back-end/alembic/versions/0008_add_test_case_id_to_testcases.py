from alembic import op
import sqlalchemy as sa


revision = "0008_add_test_case_id"
down_revision = "0007_ai_import_binding_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("testcases", sa.Column("test_case_id", sa.String(length=64), nullable=True))
    op.create_index(
        "uq_testcases_project_test_case_id",
        "testcases",
        ["project_id", "test_case_id"],
        unique=True,
        postgresql_where=sa.text("test_case_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_testcases_project_test_case_id", table_name="testcases")
    op.drop_column("testcases", "test_case_id")
