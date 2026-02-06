"""add_report_type_to_financial_unique_constraint

Revision ID: 2f57f7625d3f
Revises: 447f373a6d46
Create Date: 2026-02-06 01:16:52.879298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f57f7625d3f'
down_revision: Union[str, None] = '447f373a6d46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 기존 unique constraint 삭제
    op.drop_constraint('uq_financial_period', 'financial_statements', type_='unique')

    # 새 unique constraint 생성 (report_type 포함)
    op.create_unique_constraint(
        'uq_financial_period',
        'financial_statements',
        ['company_id', 'fiscal_year', 'fiscal_quarter', 'report_type']
    )


def downgrade() -> None:
    # 새 constraint 삭제
    op.drop_constraint('uq_financial_period', 'financial_statements', type_='unique')

    # 기존 constraint 복원
    op.create_unique_constraint(
        'uq_financial_period',
        'financial_statements',
        ['company_id', 'fiscal_year', 'fiscal_quarter']
    )
