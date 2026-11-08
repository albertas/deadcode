from fastapi import Depends


def get_current_user(token: str = Depends(lambda: 'token')) -> str:
    return token


def unused_dependency() -> None:
    pass
