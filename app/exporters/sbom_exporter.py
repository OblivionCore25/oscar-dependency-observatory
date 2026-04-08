"""
OSCAR Dependency Graph Observatory — SBOM Export Service

Exports the transitive dependency graph as a standard Software Bill of Materials (SBOM)
in CycloneDX or SPDX format using lib4sbom.
"""

from typing import Dict, Any, List
import uuid
import datetime
import json
from packageurl import PackageURL

from lib4sbom.sbom import SBOM
from lib4sbom.data.document import SBOMDocument
from lib4sbom.data.package import SBOMPackage
from lib4sbom.data.relationship import SBOMRelationship
from lib4sbom.data.vulnerability import Vulnerability
from lib4sbom.generator import SBOMGenerator

from app.models.api import TransitiveDependenciesResponse, PackageMetrics


class SBOMExporter:
    """
    Handles extracting the resolved dependency graph to standards-compliant
    SBOM documents (CycloneDX and SPDX).
    """

    def _build_sbom_model(self, ecosystem: str, package_name: str, version: str,
                          graph_data: TransitiveDependenciesResponse,
                          vulnerabilities: dict = None) -> SBOM:
        """
        Builds the abstract lib4sbom model from OSCAR graph data.
        """
        sbom = SBOM()
        sbom.set_type("application")
        
        # 1. Document metadata
        sbom_doc = SBOMDocument()
        sbom_doc.set_name(f"{package_name}-sbom")
        sbom_doc.set_version(version)
        sbom_doc.set_metadata_type("application")
        
        # Tool info
        sbom_doc.set_creator("tool", "OSCAR")
        sbom_doc.set_created(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
        sbom.add_document(sbom_doc.get_document())
        
        vulnerabilities = vulnerabilities or {}

        # 2. Add Packages (Nodes)
        packages_dict = {}
        
        # Root package
        root_purl = PackageURL(type=ecosystem, name=package_name, version=version).to_string()
        root_pkg = SBOMPackage()
        root_pkg.set_name(package_name)
        root_pkg.set_version(version)
        root_pkg.set_type("application")
        root_pkg.set_purl(root_purl)
        packages_dict[package_name] = root_pkg.get_package()
        
        # Graph nodes
        for node in graph_data.nodes:
            # Skip the root node if it's already added to prevent duplication
            if node.package == package_name and node.version == version:
                continue
                
            pkg = SBOMPackage()
            pkg.set_name(node.package)
            pkg.set_version(node.version)
            pkg.set_type("library")
            
            purl = PackageURL(type=node.ecosystem, name=node.package, version=node.version).to_string()
            pkg.set_purl(purl)
            
            pkg_key = f"{node.package}@{node.version}"
            packages_dict[pkg_key] = pkg.get_package()
            
        if packages_dict:
            sbom.add_packages(packages_dict)
            
        # 3. Add Relationships (Edges)
        added_relations = set()
        relationships_list = []
        
        for edge in graph_data.edges:
            # Parse src/target formats like "npm:express@5.1.0"
            src_parts = edge.source.split(":")
            tgt_parts = edge.target.split(":")
            
            if len(src_parts) == 2 and len(tgt_parts) == 2:
                src_pkg_ver = src_parts[1].split("@")
                tgt_pkg_ver = tgt_parts[1].split("@")
                
                src_name = src_pkg_ver[0]
                tgt_name = tgt_pkg_ver[0]
                
                # Deduplicate relationships
                rel_key = f"{src_name}->{tgt_name}"
                if rel_key not in added_relations:
                    rel = SBOMRelationship()
                    rel.set_relationship(src_name, "DEPENDS_ON", tgt_name)
                    relationships_list.append(rel.get_relationship())
                    added_relations.add(rel_key)

        if relationships_list:
            sbom.add_relationships(relationships_list)

        # 4. Add Vulnerabilities
        if vulnerabilities:
            vulns_list = []
            for pkg_ver, vulns in vulnerabilities.get("breakdown", {}).items():
                if not vulns:
                    continue
                    
                pkg_name = pkg_ver.split("@")[0] if "@" in pkg_ver else pkg_ver
                
                # Ensure the vulnerable package exists in the SBOM
                target_purl = None
                for node in graph_data.nodes:
                    if node.id == f"{ecosystem}:{pkg_ver}":
                        target_purl = PackageURL(type=ecosystem, name=node.package, version=node.version).to_string()
                        break
                
                if not target_purl:
                    target_purl = PackageURL(type=ecosystem, name=pkg_name, version="unknown").to_string()
                
                for v in vulns:
                    vuln = Vulnerability()
                    vuln_id = v.get("id")
                    vuln.set_id(vuln_id)
                    vuln.set_name(vuln_id)
                    vuln.set_description(v.get("summary", ""))
                    
                    # Map OSCAR severity back to standard
                    sev = v.get("severity", "UNKNOWN")
                    # lib4sbom exposes set_value for arbitrary vulnerability fields
                    if sev != "UNKNOWN":
                        vuln.set_value("severity", sev)
                        
                    # Link vulnerability to the specific package using its PURL or name
                    vuln.set_value("bom-ref", target_purl)
                    vulns_list.append(vuln.get_vulnerability())

            if vulns_list:
                sbom.add_vulnerabilities(vulns_list)

        return sbom

    def export_cyclonedx(self, ecosystem: str, package_name: str, version: str,
                         graph_data: TransitiveDependenciesResponse,
                         vulnerabilities: dict = None) -> dict:
        """
        Exports the graph to CycloneDX JSON format.
        """
        sbom_model = self._build_sbom_model(ecosystem, package_name, version, graph_data, vulnerabilities)
        gen = SBOMGenerator(sbom_type="cyclonedx", format="json")
        gen.generate(package_name, sbom_model.get_sbom(), "cyclonedx.json")
        
        with open("cyclonedx.json", "r") as f:
            data = json.load(f)
            
        return data

    def export_spdx(self, ecosystem: str, package_name: str, version: str,
                    graph_data: TransitiveDependenciesResponse,
                    vulnerabilities: dict = None) -> dict:
        """
        Exports the graph to SPDX JSON format.
        """
        sbom_model = self._build_sbom_model(ecosystem, package_name, version, graph_data, vulnerabilities)
        gen = SBOMGenerator(sbom_type="spdx", format="json")
        gen.generate(package_name, sbom_model.get_sbom(), "spdx.json")
        
        with open("spdx.json", "r") as f:
            data = json.load(f)
            
        return data

