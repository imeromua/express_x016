from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Базовий клас репозиторію — зберігає сесію."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
