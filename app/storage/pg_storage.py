import json
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from app.models.domain import Package, Version, DependencyEdge
from app.storage import StorageService
from app.storage.models import Base, PackageModel, VersionModel, DependencyEdgeModel

class PgStorage(StorageService):
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        # Automatically create tables for MVP.
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def save_package(self, package: Package) -> None:
        with self.SessionLocal() as session:
            stmt = insert(PackageModel).values(
                ecosystem=package.ecosystem,
                name=package.name
            )
            # Use ON CONFLICT DO NOTHING to emulate idempotent inserts
            stmt = stmt.on_conflict_do_nothing(
                index_elements=['ecosystem', 'name']
            )
            session.execute(stmt)
            session.commit()

    def save_versions(self, versions: List[Version]) -> None:
        if not versions:
            return
            
        with self.SessionLocal() as session:
            values = []
            for v in versions:
                values.append(dict(
                    ecosystem=v.ecosystem,
                    package_name=v.package_name,
                    version=v.version,
                    published_at=v.published_at
                ))
            
            stmt = insert(VersionModel).values(values)
            # On conflict, optionally update but for versions it's generally immutable
            stmt = stmt.on_conflict_do_update(
                index_elements=['ecosystem', 'package_name', 'version'],
                set_=dict(published_at=stmt.excluded.published_at)
            )
            session.execute(stmt)
            session.commit()

    def save_edges(self, edges: List[DependencyEdge]) -> None:
        if not edges:
            return

        # Deduplicate within the batch using the unique constraint key.
        # PostgreSQL's ON CONFLICT DO UPDATE cannot handle two rows in the
        # same INSERT that conflict with each other (CardinalityViolation).
        # Using a dict keyed on the constraint columns ensures uniqueness;
        # the last occurrence wins, matching the upsert semantics.
        seen: dict = {}
        for e in edges:
            key = (
                e.ecosystem,
                e.source_package,
                e.source_version,
                e.target_package,
                e.dependency_type or "runtime",
            )
            seen[key] = dict(
                ecosystem=e.ecosystem,
                source_package=e.source_package,
                source_version=e.source_version,
                target_package=e.target_package,
                version_constraint=e.version_constraint,
                resolved_target_version=e.resolved_target_version,
                dependency_type=e.dependency_type or "runtime",
                ingestion_timestamp=e.ingestion_timestamp,
            )

        values = list(seen.values())

        with self.SessionLocal() as session:
            stmt = insert(DependencyEdgeModel).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ecosystem', 'source_package', 'source_version', 'target_package', 'dependency_type'],
                set_=dict(
                    version_constraint=stmt.excluded.version_constraint,
                    resolved_target_version=stmt.excluded.resolved_target_version,
                    ingestion_timestamp=stmt.excluded.ingestion_timestamp,
                )
            )
            session.execute(stmt)
            session.commit()

    def get_package(self, ecosystem: str, name: str) -> Optional[Package]:
        with self.SessionLocal() as session:
            row = session.query(PackageModel).filter_by(ecosystem=ecosystem, name=name).first()
            if row:
                return Package(ecosystem=row.ecosystem, name=row.name)
        return None

    def get_versions(self, ecosystem: str, package_name: str) -> List[Version]:
        with self.SessionLocal() as session:
            rows = session.query(VersionModel).filter_by(ecosystem=ecosystem, package_name=package_name).all()
            return [
                Version(
                    package_name=r.package_name,
                    ecosystem=r.ecosystem,
                    version=r.version,
                    published_at=r.published_at
                ) for r in rows
            ]

    def get_edges_for_version(self, ecosystem: str, package_name: str, version: str) -> List[DependencyEdge]:
        with self.SessionLocal() as session:
            rows = session.query(DependencyEdgeModel).filter_by(
                ecosystem=ecosystem,
                source_package=package_name,
                source_version=version
            ).all()
            
            return [
                DependencyEdge(
                    ecosystem=r.ecosystem,
                    source_package=r.source_package,
                    source_version=r.source_version,
                    target_package=r.target_package,
                    version_constraint=r.version_constraint,
                    resolved_target_version=r.resolved_target_version,
                    dependency_type=r.dependency_type,
                    ingestion_timestamp=r.ingestion_timestamp
                ) for r in rows
            ]

    def get_all_versions(self, ecosystem: str) -> List[Version]:
        with self.SessionLocal() as session:
            rows = session.query(VersionModel).filter_by(ecosystem=ecosystem).all()
            return [
                Version(
                    package_name=r.package_name,
                    ecosystem=r.ecosystem,
                    version=r.version,
                    published_at=r.published_at
                ) for r in rows
            ]

    def get_all_edges(self, ecosystem: str) -> List[DependencyEdge]:
        with self.SessionLocal() as session:
            rows = session.query(DependencyEdgeModel).filter_by(ecosystem=ecosystem).all()
            return [
                DependencyEdge(
                    ecosystem=r.ecosystem,
                    source_package=r.source_package,
                    source_version=r.source_version,
                    target_package=r.target_package,
                    version_constraint=r.version_constraint,
                    resolved_target_version=r.resolved_target_version,
                    dependency_type=r.dependency_type,
                    ingestion_timestamp=r.ingestion_timestamp
                ) for r in rows
            ]
