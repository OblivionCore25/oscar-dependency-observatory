"""
OSCAR Dependency Graph Observatory — PyPI Normalizer
"""

from typing import Dict, Any, List, Tuple, Optional
import re

from app.models.domain import Package, Version, DependencyEdge


class PypiNormalizer:
    ECOSYSTEM = "pypi"

    @classmethod
    def normalize_package(cls, raw_data: Dict[str, Any]) -> Package:
        """Extract identity package from PyPI response."""
        info = raw_data.get("info", {})
        name = info.get("name", "")
        return Package(
            ecosystem=cls.ECOSYSTEM,
            name=name
        )

    @classmethod
    def normalize_version(cls, raw_data: Dict[str, Any]) -> Version:
        """Extract strict Version identity."""
        info = raw_data.get("info", {})
        name = info.get("name", "")
        version = info.get("version", "")
        
        # PyPI releases dict contains timestamps, but we can fall back safely without it for this MVP
        return Version(
            package_name=name,
            ecosystem=cls.ECOSYSTEM,
            version=version
        )

    @classmethod
    def _parse_requirement(cls, req_string: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parses PEP 508 dependency strings.
        Example strings:
        - "httpx (>=0.22.0)"
        - "pydantic[email]"
        - "pytest ; extra == 'test'"
        Returns a tuple: (dependency_name, constraint_string) or (None, None) if skipped.
        """
        # Split environment markers logically via semicolon
        parts = req_string.split(";")
        req_part = parts[0].strip()
        marker_part = parts[1].strip() if len(parts) > 1 else ""
        
        # Skip ALL optional extras — any requirement gated on `extra ==` is an
        # optional install group (e.g. test, dev, ml, cuda, security …).
        # Including them would pull GPU / ML packages into a runtime graph.
        if "extra ==" in marker_part or 'extra ==' in marker_part:
            return None, None
            
        # Regex extracts name, brackets (optional), and constraints reliably 
        # Match groups: 1 = name, 2 = constraint if in parens, 3 = constraint if not in parens
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:\[.*?\])?\s*(?:\((.*?)\)|(.*?))?$", req_part)
        if not match:
            return None, None
            
        name = match.group(1).strip()
        constraint1 = match.group(2)
        constraint2 = match.group(3)
        
        constraint = ""
        if constraint1:
            constraint = constraint1.strip()
        elif constraint2:
            constraint = constraint2.strip()
            
        return name, constraint

    @classmethod
    def normalize_edges(cls, raw_data: Dict[str, Any]) -> List[DependencyEdge]:
        """Extract direct edges recursively from requires_dist payload."""
        info = raw_data.get("info", {})
        source_name = info.get("name", "")
        source_version = info.get("version", "")
        
        requires_dist = info.get("requires_dist")
        if not requires_dist:
            return []
            
        edges = []
        for req in requires_dist:
            target_name, constraint = cls._parse_requirement(req)
            if not target_name:
                continue
                
            edges.append(DependencyEdge(
                source_package=source_name,
                source_version=source_version,
                target_package=target_name,
                version_constraint=constraint,
                ecosystem=cls.ECOSYSTEM
            ))
        return edges

    @classmethod
    def normalize_package_data(cls, raw_data: Dict[str, Any]) -> Tuple[Package, List[Version], List[DependencyEdge]]:
        """
        Combines package, a single release version, and edges into the standard tuple output suitable for storage.
        """
        package = cls.normalize_package(raw_data)
        version = cls.normalize_version(raw_data)
        edges = cls.normalize_edges(raw_data)
        return package, [version], edges
