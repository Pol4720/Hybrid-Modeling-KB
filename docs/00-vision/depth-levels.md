---
id: DOC-DEPTH-LEVELS
type: doc
title: Niveles de profundidad L0–L3 (formalismos, procesamientos, dominios)
status: reviewed
updated: 2026-10-29
phase: 0
tags: [scope, maturity]
related: [DOC-VISION]
---

# Niveles de profundidad

## Resumen ejecutivo
- Escala común para declarar cuánto cubre la plataforma de cada formalismo, procesamiento o dominio.
- **L0** no soportado · **L1** representable y simulable · **L2** analizable y validado · **L3** especializado (casi siempre delegado a un backend externo).
- El objetivo por defecto del núcleo es **L2** en los formalismos centrales y **L1** en los periféricos.
- Un nivel solo se reclama si la suite de benchmarks correspondiente pasa ([`../../knowledge/benchmarks/INDEX.md`](../../knowledge/benchmarks/INDEX.md)).

## Definiciones `[PROPUESTA]`

| Nivel | Criterio verificable |
|---|---|
| **L0 — No soportado** | No se puede declarar en la IR. |
| **L1 — Representable** | (a) se declara en la IR con validación estructural (tipos, unidades, dimensiones); (b) hay al menos un solver de referencia con configuración documentada; (c) pasa ≥1 benchmark de formalismo con referencia analítica o publicada; (d) exporta resultados con metadatos de reproducibilidad. |
| **L2 — Analizable y validado** | L1 + (e) se compone con al menos otros 2 formalismos mediante puertos tipados y adaptadores; (f) admite los procesamientos genéricos aplicables (sensibilidad, calibración, UQ y, si es determinista y suave, análisis cualitativo); (g) pasa la suite completa de su formalismo con tolerancias declaradas; (h) importa/exporta un estándar cuando existe (SBML, FMI, NeuroML…). |
| **L3 — Especializado** | Rendimiento y fidelidad comparables a un simulador especializado: mallas 3D complejas, HPC, multifísica fuertemente acoplada, escalas industriales. Se alcanza como **L3-delegado**: la IR se traduce a un backend (FEniCS, OpenFOAM, LAMMPS, NEST…) que hace el trabajo pesado. |

## Reglas de declaración
- Cada ficha `FRM-`, `PRC-` y `DPK-` lleva `baseline_support` (estado actual) y `target_level` (objetivo del roadmap).
- Subir de nivel requiere un PR con la suite de benchmarks en verde y la actualización de la ficha.
- Bajar de nivel (regresión) bloquea la publicación de la versión.
