from app.storage.pg_storage import PgStorage
from app.config.settings import settings
import networkx as nx

db = PgStorage(settings.database_url)
ecosystem = "npm"
root = "request@2.88.2"

all_edges = db.get_all_edges(ecosystem)
all_versions = db.get_all_versions(ecosystem)

from collections import defaultdict
versions_by_pkg = defaultdict(list)
for v in all_versions:
    versions_by_pkg[v.package_name].append(v)

latest_date_by_pkg = {}
latest_version_by_pkg = {}
for pkg, vlist in versions_by_pkg.items():
    valid_versions = [v for v in vlist if v.published_at]
    if valid_versions:
        latest_v = max(valid_versions, key=lambda x: x.published_at)
        latest_date_by_pkg[pkg] = latest_v.published_at
        latest_version_by_pkg[pkg] = latest_v.version

date_by_vid = {f"{v.package_name}@{v.version}": v.published_at for v in all_versions if v.published_at}

import re
VG = nx.DiGraph()
for edge in all_edges:
    t_ver = edge.resolved_target_version
    if not t_ver and edge.version_constraint:
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", edge.version_constraint)
        if match:
            t_ver = match.group(1)
            
    if not t_ver:
        t_ver = latest_version_by_pkg.get(edge.target_package, "unknown")
        
    VG.add_edge(f"{edge.source_package}@{edge.source_version}", f"{edge.target_package}@{t_ver}")

descendants_v = nx.descendants(VG, root)

libyears = 0.0
for tgt_id in descendants_v:
    if "@" not in tgt_id: continue
    pkg_only, ver_only = tgt_id.split("@", 1)
    
    latest_date = latest_date_by_pkg.get(pkg_only)
    used_date = date_by_vid.get(tgt_id)
    
    if not used_date and pkg_only in versions_by_pkg:
        for v in versions_by_pkg[pkg_only]:
            if v.version.startswith(ver_only) and v.published_at:
                used_date = v.published_at
                break
                
    print(f"{tgt_id} -> used: {used_date}, latest: {latest_date}")
    
    if used_date and latest_date and latest_date > used_date:
        delta = (latest_date - used_date).days / 365.25
        libyears += delta

print(f"Total Libyears: {libyears}")
