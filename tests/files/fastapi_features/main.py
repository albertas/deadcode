from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from errors import NotFoundError
from middleware import TimingMiddleware
from models import Item
from routes import items
from security import get_current_user, verify_api_key

SETTING = 'value'


def log_startup() -> None:
    print(SETTING)


def current_user_name(user: Annotated[str, Depends(get_current_user)]) -> str:
    return user


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_startup()
    yield


app = FastAPI(title='Feature example', version='1.0.0', lifespan=lifespan, dependencies=[Depends(verify_api_key)])
app.add_middleware(TimingMiddleware)
app.include_router(items.router)
app.include_router(items.admin_router)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, error: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={'detail': str(error)})


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={'detail': error.detail})


@app.middleware('http')
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)
    response.headers['x-process-time'] = '0'
    return response


@app.get('/me', response_model=dict[str, str])
async def read_me(user: Annotated[str, Depends(get_current_user)]) -> dict[str, str]:
    return {'user': user}


@app.get('/redirect')
def redirect() -> RedirectResponse:
    return RedirectResponse('/me')


@app.get('/stream')
def stream() -> StreamingResponse:
    def generate():
        yield b'item'

    return StreamingResponse(generate())


@app.head('/health')
def health() -> None:
    pass


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, user: Annotated[str, Depends(get_current_user)]) -> None:
    await websocket.accept()
    del user
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


def health_check() -> dict[str, str]:
    return {'status': 'ok'}


app.add_api_route('/health', health_check)


def custom_openapi() -> dict[str, object]:
    return app.openapi()


app.openapi = custom_openapi


def unused_handler(item: Item) -> None:
    print(item)
