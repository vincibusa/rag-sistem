"""Change status column from ENUM to VARCHAR."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_change_status_to_varchar"
down_revision: str = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Cambia il tipo della colonna status da ENUM a VARCHAR
    # Prima convertiamo tutti i valori esistenti (anche se sono già stringhe)
    op.execute("""
        ALTER TABLE documents 
        ALTER COLUMN status TYPE VARCHAR(32) 
        USING status::text;
    """)
    
    # Rimuoviamo il tipo ENUM se non è più usato
    op.execute("""
        DROP TYPE IF EXISTS document_status CASCADE;
    """)


def downgrade() -> None:
    # Ricreiamo il tipo ENUM
    op.execute("""
        CREATE TYPE document_status AS ENUM ('new', 'processing', 'ready', 'failed');
    """)
    
    # Cambiamo il tipo della colonna da VARCHAR a ENUM
    op.execute("""
        ALTER TABLE documents 
        ALTER COLUMN status TYPE document_status 
        USING status::document_status;
    """)

