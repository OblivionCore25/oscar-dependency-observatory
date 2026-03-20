# OSCAR -- Dependency Graph Observatory

Graph-based observatory for analyzing transitive dependencies, systemic
risk, and structural patterns in open-source software ecosystems.

------------------------------------------------------------------------

## 📌 Overview

The **Dependency Graph Observatory** is a core module of the OSCAR
project:

> **OSCAR --- Open Supply-Chain Assurance & Resilience for Cloud-Native
> Software Ecosystems**

This module focuses on constructing and analyzing **directed dependency
graphs** across software ecosystems (e.g., npm, PyPI) to identify:

-   Transitive dependency relationships
-   High-impact (central) packages
-   Fragile dependency structures
-   Systemic risk concentrations

The goal is to provide a **data-driven, graph-based foundation** for
understanding how vulnerabilities and failures can propagate across
modern software supply chains.

------------------------------------------------------------------------

## 🧪 Research Motivation

Modern software systems depend heavily on open-source ecosystems with
deeply nested dependency chains. However, existing tools primarily focus
on:

-   Vulnerability scanning (CVE-based)
-   Static SBOM generation

There is limited capability to:

-   Model **dependency topology at scale**
-   Quantify **structural risk propagation**
-   Identify **systemic concentration risks**

This project aims to address that gap using **graph-based analysis and
reproducible datasets**.

------------------------------------------------------------------------

## 🎯 Objectives (MVP)

The initial prototype aims to:

-   Ingest dependency data from **npm and PyPI**
-   Construct **transitive dependency graphs**
-   Compute key graph-based metrics:
    -   Fan-in / Fan-out
    -   Transitive reach
    -   Diamond dependency patterns
    -   Bottleneck (centrality proxy) scores
-   Provide simple APIs or CLI queries
-   Export datasets for research and analysis

------------------------------------------------------------------------

## ❓ Research Questions

This work explores the following questions:

1.  Do software ecosystems exhibit **centralization patterns** that
    increase systemic risk?
2.  Can graph metrics serve as proxies for **blast radius estimation**?
3.  How prevalent are **diamond dependency structures**, and how do they
    affect failure propagation?
4.  Can dependency snapshots reveal **emerging risk concentrations over
    time**?

------------------------------------------------------------------------

## 🧠 Hypothesis

> A small subset of packages within major ecosystems exhibits
> disproportionately high centrality and downstream exposure, making
> them critical points of systemic vulnerability.

------------------------------------------------------------------------

## 🏗️ MVP Scope

To ensure feasibility and reproducibility, the MVP is intentionally
scoped:

-   Focus on **package/version-level dependency graphs**
-   Initial support for:
    -   npm
    -   PyPI
-   Deterministic ingestion and normalization
-   Emphasis on **interpretable metrics**, not complex models

Future phases will extend into:

-   Code-level (method/function) dependency analysis
-   SBOM integration
-   Provenance and trust signals
-   Chaos testing for supply-chain resilience

------------------------------------------------------------------------

## 🗂️ Project Structure

    oscar-dependency-observatory/

    backend/
      app/
        ingestion/
        graph/
        analytics/
        api/
        models/
        storage/

    scripts/
    data/
    notebooks/
    docker/

------------------------------------------------------------------------

## 🚀 Getting Started (Planned)

### 1. Run API (FastAPI)

    uvicorn app.main:app --reload

### 2. Ingest a package

    GET /ingest/npm/{package}

### 3. Query dependencies

    GET /dependencies/{package}/{version}
    GET /dependencies/{package}/{version}/transitive

------------------------------------------------------------------------

## 📊 Example Metrics

-   **Fan-out**: Number of dependencies (direct + transitive)
-   **Fan-in**: Number of dependents
-   **Bottleneck score**:

```{=html}
<!-- -->
```
    score = fan_in * log(transitive_dependents + 1)

-   **Diamond detection**:

```{=html}
<!-- -->
```
    A → B → D
    A → C → D

------------------------------------------------------------------------

## 📦 Dataset Outputs

The observatory produces:

-   Dependency graph datasets (JSON / CSV)
-   Snapshot-based graph states
-   Derived metrics for analysis

These datasets are intended for:

-   Research experiments
-   Visualization
-   Risk modeling

------------------------------------------------------------------------

## 🔜 Roadmap

### Phase A (Current)

-   Dependency graph ingestion
-   Graph analytics
-   Dataset generation

### Phase B

-   Code-level dependency mapping (methods/classes)
-   Language-specific analysis (Java, Python)

### Phase C

-   Unified multi-level graph (code + package + SBOM)
-   Advanced risk modeling

------------------------------------------------------------------------

## 🤝 Collaboration

This repository is an **early-stage working prototype** intended to
facilitate collaboration and research discussion.

> ⚠️ The architecture, scope, and implementation are expected to evolve.

Feedback is highly encouraged, especially on:

-   Research direction
-   Metric definitions
-   Data modeling
-   Ecosystem coverage

------------------------------------------------------------------------

## 📄 License

TBD

------------------------------------------------------------------------

## 👤 Author

Fabian Gonzalez\
Software Engineer \| Distributed Systems \| Cloud Infrastructure

------------------------------------------------------------------------

## 🌐 Related Work (to be expanded)

-   Software dependency networks research
-   Supply-chain security (Log4j, SolarWinds)
-   Graph-based risk analysis
-   SBOM standards (SPDX, CycloneDX)
