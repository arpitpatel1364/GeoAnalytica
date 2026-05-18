from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Called at startup — ensures PostGIS extension exists and seeds master user."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    # Seed master user if configured
    if settings.MASTER_USER_EMAIL:
        from app.models.user import User
        from app.services.auth_service import hash_password
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            try:
                email = settings.MASTER_USER_EMAIL.lower()
                result = await session.execute(select(User).where(User.email == email))
                master_user = result.scalar_one_or_none()

                if not master_user:
                    master_user = User(
                        email=email,
                        full_name="Master Administrator",
                        hashed_password=hash_password(settings.MASTER_USER_PASSWORD),
                        is_active=True,
                        is_verified=True,
                        is_admin=True,
                        tier="pro",
                    )
                    session.add(master_user)
                    await session.commit()
            except Exception as e:
                await session.rollback()
                import structlog
                logger = structlog.get_logger()
                logger.error("failed_to_seed_master_user", error=str(e))
