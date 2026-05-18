from cryptography.fernet import Fernet, InvalidToken
from app.config import settings
import structlog

logger = structlog.get_logger()

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if not key:
            if settings.is_production:
                raise RuntimeError(
                    "ENCRYPTION_KEY environment variable is required in production. "
                    "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
            # Development-only fallback — ephemeral key, data cannot be recovered after restart
            logger.warning(
                "ENCRYPTION_KEY not set — using ephemeral key. "
                "Encrypted API keys will be lost on restart. Set ENCRYPTION_KEY in .env to fix this."
            )
            key = Fernet.generate_key().decode()
        try:
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise RuntimeError(
                f"Invalid ENCRYPTION_KEY format: {e}. "
                "Generate a valid key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ) from e
    return _fernet


def encrypt_key(plaintext: str) -> str:
    """Encrypt an API key string and return base64-encoded ciphertext."""
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """Decrypt an encrypted API key string."""
    fernet = _get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt API key — key may have been rotated")
        raise ValueError("Unable to decrypt stored API key. The encryption key may have changed.")
