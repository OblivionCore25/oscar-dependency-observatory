import asyncio
from app.storage.factory import get_storage
from app.graph.analytics import AnalyticsService

async def main():
    storage = get_storage()
    if hasattr(storage, 'connect'): 
        await storage.connect()
    analytics = AnalyticsService(storage)
    
    # Check top level
    m = await analytics.get_package_metrics("npm", "@babel/core", "8.0.0-rc.3")
    print(f"Total Libyears Debt: {m.libyears}")
    
    # Check breakdown
    br = analytics.get_libyears_breakdown("npm", "@babel/core", "8.0.0-rc.3")
    print(f"Breakdown items: {len(br)}")
    for k, v in list(br.items())[:5]:
        print(f"  {k}: {v}")
        
    sum_br = sum(br.values())
    print(f"Sum of breakdown: {sum_br}")
    
if __name__ == '__main__':
    asyncio.run(main())
