from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestAlembicMigrations(BaseTestCase):
    def test_migration_callbacks_and_revision_ids_suppressed_via_ignore_names(self):
        self.files = {
            'versions/abc123_init.py': """
                from alembic import op
                import sqlalchemy as sa


                revision = "abc123"
                down_revision = None
                branch_labels = None
                depends_on = None


                def upgrade():
                    op.create_table("users", sa.Column("id", sa.Integer))


                def downgrade():
                    op.drop_table("users")


                def _unused_migration_helper():
                    return None
                """
        }

        output = main(
            [
                'versions/abc123_init.py',
                '--no-color',
                '--ignore-names=upgrade',
                '--ignore-names=downgrade',
                '--ignore-names=revision',
                '--ignore-names=down_revision',
                '--ignore-names=branch_labels',
                '--ignore-names=depends_on',
            ]
        )

        self.assertEqual(
            output,
            'versions/abc123_init.py:19:0: DC02 Function `_unused_migration_helper` is never used',
        )

    def test_versions_directory_suppressed_via_ignore_names_in_files(self):
        self.files = {
            'versions/abc123_init.py': """
                from alembic import op
                import sqlalchemy as sa


                revision = "abc123"
                down_revision = None


                def upgrade():
                    op.create_table("users")


                def downgrade():
                    op.drop_table("users")
                """,
            'service.py': """
                def _genuinely_unused():
                    return None
                """,
        }

        output = main(
            [
                'versions/abc123_init.py',
                'service.py',
                '--no-color',
                '--ignore-names-in-files=*versions*',
            ]
        )

        self.assertEqual(output, 'service.py:1:0: DC02 Function `_genuinely_unused` is never used')
