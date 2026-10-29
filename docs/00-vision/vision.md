---
id: DOC-VISION
type: doc
title: Visión, alcance y principios de la plataforma universal de modelación
status: reviewed
updated: 2026-10-29
phase: 0
tags: [vision, scope]
related: [DOC-BASELINE, DOC-DEPTH-LEVELS]
---

# Visión y alcance

## Resumen ejecutivo
- Objetivo: generalizar Hybrid-Modeling (EDO + CA + ABM + composición para epidemiología) a una **plataforma universal sin programación**. El usuario debe poder declarar, componer, simular y *procesar* modelos de cualquier dominio.
- Prioridad: **amplitud y generalidad con rigor**. La profundidad por dominio es deliberadamente menor que la de un simulador especializado y se declara con niveles L0–L3 ([`depth-levels.md`](depth-levels.md)).
- Arquitectura: un **núcleo común** (meta-modelo, IR, semántica de composición, pipeline, plugins) más **paquetes de dominio** finos encima.
- Ejes de trabajo: A = universo de formalismos, B = procesamientos sobre cualquier modelo, C = paquetes de dominio.
- Entregables: matriz de plataformas, fundamentos por formalismo, marco unificador, brechas + roadmap + ADRs, catálogo de algoritmos y librerías, suite de benchmarks y bibliografía verificada.

## 1. Problema
Las herramientas existentes son excelentes dentro de un paradigma (SUNDIALS/ModelingToolkit para ecuaciones, NetLogo/Mesa para agentes, COPASI para bioquímica, FEniCS para EDP) o en una familia de acoplamientos (Modelica/FMI para sistemas físicos acausales, AnyLogic para SD+DES+ABM). Lo que falta es: (i) una representación común que permita **componer formalismos heterogéneos con semántica explícita**; (ii) que los **procesamientos** (sensibilidad, inferencia, reducción, verificación) se apliquen de forma uniforme sobre esa representación; (iii) que todo sea accesible **sin programar**. Ver la matriz en `docs/05-platforms-sota/platform-matrix.md` (Fase 3).

## 2. Principios
1. **Semántica primero** `[PROPUESTA]`: cada formalismo se define por su espacio de estados, su base temporal y su regla de evolución. La UI y los solvers derivan de esa definición, no al revés.
2. **Composición tipada** `[PROPUESTA]`: los submodelos se conectan por **puertos** con tipo (dominio, unidad, causalidad, base temporal). Una conexión entre bases temporales distintas exige un **adaptador** explícito (muestreo, retención, agregación, evento).
3. **Procesamiento como transformación de IR** `[PROPUESTA]`: un análisis consume una IR y devuelve otra IR o un artefacto; se declaran precondiciones (diferenciable, determinista, finito…).
4. **Integrar antes que reimplementar** `[PRÁCTICA]`: los solvers de referencia (SUNDIALS, PETSc, FEniCS, SALib, PRISM…) se envuelven como backends. Se reimplementa solo lo que no existe con licencia compatible o lo que es crítico para la composición.
5. **Reproducibilidad por defecto**: semilla, versión de modelo (hash de IR), versión de backend y configuración del solver quedan en cada resultado.
6. **Declarar el nivel**: cada formalismo, procesamiento y dominio publica su nivel L0–L3 y la suite de benchmarks que lo respalda.

## 3. Fuera de alcance (explícito)
- Fidelidad de simulador especializado (CFD turbulento industrial, MD de proteínas a escala de µs, electromagnetismo 3D de alta frecuencia, NWP climático). Se cubre como **L3-delegado** cuando un backend externo lo permite.
- Entrenamiento de modelos de ML de gran escala; los formalismos basados en datos se restringen a modelos compactos (SINDy, GP, Neural ODE pequeñas).

## 4. Mapa del repositorio
| Carpeta | Contenido |
|---|---|
| [`docs/01-formalisms`](../01-formalisms/INDEX.md) | Síntesis del Eje A |
| [`docs/02-composition-theory`](../02-composition-theory/INDEX.md) | Teoría de composición |
| [`docs/03-model-processing`](../03-model-processing/INDEX.md) | Síntesis del Eje B |
| [`docs/04-domain-packs`](../04-domain-packs/INDEX.md) | Eje C: un documento por dominio |
| [`docs/05-platforms-sota`](../05-platforms-sota/INDEX.md) | Matriz de plataformas |
| [`docs/06-unified-framework`](../06-unified-framework/INDEX.md) | Marco unificador e IR |
| [`docs/07-gap-analysis-roadmap`](../07-gap-analysis-roadmap/INDEX.md) | Brechas y roadmap |
| [`docs/adr`](../adr/INDEX.md) | Decisiones de arquitectura |
| [`knowledge/`](../../knowledge/INDEX.md) | Fichas atómicas |
| [`bibliography/`](../../bibliography/README.md) | Referencias verificadas |
