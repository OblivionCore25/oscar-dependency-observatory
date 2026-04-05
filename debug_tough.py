from app.storage.pg_storage import PgStorage
from app.config.settings import settings
import sys

print("Started db connection", file=sys.stderr)
db = PgStorage(settings.database_url)

versions = db.get_versions("npm", "tough-cookie")
print(f"Versions of tough-cookie: {len(versions)}")

all_v = db.get_all_versions("npm")
packages_in_db = set([v.package_name for v in all_v])
print(f"Total packages in DB: {len(packages_in_db)}")
