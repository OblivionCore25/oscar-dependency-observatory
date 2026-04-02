"""
OSCAR Dependency Graph Observatory — npm Normalizer

Transforms raw JSON responses from the npm registry into standardized
domain models defined in `app.models.domain`.
"""

from typing import Dict, Any, Tuple, List
from datetime import datetime

from app.models.domain import Package, Version, DependencyEdge

class NpmNormalizer:
    """
    Normalizes raw npm registry responses into internal domain models.
    """

    ECOSYSTEM = "npm"

    @classmethod
    def normalize_package_data(cls, raw_data: Dict[str, Any]) -> Tuple[Package, List[Version], List[DependencyEdge]]:
        """
        Takes a full standard response from registry.npmjs.org and converts it
        to our internal Domain objects.
        
        Args:
            raw_data: The JSON dictionary from the registry.
            
        Returns:
            A tuple containing:
            - The Package model
            - A list of Version models
            - A list of DependencyEdge models
        """
        name = raw_data.get("name")
        if not name:
            raise ValueError("Invalid npm data: missing 'name' field")

        package = Package(ecosystem=cls.ECOSYSTEM, name=name)
        
        versions_list: List[Version] = []
        edges_list: List[DependencyEdge] = []
        
        raw_versions = raw_data.get("versions", {})
        raw_time = raw_data.get("time", {})
        
        for version_str, version_info in raw_versions.items():
            # Parse publication time if available
            pub_time_str = raw_time.get(version_str)
            published_at = None
            if pub_time_str:
                try:
                    # fromisoformat handles basic ISO 8601 strings, including 'Z' in Python 3.11+
                    published_at = datetime.fromisoformat(pub_time_str.replace('Z', '+00:00'))
                except Exception:
                    pass

            version_model = Version(
                package_name=name,
                ecosystem=cls.ECOSYSTEM,
                version=version_str,
                published_at=published_at
            )
            versions_list.append(version_model)
            
            # Extract dependencies
            deps = version_info.get("dependencies", {})
            for target_name, constraint in deps.items():
                # Some packages might have weird constraints, ensure it's a string
                constraint_str = str(constraint) if constraint is not None else "*"
                edge = DependencyEdge(
                    source_package=name,
                    source_version=version_str,
                    target_package=target_name,
                    version_constraint=constraint_str,
                    dependency_type="runtime",
                    ecosystem=cls.ECOSYSTEM
                )
                edges_list.append(edge)
                
        return package, versions_list, edges_list
