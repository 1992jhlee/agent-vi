import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Bearer JWT를 검증하고 Google sub claim을 반환합니다.

    프론트엔드의 /api/auth/token (Next.js server route)에서 AUTH_SECRET으로
    서명한 HS256 JWT를 기대합니다. payload는 { sub: "<google_user_id>" } 형태입니다.
    """
    if not settings.auth_secret:
        raise HTTPException(status_code=500, detail="AUTH_SECRET 환경변수가 설정되지 않았습니다.")

    if not credentials:
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.auth_secret,
            algorithms=["HS256"],
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
