# OSCAR Method-Level Dependency Observatory — Technical Specification (MVP Extension)

**Version:** 0.1.0 (Experimental MVP)  
**Date:** March 2026  
**Author:** Fabian Gonzalez  

---

# 1. 🎯 Objective

The goal of this module is to extend the OSCAR Dependency Graph Observatory from **package-level analysis** to **method-level usage analysis**, enabling:

- More precise **risk estimation**
- Detection of **actual dependency usage patterns**
- Reduction of **false positives in supply-chain risk modeling**

---

# 2. 🧠 Problem Statement

Current dependency analysis assumes:

> “If a package is included, all of it is equally relevant.”

This leads to:

- Overestimated risk (fan-in inflation)
- Lack of visibility into **actual usage**
- No distinction between:
  - critical usage vs incidental usage

---

# 3. 🚀 Proposed Solution

Introduce a **Method-Level Dependency Graph Layer** that:

- Extracts **function-level usage** from source code
- Maps usage to packages
- Computes **fine-grained dependency metrics**

---

# 4. 🏗️ Architecture

```mermaid
flowchart LR
    A[Source Code Project] --> B[AST Parser (Babel)]
    B --> C[Import Extractor]
    B --> D[Call Expression Analyzer]

    C --> E[Symbol Table]
    D --> F[Usage Resolver]

    E --> F
    F --> G[Method Usage Map]

    G --> H[Method-Level Graph]
    G --> I[Metrics Engine]

    I --> J[Insight Layer]
    H --> J

    J --> K[API Layer]
```

---

# 5. ⚙️ Technology Stack

| Component | Technology |
|----------|----------|
| AST Parsing | @babel/parser |
| Traversal | @babel/traverse |
| Language Support | JavaScript / TypeScript |
| Backend Integration | FastAPI (existing OSCAR backend) |
| Storage | JSON (aligned with current storage model) |

---

# 6. 📦 Scope Definition (STRICT MVP)

### Included:
- npm ecosystem only
- JavaScript / TypeScript only
- Static import + method usage extraction
- 1–3 sample projects

### Excluded:
- Dynamic imports (require(variable))
- Reflection / runtime evaluation
- Full ecosystem scanning

---

# 7. 🔍 Data Extraction Pipeline

## 7.1 Input

- Local project directory
- Source files (.js, .ts, .tsx)

---

## 7.2 Import Extraction

Example:

```javascript
import { useState } from "react"
import _ from "lodash"
```

Output:

```json
{
  "react": ["useState"],
  "lodash": ["default"]
}
```

---

## 7.3 Method Call Extraction

Example:

```javascript
useState()
_.merge(obj1, obj2)
```

Output:

```json
[
  { "package": "react", "method": "useState" },
  { "package": "lodash", "method": "merge" }
]
```

---

## 7.4 Combined Usage Map

```json
{
  "file": "App.js",
  "usages": [
    { "package": "react", "method": "useState" },
    { "package": "lodash", "method": "merge" }
  ]
}
```

---

# 8. 🧩 Method-Level Graph Model

## Node Types

| Type | Example |
|------|--------|
| Method Node | react::useState |
| Package Node (optional) | react@18.2.0 |

---

## Edge Types

| Edge | Meaning |
|------|--------|
| App::Component → react::useState | usage |
| react::useState → scheduler::scheduleUpdate | internal dependency (future) |

---

# 9. 📊 Metrics (Core Contribution)

## 9.1 Effective Dependency Weight (EDW)

Definition:

EDW(P) = number of methods used from package P

---

## 9.2 Usage Concentration Ratio (UCR)

Definition:

UCR(P) = used_methods / total_methods_in_package

---

## 9.3 Critical Method Centrality (CMC)

Definition:

CMC(M) = number_of_projects_using_method_M

---

## 9.4 Effective Blast Radius (EBR)

Definition:

EBR(M) = number_of_call_sites_or_paths_using_M

---

# 10. 🔥 Insight Generation Layer

## Goal:
Compare package-level vs method-level signals

---

## Insight 1: Risk Inflation

Example:

| Package | fan-in | EDW |
|--------|--------|-----|
| lodash | 1000 | 2 |

Insight:
Package-level metrics overestimate risk

---

## Insight 2: Hidden Critical Methods

Example:
lodash::merge → high usage  
lodash::chunk → low usage  

Insight:
Risk is concentrated in specific methods

---

## Insight 3: Over-Dependency Detection

Detect:
- imported but unused methods
- heavy libraries with minimal usage

---

# 11. 🔌 API Design

## POST /analysis/method-usage

Input:

```json
{
  "projectPath": "./sample-app"
}
```

Response:

```json
{
  "packages": [
    {
      "name": "lodash",
      "methodsUsed": ["merge"]
    }
  ]
}
```

---

## GET /metrics/method-level

```json
{
  "packages": [
    {
      "name": "lodash",
      "EDW": 1,
      "UCR": 0.02
    }
  ]
}
```

---

## GET /comparison/package-vs-method

```json
{
  "lodash": {
    "fanIn": 1000,
    "EDW": 2,
    "riskInflation": true
  }
}
```

---

# 12. 🧠 AST Extraction Implementation (Code Template)

```javascript
import { parse } from "@babel/parser"
import traverse from "@babel/traverse"
import fs from "fs"

const code = fs.readFileSync(file, "utf-8")

const ast = parse(code, {
  sourceType: "module",
  plugins: ["jsx", "typescript"]
})

const imports = {}
const usages = []

traverse(ast, {
  ImportDeclaration(path) {
    const source = path.node.source.value
    path.node.specifiers.forEach(spec => {
      imports[spec.local.name] = source
    })
  },

  CallExpression(path) {
    const callee = path.node.callee

    if (callee.type === "Identifier") {
      const pkg = imports[callee.name]
      if (pkg) {
        usages.push({ package: pkg, method: callee.name })
      }
    }

    if (callee.type === "MemberExpression") {
      const object = callee.object.name
      const method = callee.property.name
      const pkg = imports[object]

      if (pkg) {
        usages.push({ package: pkg, method })
      }
    }
  }
})
```

---

# 13. 📅 Implementation Plan (10 Days)

| Day | Task |
|----|-----|
| 1–2 | AST parser + extraction |
| 3–4 | usage map |
| 5–6 | metrics |
| 7–8 | comparison layer |
| 9–10 | insights + demo |

---

# 14. 🔬 Research Framing

## Title

Beyond Package-Level Dependency Graphs: A Method-Level Approach to Software Supply Chain Risk Analysis

---

## Research Questions

1. Does package-level centrality correlate with actual usage?
2. Can method-level analysis reduce false positives?
3. Is risk concentrated at method-level?

---

## Hypothesis

Package-level graphs overestimate systemic risk due to lack of usage granularity.

---

# 15. 🧾 EB2 NIW Alignment

This module strengthens the endeavor by:

- Introducing novel analytical methodology
- Advancing cybersecurity risk modeling
- Contributing to national infrastructure resilience

---

# 16. ⚠️ Known Limitations

| Area | Limitation |
|------|-----------|
| Static Analysis | Cannot capture runtime behavior |
| Dynamic Imports | Not supported |
| Language Scope | JS/TS only |
| Method Enumeration | May require heuristics |

---

# 17. 🚀 Future Extensions

- Multi-language support (Python AST, Java)
- Integration with SBOM Observatory
- Chaos testing at method-level
- Maintainer attribution per method

---

# 🔥 Final Statement

This module transforms OSCAR from:

Structural dependency analysis → Behavioral dependency intelligence
