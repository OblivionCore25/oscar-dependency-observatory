from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class PackageModel(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ecosystem = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint('ecosystem', 'name', name='uq_package_ecosystem_name'),
    )

class VersionModel(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ecosystem = Column(String, nullable=False, index=True)
    package_name = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('ecosystem', 'package_name', 'version', name='uq_version_eco_pkg_ver'),
    )

class DependencyEdgeModel(Base):
    __tablename__ = "dependency_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ecosystem = Column(String, nullable=False, index=True)
    source_package = Column(String, nullable=False, index=True)
    source_version = Column(String, nullable=False, index=True)
    target_package = Column(String, nullable=False, index=True)
    version_constraint = Column(String, nullable=False)
    resolved_target_version = Column(String, nullable=True)
    dependency_type = Column(String, nullable=True)
    ingestion_timestamp = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'ecosystem', 'source_package', 'source_version', 'target_package', 'dependency_type',
            name='uq_edge_eco_src_ver_tgt_type'
        ),
    )
