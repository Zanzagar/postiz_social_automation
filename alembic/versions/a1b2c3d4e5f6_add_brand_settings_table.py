"""add brand_settings table with seed data

Revision ID: a1b2c3d4e5f6
Revises: 757e503cb80d
Create Date: 2026-03-24 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "757e503cb80d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create brand_settings key-value table and seed defaults."""
    op.create_table(
        "brand_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # Seed defaults matching current BRAND_RULES in generator.py
    op.execute(
        "INSERT INTO brand_settings (key, value) VALUES "
        "('brand_name', 'Gita Valley'), "
        "('tagline', 'Cultivating Soil and Soul'), "
        "('website', 'gitavalley.org'), "
        "('key_claim', "
        "'Only USDA Certified Slaughter-Free Dairy Farm in North America'), "
        "('products', "
        "'Ahimsa (cruelty-free) dairy — paneer, cheddar, mozzarella')"
    )


def downgrade() -> None:
    op.drop_table("brand_settings")
