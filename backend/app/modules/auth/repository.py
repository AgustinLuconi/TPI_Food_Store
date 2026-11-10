from datetime import datetime

from sqlalchemy import update
from sqlmodel import select

from app.core.db_types import utcnow
from app.core.repository import BaseRepository
from app.modules.auth.models import RefreshToken


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()

    def issue(self, usuario_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        return self.create(RefreshToken(usuario_id=usuario_id, token_hash=token_hash, expires_at=expires_at))

    def revoke(self, token: RefreshToken) -> None:
        if token.revoked_at is None:
            self.update(token, {"revoked_at": utcnow()})

    def revoke_all_for_user(self, usuario_id: int) -> None:
        self.session.exec(  # type: ignore[call-overload]
            update(RefreshToken)
            .where(RefreshToken.usuario_id == usuario_id, RefreshToken.revoked_at.is_(None))  # type: ignore[attr-defined]
            .values(revoked_at=utcnow())
        )
        self.session.flush()
