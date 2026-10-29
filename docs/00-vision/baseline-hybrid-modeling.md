---
id: DOC-BASELINE
type: doc
title: "Paso 0 — Análisis de la plataforma actual (Hybrid-Modeling)"
status: reviewed
updated: 2026-10-29
phase: 0
tags: [baseline, gap-analysis]
related: [DOC-VISION, DOC-DEPTH-LEVELS]
---

# Paso 0 — Línea base: `Pol4720/Hybrid-Modeling`

## Resumen ejecutivo
- Analizado el commit `de56ed9` (rama `main`, privado): backend FastAPI/Python, frontend React + ReactFlow, PostgreSQL + Alembic.
- 4 paradigmas: **EDO** compartimental, **CA** de estados discretos, **ABM** con motor propio y **metamodelo** (composición). 136 rutas REST; 43 archivos de test con 1120 funciones `test_*`.
- El meta-modelo raíz (`BaseEpidemiologicalModel`) está **acoplado a epidemiología**: compartimentos, R0, vacunación y métricas `peak_infected` detectan infectados porque el nombre de la columna contiene `"I"`.
- La **composición** es secuencial y de un solo paso: cada submodelo corre todo el horizonte y entrega el *último valor* de una salida como *parámetro* del siguiente. Las estrategias `parallel`, `co_simulation` y `feedback` se declaran, pero no están implementadas.
- Procesamientos sólidos para el dominio original: Sobol/Morris (SALib), unas 20 estrategias de calibración (locales, globales, metaheurísticas, MCMC y ABC), R0 por matriz de siguiente generación, estabilidad por jacobiano numérico, coste-beneficio y escenarios.
- Ausentes: DAE/EDP/DDE/SDE, SSA/Gillespie, eventos, unidades, intercambio (SBML/SED-ML/FMI), semillas controladas en CA, IR declarativa y verificación formal.
- Conclusión: la base sirve como **producto de dominio** (epidemiología). Como **núcleo universal** hay que rediseñarla. Detalle de brechas en `docs/07-gap-analysis-roadmap/gap-analysis.md` (Fase 4).

## 1. Alcance del análisis
- Repositorio: `https://github.com/Pol4720/Hybrid-Modeling` (privado), commit `de56ed9e4f3d9e107d84332d121aca97f693a792`.
- Leídos de forma directa: `app/domain/models/{base,generic_ode,generic_ca,generic_abm,generic_metamodel}.py`, `app/domain/simulation/engines/{base,ode_engine,ca_engine,abm_engine,metamodel_engine}.py`, `app/core/model_resolver.py`, `app/domain/{sensitivity,fitting,endemicity,optimization}`, `app/domain/builders/__init__.py`, servicios de *builders*, `README.md` y `.github/workflows/ci.yml`.
- Métricas obtenidas por búsqueda automática en el código (`grep`), no estimadas a mano: 136 decoradores `@router.*`, 43 archivos de test, 1120 `def test_`, 0 apariciones de `sbml`, `gillespie`, `pint`/`UnitRegistry` ni `GaussianProcess`/`Kriging`.

## 2. Objetos matemáticos soportados

| Paradigma | Representación en el código | Semántica efectiva | Observaciones |
|---|---|---|---|
| EDO (`GenericODEModel`) | Lista de *transiciones* `from → to` con `rate_expression` (cadena Python) | $\dot{x}_i = \sum_{k: to=i} f_k(x,p,t) - \sum_{k: from=i} f_k(x,p,t)$; fuentes y sumideros cuando `from`/`to` son nulos | Es en la práctica una **red de flujos estoquiométrica** (≈ red de Petri continua). Se evalúa con `eval` en cada llamada al RHS. **El RHS recorta los estados a $\max(y_i,0)$**, lo que rompe sistemas con estados negativos (péndulo, Lorenz, circuitos) e introduce no-suavidad. Si falla una expresión, el flujo se pone a 0 **en silencio**. Solver por defecto: `solve_ivp` RK45. |
| CA (`GenericCAModel` + `CAEngine`) | Estados discretos, reglas `from_state → to_state` con `probability` y `condition` evaluada sobre conteos de vecinos | Autómata estocástico síncrono, asíncrono o secuencial; vecindarios Moore, von Neumann, hexagonal y extendido; fronteras periódicas, fijas, reflectivas o absorbentes | Usa `np.random.random()` global, sin semilla por ejecución, y por tanto **no es reproducible**. La probabilidad es por paso y no depende de `dt`. La regla se evalúa con `eval` celda a celda, con un coste de $O(N\cdot R)$ intérprete por paso. |
| ABM (`GenericABMModel` + `ABMEngine`) | Tipos de agente con atributos y reglas; espacios grid, continuo (con hash espacial) y red; *schedulers* random, simultaneous y staged | Tiempo discreto de paso fijo | Motor propio inspirado en Mesa; el *builder* genera código Mesa. Las salidas se agregan a conteos por estado. |
| Metamodelo (`GenericMetamodel`) | `sub_models`, `variable_mappings`, `coupling`, `execution_order` | Ejecución **secuencial**: corre el submodelo A en $[t_0,t_f]$, toma el último valor de `A.var` y lo asigna como parámetro de B | No hay sincronización temporal, ni realimentación, ni conservación en la interfaz, ni unidades. `MetamodelEngine.step()` solo incrementa un contador. El README describe "Metamodel" como *surrogates* (polinomios, Kriging, NN), pero **no hay código de surrogates**. |

**[HECHO]** (observado en el código) La interfaz común `run_simulation(t_span) → SimulationResult(time, compartments)` iguala todos los paradigmas a **series temporales agregadas**. Es un buen mínimo común, pero pierde la estructura espacial (CA) y la individual (ABM) que haría falta para acoplar a nivel de campo o de agente.

## 3. Composición
- Tipos declarados (`CouplingType`): `hierarchical`, `parallel`, `sequential`, `feedback`. Solo existe el comportamiento secuencial, y es *one-shot*.
- **[HECHO]** Con esta semántica no se puede expresar EDO↔ABM bidireccional, CA↔EDP con intercambio por paso, ni Petri+EDO con eventos. Cualquier realimentación exige iterar en el tiempo (co-simulación con *macro-steps* o acoplamiento monolítico); ver `docs/02-composition-theory/composition-theory.md` (Fase 3).
- **[PRÁCTICA]** La "composición por paso de parámetros" equivale a un acoplamiento débil unidireccional (*one-way coupling*). Solo es válida si la escala temporal del emisor es mucho más lenta que la del receptor o si el emisor no depende del receptor.

## 4. Procesamientos existentes

| Procesamiento | Implementación | Alcance |
|---|---|---|
| Sensibilidad global | SALib: Sobol (Saltelli), Morris; OAT | Escalar de salida (métrica epidemiológica) |
| Calibración | `domain/fitting/strategies.py`: Nelder-Mead, Powell, L-BFGS-B, LM, TRF, DE, basin-hopping, dual annealing, SHGO, brute force, DIRECT, AMPGO, PSO, GA, SA, CMA-ES, emcee, Metropolis, ABC-rechazo, ABC-SMC, multistart, híbrida | Muy completo para EDO de pocos parámetros; la función objetivo interpola un solo compartimento |
| Análisis cualitativo | `endemicity.py`: R0 (SIR/SEIR cerrados y NGM $\rho(FV^{-1})$), equilibrios por `fsolve`, jacobiano por diferencias finitas, clasificación por autovalores, "bifurcación" 1-parámetro por barrido | Sin continuación numérica ni detección de Hopf por funciones test |
| Optimización / control | Parser de expresiones objetivo (sympy) sobre trayectorias, escenarios | Optimización de parámetros/escenarios; no hay control óptimo dinámico |
| Coste-beneficio, reportes | Motor CBA con parser de expresiones; reportes PDF | Específico de salud pública |
| Codegen | *Builders* que generan código Python (EDO con sympy, CA, ABM-Mesa) | Generación para exportar, no para ejecutar con rendimiento |

## 5. Resultados cuantitativos reportados por la propia plataforma
El informe del proyecto (carpeta `Report/` y la figura de síntesis) reporta **[HECHO, medido por los autores; no reproducido aquí]**:
- LSODA es el solver de EDO más rápido en su banco (≈10.35 ms, IC95 8.60–12.09) y Radau obtiene el mejor NRMSE.
- Escalado casi lineal con el tamaño del problema: exponentes $\alpha_{CA}=0.965\pm0.060$ y $\alpha_{ABM}=0.958\pm0.058$.
- 10 métodos de ajuste con error relativo medio ≈0.3%; PSO alcanza el menor (0.273%) y L-BFGS-B es el más rápido (0.510 s).

Supuesto de validez: banco con modelos SIR/SEIR de baja dimensión. Estos números **no** se extrapolan a sistemas rígidos grandes ni a acoplamientos.

## 6. Limitaciones críticas para la generalización (resumen)
1. **Meta-modelo con sesgo de dominio**: `BaseEpidemiologicalModel`, `R0ComputationInfo`, `supports_vaccination`, cotas por nombre de parámetro griego (`β∈[0,2]`).
2. **Sin IR declarativa**: los modelos son objetos Python con `eval` de cadenas. No hay grafo simbólico que permita derivar jacobianos, reducir, verificar ni generar código.
3. **Composición sin semántica temporal** (ver §3).
4. **Tipos y unidades ausentes**: variables sin dimensión, sin dominio (ℝ, ℝ≥0, ℕ, categórico) y sin causalidad declarada.
5. **Reproducibilidad**: RNG global en CA; sin registro de semilla ni hash de versión del modelo en los resultados.
6. **Robustez numérica**: recorte a 0 dentro del RHS, errores silenciosos y RK45 por defecto incluso en problemas rígidos (aunque existe un `StiffnessDetector` en `ode_engine.py`, el camino `GenericODEModel.run_simulation` no lo usa).
7. **Rendimiento**: interpretación por celda/agente con `eval`; sin vectorización ni JIT.
8. **Interoperabilidad**: ni SBML, ni SED-ML, ni FMI, ni NeuroML; la exportación es CSV/JSON/PDF.

## 7. Fortalezas a conservar
- Separación limpia en capas (dominio, servicios, API, infraestructura) y el patrón `SimulationEngineFactory` como embrión del registro de plugins.
- Editor visual de nodos (ReactFlow): es la base del requisito "sin programar".
- Batería de calibración y de sensibilidad, ya integrada con la API y la persistencia.
- Cobertura de tests alta en número de casos (1120 funciones), útil como red de seguridad durante la migración.
