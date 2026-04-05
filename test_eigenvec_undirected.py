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
        udG = G.to_undirected()
        largest_cc = max(nx.connected_components(udG), key=len)
        print(f"Largest connected component has {len(largest_cc)} nodes.")
        subG = udG.subgraph(largest_cc)
        eigenvectors = nx.eigenvector_centrality_numpy(subG)
        print("Eigenvector calculation succeeded.")
        nonzero = {k: v for k, v in eigenvectors.items() if v > 0.0001}
        print(f"Found {len(nonzero)} nodes with nonzero eigenvector")
        print(f"jest-util directly: {eigenvectors.get('jest-util', 0.0):.6f}")
        print(f"babel-core directly: {eigenvectors.get('babel-core', 0.0):.6f}")
    except Exception as e:
        print(f"Exception: {e}")

asyncio.run(main())
