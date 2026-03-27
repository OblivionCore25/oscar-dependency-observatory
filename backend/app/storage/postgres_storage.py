import logging
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models.domain import Package, Version, DependencyEdge
from app.storage import StorageService
from app.storage.postgres_models import Base, PackageModel, VersionModel, DependencyEdgeModel

logger = logging.getLogger(__name__)

class PostgresStorage(StorageService):
    """
    PostgreSQL-based implementation of the StorageService.
    """

    def __init__(self, database_url: str):
        # Allow standard postgres:// URLs to be used with psycopg2
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Ensure tables exist (MVP approach; Alembic is better for production)
        Base.metadata.create_all(bind=self.engine)

    def save_package(self, package: Package) -> None:
        with self.SessionLocal() as session:
            existing = session.query(PackageModel).filter_by(
                ecosystem=package.ecosystem,
                name=package.name
            ).first()

            if not existing:
                db_package = PackageModel(
                    ecosystem=package.ecosystem,
                    name=package.name
                )
                session.add(db_package)
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()

    def save_versions(self, versions: List[Version]) -> None:
        if not versions:
            return

        with self.SessionLocal() as session:
            for v in versions:
                existing = session.query(VersionModel).filter_by(
                    ecosystem=v.ecosystem,
                    package_name=v.package_name,
                    version=v.version
                ).first()

                if existing:
                    existing.published_at = v.published_at
                else:
                    db_version = VersionModel(
                        ecosystem=v.ecosystem,
                        package_name=v.package_name,
                        version=v.version,
                        published_at=v.published_at
                    )
                    session.add(db_version)

            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                logger.error(f"IntegrityError saving versions for {versions[0].package_name}")

    def save_edges(self, edges: List[DependencyEdge]) -> None:
        if not edges:
            return

        with self.SessionLocal() as session:
            for edge in edges:
                existing = session.query(DependencyEdgeModel).filter_by(
                    ecosystem=edge.ecosystem,
                    source_package=edge.source_package,
                    source_version=edge.source_version,
                    target_package=edge.target_package,
                    dependency_type=edge.dependency_type
                ).first()

                if existing:
                    existing.version_constraint = edge.version_constraint
                    existing.resolved_target_version = edge.resolved_target_version
                    existing.ingestion_timestamp = edge.ingestion_timestamp
                else:
                    db_edge = DependencyEdgeModel(
                        ecosystem=edge.ecosystem,
                        source_package=edge.source_package,
                        source_version=edge.source_version,
                        target_package=edge.target_package,
                        version_constraint=edge.version_constraint,
                        resolved_target_version=edge.resolved_target_version,
                        dependency_type=edge.dependency_type,
                        ingestion_timestamp=edge.ingestion_timestamp
                    )
                    session.add(db_edge)

            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                logger.error(f"IntegrityError saving edges from {edges[0].source_package}@{edges[0].source_version}")

    def get_package(self, ecosystem: str, name: str) -> Optional[Package]:
        with self.SessionLocal() as session:
            db_pkg = session.query(PackageModel).filter_by(
                ecosystem=ecosystem,
                name=name
            ).first()

            if db_pkg:
                return Package(ecosystem=db_pkg.ecosystem, name=db_pkg.name)
        return None

    def get_versions(self, ecosystem: str, package_name: str) -> List[Version]:
        with self.SessionLocal() as session:
            db_versions = session.query(VersionModel).filter_by(
                ecosystem=ecosystem,
                package_name=package_name
            ).all()

            return [
                Version(
                    ecosystem=v.ecosystem,
                    package_name=v.package_name,
                    version=v.version,
                    published_at=v.published_at
                ) for v in db_versions
            ]

    def get_edges_for_version(self, ecosystem: str, package_name: str, version: str) -> List[DependencyEdge]:
        with self.SessionLocal() as session:
            db_edges = session.query(DependencyEdgeModel).filter_by(
                ecosystem=ecosystem,
                source_package=package_name,
                source_version=version
            ).all()

            return [
                DependencyEdge(
                    ecosystem=e.ecosystem,
                    source_package=e.source_package,
                    source_version=e.source_version,
                    target_package=e.target_package,
                    version_constraint=e.version_constraint,
                    resolved_target_version=e.resolved_target_version,
                    dependency_type=e.dependency_type,
                    ingestion_timestamp=e.ingestion_timestamp
                ) for e in db_edges
            ]

    def get_all_versions(self, ecosystem: str) -> List[Version]:
        with self.SessionLocal() as session:
            db_versions = session.query(VersionModel).filter_by(
                ecosystem=ecosystem
            ).all()

            return [
                Version(
                    ecosystem=v.ecosystem,
                    package_name=v.package_name,
                    version=v.version,
                    published_at=v.published_at
                ) for v in db_versions
            ]

    def get_all_edges(self, ecosystem: str) -> List[DependencyEdge]:
        with self.SessionLocal() as session:
            db_edges = session.query(DependencyEdgeModel).filter_by(
                ecosystem=ecosystem
            ).all()

            return [
                DependencyEdge(
                    ecosystem=e.ecosystem,
                    source_package=e.source_package,
                    source_version=e.source_version,
                    target_package=e.target_package,
                    version_constraint=e.version_constraint,
                    resolved_target_version=e.resolved_target_version,
                    dependency_type=e.dependency_type,
                    ingestion_timestamp=e.ingestion_timestamp
                ) for e in db_edges
            ]
