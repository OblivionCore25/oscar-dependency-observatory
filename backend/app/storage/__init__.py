"""
OSCAR Dependency Graph Observatory — Storage Module

Contains protocols and implementations for persisting domain models.
"""

from typing import Protocol, List, Optional
from app.models.domain import Package, Version, DependencyEdge


class StorageService(Protocol):
    """
    Interface for the persistence layer.
    """
    
    def save_package(self, package: Package) -> None:
        ...
        
    def save_versions(self, versions: List[Version]) -> None:
        ...

    def save_edges(self, edges: List[DependencyEdge]) -> None:
        ...

    def get_package(self, ecosystem: str, name: str) -> Optional[Package]:
        ...

    def get_versions(self, ecosystem: str, package_name: str) -> List[Version]:
        ...

    def get_edges_for_version(self, ecosystem: str, package_name: str, version: str) -> List[DependencyEdge]:
        ...

    def get_all_versions(self, ecosystem: str) -> List[Version]:
        ...

    def get_all_edges(self, ecosystem: str) -> List[DependencyEdge]:
        ...
