import asyncio
from app.storage.factory import get_storage
from app.graph.analytics import AnalyticsService
import networkx as nx

async def main():
    storage = get_storage()
    analytics = AnalyticsService(storage)
    G = analytics._build_nx_graph("npm")
    print(f"Graph has {len(G.nodes)} nodes and {len(G.edges)} edges.")
    try:
        eigen = nx.eigenvector_centrality_numpy(G)
        print("Eigenvector calculation succeeded.")
        # Print a few nonzero values
        nonzero = {k: v for k, v in eigen.items() if v > 0.0001}
        print(f"Found {len(nonzero)} nodes with eigenvector > 0.0001")
        for k in list(nonzero.keys())[:5]:
            print(f"{k}: {nonzero[k]:.6f}")
    except Exception as e:
        print(f"Exception: {e}")

asyncio.run(main())
