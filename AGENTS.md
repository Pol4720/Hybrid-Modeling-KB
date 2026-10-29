---
id: DOC-AGENTS
type: doc
title: Guía operativa para agentes y mantenedores
status: stable
updated: 2026-10-29
---

# AGENTS.md — Guía operativa

## Resumen ejecutivo
- Este repositorio es la **memoria técnica** de la plataforma universal de modelación (línea base: `Pol4720/Hybrid-Modeling`).
- Léelo en este orden: [`INDEX.md`](INDEX.md) → [`llms-index.md`](llms-index.md) → el documento de la fase que vayas a tocar.
- Todo conocimiento vive en **fichas Markdown con frontmatter YAML** validado contra [`schemas/`](schemas/).
- Las referencias se registran en [`bibliography/manifest.csv`](bibliography/manifest.csv) + [`bibliography/library.bib`](bibliography/library.bib); nunca se inventan.
- Las decisiones se registran como ADR en [`docs/adr/`](docs/adr/INDEX.md).
- Antes de cada PR: `python scripts/kb.py check` (offline) debe pasar; la CI lo repite.
- Autoría: commits y PRs bajo la identidad del propietario (`Pol4720`), sin trailers de coautoría ni marcas de generación.

## 1. Reglas de rigor (no negociables)
1. **Cero citas inventadas.** Cada referencia tiene DOI, arXiv o ISBN verificado contra la fuente (Crossref, arXiv OAI-PMH, Open Library). Si no se puede verificar → `verification: UNVERIFIED` y se explica por qué.
2. **Acceso legal.** Solo se descargan PDFs de acceso abierto. Solo se **versionan** en `bibliography/pdfs/` los que tienen licencia redistribuible (CC-BY, CC-BY-SA, CC0, dominio público). El resto: metadatos + resumen propio con `access: PAYWALLED` u `OA-LINK`. Licencia y `sha256` por archivo en el manifiesto.
3. **Estatus epistémico explícito.** En el texto se etiqueta cada afirmación relevante:
   - `[HECHO]` teorema demostrado o resultado medido (con condiciones de validez).
   - `[PRÁCTICA]` práctica común de la comunidad, sin garantía formal.
   - `[PROPUESTA]` propuesta propia de este repositorio (hipótesis de diseño).
4. **Toda abstracción propuesta** se prueba conceptualmente con ≥2–3 casos de composición (EDO+ABM, CA+EDP, Petri+EDO, red+control óptimo, fluido+partículas).
5. **Cada formalismo/procesamiento** incluye: definición formal, algoritmos canónicos, software de referencia, benchmarks de validación.

## 2. Convenciones de identificadores (estables, nunca se reutilizan)
| Prefijo | Tipo | Carpeta |
|---|---|---|
| `FRM-` | formalismo | `knowledge/cards/formalisms/` |
| `PRC-` | procesamiento sobre modelos | `knowledge/cards/processing/` |
| `CMP-` | patrón/caso de composición | `knowledge/cards/composition/` |
| `PLT-` | plataforma existente | `knowledge/cards/platforms/` |
| `ALG-` | algoritmo | `knowledge/algorithms/` |
| `LIB-` | librería/software | `knowledge/libraries/` |
| `BEN-` | benchmark de validación | `knowledge/benchmarks/` |
| `MOD-` | modelo canónico de dominio | `knowledge/domain-models/` |
| `DPK-` | paquete de dominio | `docs/04-domain-packs/` |
| `PAP-` | ficha de referencia procesada | `bibliography/processed/` |
| `ADR-NNNN` | decisión de arquitectura | `docs/adr/` |
| `DOC-` | documento de síntesis | `docs/**` |
| `GAP-` | brecha frente a la línea base | `docs/07-gap-analysis-roadmap/` |

Renombrar un archivo está permitido; cambiar un `id` no. Si una ficha queda obsoleta: `status: deprecated` + `superseded_by:`.

## 3. Frontmatter mínimo
```yaml
---
id: FRM-ODE            # estable, único
type: formalism        # ver schemas/
title: Ecuaciones diferenciales ordinarias
status: draft          # draft | reviewed | stable | deprecated
updated: 2026-10-29
tags: [continuo, determinista]
refs: [hairer1993, hindmarsh2005]   # claves de bibliography/library.bib
related: [FRM-DAE, PRC-QUAL]        # ids existentes
---
```
Cada documento empieza con `## Resumen ejecutivo` de **≤10 líneas**.

## 4. Flujo de trabajo Git
- Rama por fase o tema: `phase/0-scaffold`, `feat/bib-<tema>`, `docs/<tema>`, `fix/<tema>`.
- **Conventional Commits**: `feat(knowledge): …`, `docs(adr): …`, `chore(ci): …`, `fix(bib): …`.
- PR siempre contra `main` (protegido), referencia issues (`Closes #12`), CI en verde.
- Milestones = fases (F0…F5). Etiquetas: `formalism`, `processing`, `composition`, `domain-pack`, `bibliography`, `gap`, `decision-needed`, `priority:high|medium|low`, `phase:N`.

## 5. Mantenimiento incremental (recetas)
```bash
# añadir un paper (verifica, añade a manifest + bib y crea ficha PAP-)
python scripts/kb.py add-paper --doi 10.1137/S0036144500371907 --tags f:CMP d:EPI
python scripts/kb.py add-paper --arxiv 2103.05244 --tags f:ACAUSAL p:SYM

# re-verificar todas las referencias contra Crossref/arXiv (red necesaria)
python scripts/kb.py dois --online

# regenerar índices (INDEX.md por carpeta + llms-index.md)
python scripts/kb.py index

# verificación completa offline (lo que corre la CI en cada PR)
python scripts/kb.py check
```
- **Revisión trimestral del estado del arte**: issue automático (workflow `quarterly-review.yml`) con checklist: buscar nuevas versiones de las plataformas de la matriz, re-verificar DOIs, revisar ADRs con `status: proposed`.

## 6. Qué no hacer
- No pegar abstracts ni fragmentos largos de artículos con copyright: el resumen es propio.
- No subir PDFs sin licencia redistribuible.
- No editar `INDEX.md`/`llms-index.md` a mano: se generan.
- No mezclar en un mismo PR cambios de varias fases.
