import asyncio
from app.storage.postgres import PostgresStorage
from app.graph.analytics import AnalyticsService

async def main():
    storage = PostgresStorage()
    await storage.connect()
    # Or SQLite if fallback... wait, factory uses ENV.
    
    from app.storage.factory import get_storage
    storage = get_storage()
    if hasattr(storage, 'connect'): 
        await storage.connect()

    analytics = AnalyticsService(storage)
    
    print("Testing apache-airflow@2.9.0")
    res = analytics.get_libyears_breakdown("pypi", "apache-airflow", "2.9.0")
    print(f"Items returned: {len(res)}")
    if len(res) < 10:
        print(res)
        
    print()
    all_edges = storage.get_all_edges("pypi")
    print(f"Total pypi edges: {len(all_edges)}")
    all_versions = storage.get_all_versions("pypi")
    print(f"Total pypi versions: {len(all_versions)}")
    
if __name__ == '__main__':
    asyncio.run(main())
