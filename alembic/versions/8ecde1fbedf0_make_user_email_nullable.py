"""make user email nullable

Revision ID: 8ecde1fbedf0
Revises: 
Create Date: 2026-10-24 13:29:21.096019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ecde1fbedf0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.alter_column(
        "user",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "email",
        existing_type=sa.String(length=255),
        nullable=False,
    )

