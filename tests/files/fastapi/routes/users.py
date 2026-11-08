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
