"""
JSON-based implementation of the StorageService.
"""

import json
import os
from pathlib import Path
from typing import List, Optional

from app.models.domain import Package, Version, DependencyEdge
from app.storage import StorageService


class JSONStorage(StorageService):
    """
    A simple file-based storage engine using JSON files.
    Data is stored in `base_dir` with the following physical structure:
        {base_dir}/{ecosystem}/packages/{name}.json
        {base_dir}/{ecosystem}/versions/{name}.json
        {base_dir}/{ecosystem}/edges/{name}_{version}.json
    """

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        # We don't create directories right away, we create them lazily upon save.

    def _get_path(self, ecosystem: str, entity_type: str, filename: str) -> Path:
        """Helper to compute the nested storage path."""
        # Sanitize filename to avoid weird bugs if packages have slashes
        # npm scoped packages (@scope/name) will be mapped to a safe name
        safe_filename = filename.replace("/", "_").replace("@", "") + ".json"
        
        path = self.base_dir / ecosystem / entity_type / safe_filename
        return path

    def _ensure_dir(self, file_path: Path):
        """Helper to create parent directories."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_package(self, package: Package) -> None:
        path = self._get_path(package.ecosystem, "packages", package.name)
        self._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(package.model_dump_json(indent=2))

    def save_versions(self, versions: List[Version]) -> None:
        if not versions:
            return
            
        ecosystem = versions[0].ecosystem
        package_name = versions[0].package_name
        
        path = self._get_path(ecosystem, "versions", package_name)
        self._ensure_dir(path)
        
        # Load existing if any, to merge or overwrite
        existing = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    existing = [Version.model_validate(v) for v in data]
                except (json.JSONDecodeError, ValueError):
                    pass
                    
        # Merge logic: just overwrite if duplicate version exists
        version_map = {v.version: v for v in existing}
        for v in versions:
            version_map[v.version] = v
            
        final_list = [v.model_dump() for v in version_map.values()]
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(final_list, f, indent=2, default=str)

    def save_edges(self, edges: List[DependencyEdge]) -> None:
        if not edges:
            return
            
        # Group edges by (source_package, source_version)
        grouped = {}
        for edge in edges:
            key = (edge.ecosystem, edge.source_package, edge.source_version)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(edge)
            
        for (ecosystem, pkg_name, version), edge_list in grouped.items():
            filename = f"{pkg_name}_{version}"
            path = self._get_path(ecosystem, "edges", filename)
            self._ensure_dir(path)
            
            # For MVP, we completely overwrite the file per ingestion
            # assuming ingestion fetches full dependencies for a version.
            data = [e.model_dump() for e in edge_list]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

    def get_package(self, ecosystem: str, name: str) -> Optional[Package]:
        path = self._get_path(ecosystem, "packages", name)
        if not path.exists():
            return None
            
        with open(path, "r", encoding="utf-8") as f:
            return Package.model_validate_json(f.read())

    def get_versions(self, ecosystem: str, package_name: str) -> List[Version]:
        path = self._get_path(ecosystem, "versions", package_name)
        if not path.exists():
            return []
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Version.model_validate(v) for v in data]

    def get_edges_for_version(self, ecosystem: str, package_name: str, version: str) -> List[DependencyEdge]:
        filename = f"{package_name}_{version}"
        path = self._get_path(ecosystem, "edges", filename)
        if not path.exists():
            return []
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [DependencyEdge.model_validate(e) for e in data]

    def get_all_versions(self, ecosystem: str) -> List[Version]:
        dir_path = self.base_dir / ecosystem / "versions"
        if not dir_path.exists():
            return []
            
        all_versions = []
        for file_path in dir_path.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    all_versions.extend([Version.model_validate(v) for v in data])
                except (json.JSONDecodeError, ValueError):
                    pass
        return all_versions

    def get_all_edges(self, ecosystem: str) -> List[DependencyEdge]:
        dir_path = self.base_dir / ecosystem / "edges"
        if not dir_path.exists():
            return []
            
        all_edges = []
        for file_path in dir_path.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    all_edges.extend([DependencyEdge.model_validate(e) for e in data])
                except (json.JSONDecodeError, ValueError):
                    pass
        return all_edges
