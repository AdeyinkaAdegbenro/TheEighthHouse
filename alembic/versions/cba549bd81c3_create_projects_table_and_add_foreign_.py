"""create_projects_table_and_add_foreign_keys

Revision ID: cba549bd81c3
Revises: 
Create Date: 2026-06-07 00:23:03.363718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cba549bd81c3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Create the Master Projects Table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('folder_name', sa.String(length=50), nullable=False, unique=True)
    )

    # 2. Use Batch Mode to update the 'shots' table safely in SQLite
    with op.batch_alter_table('shots', schema=None) as batch_op:
        # Adds project_id and defaults existing shots to Project #1 (Last Parcel)
        batch_op.add_column(sa.Column('project_id', sa.Integer(), server_default='1', nullable=True))
    
    # 3. Use Batch Mode to update the 'script_data' table safely
    with op.batch_alter_table('script_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), server_default='1', nullable=True))
        # Enforce unique constraint so a movie only has one active script script
        batch_op.create_unique_constraint('uq_script_project_id', ['project_id'])

def downgrade():
    # Reverse the steps exactly if you ever need to roll back
    with op.batch_alter_table('script_data', schema=None) as batch_op:
        batch_op.drop_constraint('uq_script_project_id', type_='unique')
        batch_op.drop_column('project_id')

    with op.batch_alter_table('shots', schema=None) as batch_op:
        batch_op.drop_column('project_id')

    op.drop_table('projects')