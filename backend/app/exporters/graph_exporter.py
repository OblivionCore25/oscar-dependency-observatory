"""
OSCAR Dependency Graph Observatory — Export Service

Extracts entire ecosystem datasets into JSON and CSV payloads.
"""

from typing import Dict, Any
import io
import csv

from app.storage import StorageService

class ExportService:
    """
    Handles extracting the graph dataset to global export formats.
    """
    def __init__(self, storage: StorageService):
        self.storage = storage

    def export_graph_json(self, ecosystem: str) -> Dict[str, Any]:
        """
        Exports the entire known graph for a given ecosystem as JSON.
        Returns a dictionary representing Nodes and Edges.
        """
        all_versions = self.storage.get_all_versions(ecosystem)
        all_edges = self.storage.get_all_edges(ecosystem)
        
        nodes = []
        for v in all_versions:
            nodes.append({
                "id": f"{ecosystem}:{v.package_name}@{v.version}",
                "ecosystem": ecosystem,
                "package": v.package_name,
                "version": v.version
            })
            
        edges = []
        for e in all_edges:
            edges.append({
                "source": f"{ecosystem}:{e.source_package}@{e.source_version}",
                "target": f"{ecosystem}:{e.target_package}",
                "constraint": e.version_constraint
            })
            
        return {
            "ecosystem": ecosystem,
            "nodes": nodes,
            "edges": edges
        }

    def export_graph_csv(self, ecosystem: str) -> str:
        """
        Exports the entire edge list as a CSV string format.
        Useful for downstream tools like Gephi or Pandas.
        """
        all_edges = self.storage.get_all_edges(ecosystem)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["source", "target", "constraint", "ecosystem"])
        
        for e in all_edges:
            source_id = f"{ecosystem}:{e.source_package}@{e.source_version}"
            target_id = f"{ecosystem}:{e.target_package}"
            writer.writerow([source_id, target_id, e.version_constraint, ecosystem])
            
        return output.getvalue()
