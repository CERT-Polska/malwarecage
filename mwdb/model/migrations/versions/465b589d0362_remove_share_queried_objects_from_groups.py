"""Remove share_queried_objects from groups

Revision ID: 465b589d0362
Revises: 56adf974831e
Create Date: 2024-12-12 14:39:21.117379

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "465b589d0362"
down_revision = "56adf974831e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE \"group\" SET capabilities = array_remove(capabilities, 'share_queried_objects');"
    )
    pass


def downgrade():
    pass
