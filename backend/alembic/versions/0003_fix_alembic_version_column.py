"""Fix alembic_version column length."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_fix_alembic_version_column"
down_revision: str = "0002_change_status_to_varchar"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Increase the length of version_num column to accommodate longer revision IDs
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(50)")


def downgrade() -> None:
    # Revert to original length (though this might cause issues if we have long revision IDs)
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)")