from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestFastapiRoutes(BaseTestCase):
    def test_route_handlers_suppressed_unused_helper_still_reported(self):
        self.files = {
            'main.py': """
                from fastapi import FastAPI, APIRouter, Depends

                app = FastAPI()
                router = APIRouter()


                def get_db():
                    return "db"


                @app.get("/items")
                def list_items(db=Depends(get_db)):
                    return []


                @router.post("/items")
                def create_item():
                    return {}


                @app.websocket("/ws")
                async def websocket_endpoint():
                    return None


                @app.on_event("startup")
                async def on_startup():
                    return None


                def _unused_helper():
                    return 42
                """
        }

        output = main(
            [
                'main.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@app.*',
                '--ignore-definitions-if-decorated-with=@router.*',
            ]
        )

        self.assertEqual(output, 'main.py:31:0: DC02 Function `_unused_helper` is never used')

    def test_pydantic_models_suppressed_via_inherits_from(self):
        self.files = {
            'models.py': """
                from pydantic import BaseModel


                class Item(BaseModel):
                    name: str
                    price: float


                class UnusedPlainClass:
                    unused_attribute = None
                """
        }

        output = main(['models.py', '--no-color', '--ignore-definitions-if-inherits-from=BaseModel'])

        self.assertEqual(
            output,
            'models.py:9:0: DC03 Class `UnusedPlainClass` is never used\n'
            'models.py:10:4: DC01 Variable `unused_attribute` is never used',
        )
