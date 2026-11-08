from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials

from dependencies import (
    Pagination,
    Settings,
    get_client,
    get_current_user,
    get_database,
    get_optional_user,
    get_settings,
    request_id,
)
from models import User
from security import get_basic_user, require_admin, verify_api_key

# Type aliases keep dependency declarations reusable.
CurrentUser = Annotated[str, Depends(get_current_user)]
Database = Annotated[object, Depends(get_database)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
OptionalUser = Annotated[str | None, Depends(get_optional_user)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def write_audit(message: str) -> None:
    print(message)


app = FastAPI(lifespan=lifespan, dependencies=[Depends(verify_api_key)])
router = APIRouter(prefix='/dependency', dependencies=[Depends(require_admin)])


@app.get('/annotated')
def annotated_dependencies(
    user: CurrentUser,
    database: Database,
    settings: SettingsDependency,
    pagination: Annotated[Pagination, Depends()],
) -> dict[str, object]:
    return {
        'user': user,
        'database': database,
        'app_name': settings.app_name,
        'skip': pagination.skip,
        'limit': pagination.limit,
    }


@app.get('/default')
def default_dependencies(
    user: str = Depends(get_current_user),
    database: object = Depends(get_database),
    client: object = Depends(get_client),
    identifier: str = Depends(request_id),
    pagination: Pagination = Depends(Pagination),  # noqa: B008
) -> dict[str, object]:
    return {'user': user, 'database': database, 'client': client, 'identifier': identifier, 'pagination': pagination}


@app.get('/class')
def class_dependency(pagination: Pagination = Depends()) -> dict[str, int]:  # noqa: B008
    return {'skip': pagination.skip, 'limit': pagination.limit}


@app.get('/optional')
def optional_dependency(user: OptionalUser) -> dict[str, str | None]:
    return {'user': user}


@router.get('/sub')
def sub_dependency(
    user: str = Depends(get_current_user),
    admin: str = Depends(require_admin),
    basic: str = Depends(get_basic_user),
    credentials: HTTPAuthorizationCredentials | None = None,
    request: Request | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> dict[str, object]:
    if background_tasks is not None:
        background_tasks.add_task(write_audit, 'sub dependency')
    return {'user': user, 'admin': admin, 'basic': basic, 'credentials': credentials, 'request': request}


@app.get('/operation', dependencies=[Depends(verify_api_key), Depends(get_current_user)])
def operation_dependency(user: User = Depends(get_current_user)) -> User:  # noqa: B008
    return User(name=user)


@app.get('/cached')
def cached_dependency(
    first: Settings = Depends(get_settings),  # noqa: B008
    second: Settings = Depends(get_settings, use_cache=False),  # noqa: B008
) -> dict[str, str]:
    return {'first': first.app_name, 'second': second.app_name}


@app.websocket('/ws')
async def websocket_dependency(websocket: WebSocket, user: str = Depends(get_current_user)) -> None:
    await websocket.accept()
    await websocket.send_text(user)
    try:
        await websocket.receive_text()
    except WebSocketDisconnect:
        return


app.include_router(router)
app.dependency_overrides[get_database] = lambda: object()
app.add_api_route('/manual', default_dependencies, methods=['GET'], dependencies=[Depends(get_current_user)])
