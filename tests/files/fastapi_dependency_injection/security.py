from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBasic, OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
basic_scheme = HTTPBasic()
api_key_scheme = APIKeyHeader(name='x-api-key')

ADMIN_SCOPE = 'admin'


def verify_api_key(api_key: str = Security(api_key_scheme)) -> str:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return api_key


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    return token


def get_basic_user(credentials=Security(basic_scheme)) -> str:  # noqa: B008
    return credentials.username


def require_admin(user: str = Security(get_current_user, scopes=[ADMIN_SCOPE])) -> str:
    return user
