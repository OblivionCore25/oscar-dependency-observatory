from sqlalchemy import Column, String, DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class PackageModel(Base):
    __tablename__ = "packages"
    
    ecosystem = Column(String, primary_key=True)
    name = Column(String, primary_key=True)


class VersionModel(Base):
    __tablename__ = "versions"
    
    ecosystem = Column(String, primary_key=True)
    package_name = Column(String, primary_key=True)
    version = Column(String, primary_key=True)
    published_at = Column(DateTime, nullable=True)


class DependencyEdgeModel(Base):
    __tablename__ = "dependency_edges"
    
    ecosystem = Column(String, primary_key=True)
    source_package = Column(String, primary_key=True)
    source_version = Column(String, primary_key=True)
    target_package = Column(String, primary_key=True)
    dependency_type = Column(String, primary_key=True)
    
    version_constraint = Column(String, nullable=False)
    resolved_target_version = Column(String, nullable=True)
    ingestion_timestamp = Column(DateTime, nullable=False)
