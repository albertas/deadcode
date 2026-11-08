from fastapi import FastAPI

from models import User
from routes import users

app = FastAPI()
app.include_router(users.router)

SETTING = 'value'


def log_startup() -> None:
    print(SETTING)


def health() -> dict[str, str]:
    return {'status': 'ok'}


app.add_api_route('/health', health)


@app.on_event('startup')
async def on_startup() -> None:
    log_startup()


@app.get('/me')
def read_me() -> User:
    return User(name='me')


UNUSED_SETTING = 'unused'


def unused_handler() -> None:
    pass
