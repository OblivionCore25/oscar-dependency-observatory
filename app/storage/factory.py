from app.config.settings import settings
from app.storage import StorageService
from app.storage.json_storage import JSONStorage
from app.storage.pg_storage import PgStorage

def get_storage() -> StorageService:
    """Factory function to get the appropriate storage service based on configuration."""
    if settings.storage_mode == "postgres":
        return PgStorage(database_url=settings.database_url)
    # Default to file/json storage
    return JSONStorage(base_dir=settings.data_directory)
