from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestSqlalchemyDeclarative(BaseTestCase):
    def test_2_0_models_suppressed_unused_helper_still_reported(self):
        self.files = {
            'models.py': """
                from sqlalchemy import String
                from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


                class Base(DeclarativeBase):
                    pass


                class User(Base):
                    __tablename__ = "users"

                    id: Mapped[int] = mapped_column(primary_key=True)
                    name: Mapped[str] = mapped_column(String(50))


                def _unused_helper():
                    return 42
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=Base',
                '--ignore-bodies-if-inherits-from=Base',
            ]
        )

        self.assertEqual(output, 'models.py:16:0: DC02 Function `_unused_helper` is never used')

    def test_1_x_models_with_column_assignments_suppressed(self):
        self.files = {
            'models.py': """
                from sqlalchemy import Column, Integer, String
                from sqlalchemy.orm import declarative_base


                Base = declarative_base()


                class User(Base):
                    __tablename__ = "users"

                    id = Column(Integer, primary_key=True)
                    name = Column(String)


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=Base',
                '--ignore-bodies-if-inherits-from=Base',
            ]
        )

        self.assertEqual(output, 'models.py:15:0: DC01 Variable `UNUSED_CONSTANT` is never used')

    def test_event_listeners_suppressed_via_decorator(self):
        self.files = {
            'listeners.py': """
                from sqlalchemy import event

                from models import User


                @event.listens_for(User, "before_insert")
                def set_created(mapper, connection, target):
                    target.created = True


                def _unused_listener_helper():
                    return None
                """
        }

        output = main(
            [
                'listeners.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@event.*',
            ]
        )

        self.assertEqual(output, 'listeners.py:11:0: DC02 Function `_unused_listener_helper` is never used')

    def test_flask_sqlalchemy_db_model_suppressed(self):
        self.files = {
            'models.py': """
                from flask_sqlalchemy import SQLAlchemy


                db = SQLAlchemy()


                class User(db.Model):
                    __tablename__ = "users"

                    id = db.Column(db.Integer, primary_key=True)
                    name = db.Column(db.String)


                UNUSED_FLAG = True
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=db.Model',
                '--ignore-bodies-if-inherits-from=db.Model',
            ]
        )

        self.assertEqual(output, 'models.py:14:0: DC01 Variable `UNUSED_FLAG` is never used')
