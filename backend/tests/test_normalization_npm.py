import pytest
from datetime import datetime, timezone
from app.normalization.npm_normalizer import NpmNormalizer
from app.models.domain import Package, Version, DependencyEdge

def test_normalize_valid_package():
    """Test normalizing a well-formed npm registry response."""
    raw_data = {
        "name": "react",
        "description": "React library",
        "time": {
            "18.2.0": "2022-06-14T18:00:00Z",
            "18.2.1": "2022-06-15T10:00:00Z"
        },
        "versions": {
            "18.2.0": {
                "name": "react",
                "version": "18.2.0",
                "dependencies": {
                    "loose-envify": "^1.1.0"
                }
            },
            "18.2.1": {
                "name": "react",
                "version": "18.2.1",
                "dependencies": {
                    "loose-envify": "^1.1.0",
                    "object-assign": "^4.1.1"
                }
            }
        }
    }

    package, versions, edges = NpmNormalizer.normalize_package_data(raw_data)

    # Validate Package
    assert isinstance(package, Package)
    assert package.ecosystem == "npm"
    assert package.name == "react"
    assert package.package_id == "npm:react"

    # Validate Versions
    assert len(versions) == 2
    for v in versions:
        assert isinstance(v, Version)
        assert v.package_name == "react"
        assert v.ecosystem == "npm"
        if v.version == "18.2.0":
            assert v.published_at.year == 2022
            assert v.published_at.month == 6

    # Validate Edges
    assert len(edges) == 3
    for e in edges:
        assert isinstance(e, DependencyEdge)
        assert e.source_package == "react"
        assert e.ecosystem == "npm"
        assert e.dependency_type == "runtime"

    # Find specific edges to verify constraints
    loose_envify_edge = next(e for e in edges if e.source_version == "18.2.0" and e.target_package == "loose-envify")
    assert loose_envify_edge.version_constraint == "^1.1.0"


def test_normalize_missing_name():
    """Test parsing fails when no name is provided."""
    raw_data = {"versions": {}}
    with pytest.raises(ValueError, match="missing 'name'"):
        NpmNormalizer.normalize_package_data(raw_data)


def test_normalize_package_no_dependencies():
    """Test normalizing a package with no dependencies in its versions."""
    raw_data = {
        "name": "is-even",
        "versions": {
            "1.0.0": {
                "name": "is-even",
                "version": "1.0.0"
                # dependencies explicitly missing
            }
        }
    }

    package, versions, edges = NpmNormalizer.normalize_package_data(raw_data)
    
    assert package.name == "is-even"
    assert len(versions) == 1
    assert versions[0].version == "1.0.0"
    assert len(edges) == 0


def test_normalize_empty_versions():
    """Test normalizing a package that has no versions yet (e.g., unpublished or placeholder)."""
    raw_data = {
        "name": "empty-pkg",
        "versions": {}
    }

    package, versions, edges = NpmNormalizer.normalize_package_data(raw_data)
    
    assert package.name == "empty-pkg"
    assert len(versions) == 0
    assert len(edges) == 0
