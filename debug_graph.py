from app.storage.pg_storage import PgStorage
from app.config.settings import settings
import networkx as nx

db = PgStorage(settings.database_url)
ecosystem = "npm"
root = "request@2.88.2"

all_edges = db.get_all_edges(ecosystem)
print(f"Total edges: {len(all_edges)}")

VG = nx.DiGraph()
target_versions = set()
source_versions = set()

# Setup dates and versions for libyears
all_versions = db.get_all_versions(ecosystem)
from collections import defaultdict
versions_by_pkg = defaultdict(list)
for v in all_versions:
    versions_by_pkg[v.package_name].append(v)

latest_version_by_pkg = {}
for pkg, vlist in versions_by_pkg.items():
    valid_versions = [v for v in vlist if v.published_at]
    if valid_versions:
        latest_v = max(valid_versions, key=lambda x: x.published_at)
        latest_version_by_pkg[pkg] = latest_v.version
    elif vlist:
        latest_version_by_pkg[pkg] = vlist[-1].version

for edge in all_edges:
    if edge.source_package == "request":
        print(f"request edge: -> {edge.target_package} @ {edge.resolved_target_version}")
    t_ver = edge.resolved_target_version
    if not t_ver:
        t_ver = latest_version_by_pkg.get(edge.target_package, "unknown")
    src = f"{edge.source_package}@{edge.source_version}"
    tgt = f"{edge.target_package}@{t_ver}"
    VG.add_edge(src, tgt)
    
if VG.has_node(root):
    descendants = nx.descendants(VG, root)
    print(f"Root: {root}, Descendants: {len(descendants)}")
    
    sub_VG = VG.subgraph(descendants | {root})
    print(f"Transitive Depth: {nx.dag_longest_path_length(sub_VG)}")
    
    paths = nx.single_source_shortest_path(VG, root)
    for target in list(descendants)[:5]:
        print(f"Path to {target}: {paths[target]}")
else:
    print(f"Node {root} not in graph!")

