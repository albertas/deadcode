from collections.abc import AsyncGenerator, Generator
from functools import lru_cache


class Settings:
    app_name: str = 'example'


@lru_cache
def get_settings() -> Settings:
    return Settings()


class Pagination:
    def __init__(self, skip: int = 0, limit: int = 10) -> None:
        self.skip = skip
        self.limit = limit


class RequestId:
    def __call__(self) -> str:
        return 'request-id'


request_id = RequestId()


def get_database() -> Generator[object, None, None]:
    database = object()
    try:
        yield database
    finally:
        pass


async def get_client() -> AsyncGenerator[object, None]:
    yield object()


def get_optional_user(token: str | None = None) -> str | None:
    return token


def get_current_user(token: str = 'token') -> str:  # noqa: S107
    return token


def unused_dependency() -> None:
    pass
