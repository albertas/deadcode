from fastapi import APIRouter, BackgroundTasks, Body, Cookie, Depends, Header, HTTPException, Path, Query, status

from background import write_log
from models import Category, Item, ItemCreate
from security import get_current_user, require_admin

router = APIRouter(prefix='/items', tags=['items'], dependencies=[Depends(get_current_user)])
admin_router = APIRouter(prefix='/admin', tags=['admin'], dependencies=[Depends(require_admin)])

ITEMS: dict[int, Item] = {}
DEFAULT_CATEGORY = Category.MOVIES


@router.get('', response_model=list[Item])
async def list_items(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100),
    category: Category = DEFAULT_CATEGORY,
    x_request_id: str | None = Header(default=None),
    session: str | None = Cookie(default=None),
) -> list[Item]:
    del x_request_id, session
    items = [item for item in ITEMS.values() if item.category == category]
    return items[skip : skip + limit]


@router.get('/{item_id}', response_model=Item)
def read_item(item_id: int = Path(ge=1)) -> Item:
    try:
        return ITEMS[item_id]
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='not found') from error


@router.post('', response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, background_tasks: BackgroundTasks) -> Item:
    stored = Item(**item.model_dump())
    ITEMS[len(ITEMS) + 1] = stored
    background_tasks.add_task(write_log, f'created {stored.name}')
    return stored


@router.put('/{item_id}', response_model=Item)
def replace_item(item_id: int, item: Item = Body(...)) -> Item:  # noqa: B008
    ITEMS[item_id] = item
    return item


@router.patch('/{item_id}', response_model=Item)
def update_item(item_id: int, item: Item = Body(...)) -> Item:  # noqa: B008
    ITEMS[item_id] = item
    return item


@router.delete('/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int) -> None:
    ITEMS.pop(item_id, None)


@admin_router.get('/stats')
def item_stats() -> dict[str, int]:
    return {'count': len(ITEMS)}


def dead_route_helper() -> None:
    pass
