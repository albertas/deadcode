# FastAPI

deadcode is framework-agnostic: it parses source code and never imports it. FastAPI registers route handlers, event handlers, and model fields at
runtime, so code that is reachable only through a decorator or a Pydantic base class looks unused to a static analyser. This page shows the
recommended configuration, documents common use cases, and gives a complete example application that produces no wrong detections.

## Recommended configuration

Add these options to `pyproject.toml`:

```toml
[tool.deadcode]
ignore-names-if-decorated-with = ["@app.*", "@router.*"]
ignore-bodies-if-inherits-from = ["BaseModel"]
```

The same options are available as command-line flags:

```shell
deadcode . --ignore-names-if-decorated-with='@app.*' --ignore-names-if-decorated-with='@router.*' \
    --ignore-bodies-if-inherits-from=BaseModel
```

`@app.*` covers every path operation (`get`, `post`, `put`, `patch`, `delete`, `head`, `options`, `trace`), `@app.on_event`, `@app.middleware`,
`@app.exception_handler`, and `@app.websocket`. `@router.*` does the same for an `APIRouter` instance named `router`. A different instance name
needs its own pattern, for example `@api.*` for `api = APIRouter()`.

`ignore-bodies-if-inherits-from = ["BaseModel"]` analyses the body of a class that inherits `BaseModel` but does not report the fields and
validator methods defined there. The class name itself is still reported when the class is never used.

## Common use cases

| FastAPI feature | Configuration needed |
|-----------------|----------------------|
| `@app.get`, `@app.post`, `@app.put`, `@app.patch`, `@app.delete`, `@app.head`, `@app.options`, `@app.trace` | Covered by `@app.*` |
| `@app.on_event`, `@app.middleware`, `@app.exception_handler`, `@app.websocket` | Covered by `@app.*` |
| `@router.get` and the other `APIRouter` decorators | Covered by `@router.*` |
| `api = APIRouter()` or any other router variable | Add `@api.*` or the matching name |
| A mounted sub-application, `subapp = FastAPI()` | Add `@subapp.*` |
| Pydantic model fields and validators | `ignore-bodies-if-inherits-from = ["BaseModel"]` |
| `RootModel`, `BaseSettings`, or a custom model base class | Add the base class name to `ignore-bodies-if-inherits-from` |
| Dependency injection with `Depends`, `Security`, or `Annotated` | None, see [Dependency injection](#dependency-injection) |
| `app.include_router(...)`, `app.add_api_route(...)`, `app.dependency_overrides[...]` | None, these are ordinary name loads |
| Class-based middleware inheriting `BaseHTTPMiddleware` | Add `ignore-names = ["dispatch"]`, because the framework calls `dispatch` |

A class-based middleware is the one common case that needs an extra name pattern. `BaseHTTPMiddleware.dispatch` is an override that FastAPI and
Starlette call; deadcode does not resolve base-class overrides. Function-based middleware registered with `@app.middleware("http")` needs no
extra pattern because `@app.*` already covers the decorator.

## Example application

The acceptance fixture in `tests/files/fastapi` is a small multi-module application. It uses an application-level route decorator, an
`APIRouter`, `include_router`, `add_api_route`, an event handler, a Pydantic model, and a dependency.

`main.py`:

```python
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
```

`models.py`:

```python
from pydantic import BaseModel


class User(BaseModel):
    name: str
    email: str


class UnusedModel(BaseModel):
    value: int
```

`dependencies.py`:

```python
from fastapi import Depends


def get_current_user(token: str = Depends(lambda: 'token')) -> str:
    return token


def unused_dependency() -> None:
    pass
```

`routes/users.py`:

```python
from fastapi import APIRouter, Depends

from dependencies import get_current_user
from models import User

router = APIRouter()


@router.get('/users/{user_id}', response_model=User)
def read_user(user_id: int, current_user: str = Depends(get_current_user)) -> User:
    return User(name=current_user)


@router.post('/users', response_model=User)
async def create_user(user: User) -> User:
    return user


def dead_route_helper() -> None:
    pass
```

Without configuration, every handler, the event callback, and the Pydantic fields are reported, together with the definitions
and imports they keep alive: `on_startup` is dead and is the only caller of `log_startup`, whose body is the only user of
`SETTING`; `read_me` is the only user of the `User` import; `read_user` is dead and its default argument is the only user of
`get_current_user` and both `Depends` imports:

```text
project/dependencies.py:1:20: DC07 Import `Depends` is never used
project/dependencies.py:4:0: DC02 Function `get_current_user` is never used
project/dependencies.py:8:0: DC02 Function `unused_dependency` is never used
project/main.py:3:19: DC07 Import `User` is never used
project/main.py:9:0: DC01 Variable `SETTING` is never used
project/main.py:12:0: DC02 Function `log_startup` is never used
project/main.py:24:0: DC02 Function `on_startup` is never used
project/main.py:29:0: DC02 Function `read_me` is never used
project/main.py:33:0: DC01 Variable `UNUSED_SETTING` is never used
project/main.py:36:0: DC02 Function `unused_handler` is never used
project/models.py:5:4: DC06 Name `name` is never used
project/models.py:6:4: DC06 Name `email` is never used
project/models.py:9:0: DC03 Class `UnusedModel` is never used
project/models.py:10:4: DC06 Name `value` is never used
project/routes/users.py:1:31: DC07 Import `Depends` is never used
project/routes/users.py:3:25: DC07 Import `get_current_user` is never used
project/routes/users.py:10:0: DC02 Function `read_user` is never used
project/routes/users.py:15:0: DC02 Function `create_user` is never used
project/routes/users.py:19:0: DC02 Function `dead_route_helper` is never used
```

With the recommended configuration, only the intentionally unused definitions remain:

```text
project/dependencies.py:8:0: DC02 Function `unused_dependency` is never used
project/main.py:33:0: DC01 Variable `UNUSED_SETTING` is never used
project/main.py:36:0: DC02 Function `unused_handler` is never used
project/models.py:9:0: DC03 Class `UnusedModel` is never used
project/routes/users.py:19:0: DC02 Function `dead_route_helper` is never used
```

No route handler, no event handler, and no Pydantic field appears in the second report. The five remaining findings are real: they are never
referenced by the application.

## Dependency injection

FastAPI dependency injection needs no suppression. deadcode reports a definition only when its name is never loaded anywhere in the analysed
source, and every FastAPI dependency declaration loads the provider name:

| Dependency form | Why it is safe |
|-----------------|----------------|
| `user: str = Depends(get_current_user)` | `get_current_user` is a name load |
| `user: Annotated[str, Depends(get_current_user)]` | Same name load inside `Annotated` |
| `CurrentUser = Annotated[str, Depends(get_current_user)]` type alias | The alias is used in signatures and the provider is loaded at the alias definition |
| `pagination: Pagination = Depends()` | The `Pagination` annotation is a name load |
| `pagination: Annotated[Pagination, Depends()]` | Same class-name load |
| `Depends(Pagination)` | The class name is a name load |
| `Security(oauth2_scheme, scopes=["admin"])` | The scheme and the scope name are name loads |
| `dependencies=[Depends(verify_token)]` on a path operation, router, or `FastAPI(...)` | The decorator arguments and constructor arguments are name loads |
| `app.dependency_overrides[get_database] = ...` | The provider name is a name load |
| `app.add_api_route("/x", handler, dependencies=[...])` | The handler and provider names are name loads |
| Sync and async generator dependencies using `yield` | The provider is loaded; names inside the body follow normal rules |
| `@lru_cache` provider functions | The decorated function is loaded when passed to `Depends` |
| Callable instances such as `Depends(request_id)` | The instance is a name load |

Function arguments are not treated as variables by deadcode, so injected parameter names are never reported as unused. The strategies are:

1. Do not add dependency providers to `ignore-names` or any other ignore option. Doing so would hide genuinely unused providers.
2. Keep registering dependencies through names, `Annotated`, or decorator arguments. All of those are visible to the parser.
3. Leave provider bodies analysable. Unlike decorator-name suppression, dependency injection does not need to skip a whole definition.

The separate suite in `tests/documented_examples/test_fastapi_dependency_injection.py` exercises function, async, generator, async generator, class, callable
instance, `Annotated`, type-alias, `Security`, router-level, application-level, path-operation-level, `add_api_route`, override, `use_cache`,
WebSocket, `Request`, `BackgroundTasks`, and HTTP security dependency forms. It asserts that the only reported name is the intentionally unused
provider.

## Verifying the recommended configuration

Copy the configuration into `pyproject.toml`, then run:

```shell
deadcode . --no-color
```

The command exits with status `1` while real dead code remains and `0` once the application has none. If a route handler is still reported, its
decorator does not match the configured patterns. Check the router or application variable name, add the matching `@<name>.*` pattern, and run
the command again.

## Limitations

- deadcode does not detect FastAPI automatically. Configuration is explicit and applies to any framework that uses decorators.
- Dynamic registration through `getattr`, `importlib`, string paths, or code generation is invisible to a static analyser.
- A dependency resolved only by a string, such as a plugin registry entry, must be referenced by name somewhere for deadcode to see it.
- Base-class overrides outside Pydantic models, such as `BaseHTTPMiddleware.dispatch`, are not resolved; ignore the overridden name explicitly
  when the framework calls it.
