# Hybrid-Modeling-KB

Base de conocimiento técnico para evolucionar **Hybrid-Modeling** hacia una **plataforma universal de modelación sin programación**: un núcleo común (meta-modelo, representación intermedia, composición entre formalismos, pipeline de procesamiento, plugins) más paquetes de dominio (epidemiología, física, química, ecología, neurociencia, economía, tráfico, clima, ingeniería…).

## Resumen ejecutivo
- **Qué es**: la memoria del proyecto. Reúne fundamentos por formalismo, procesamientos, teoría de composición, matriz de plataformas, marco unificador, brechas, roadmap, ADRs, catálogo de algoritmos y librerías, benchmarks y bibliografía verificada.
- **Cómo leerlo**: [`INDEX.md`](INDEX.md) (navegación humana) y [`llms-index.md`](llms-index.md) (mapa compacto para agentes). Las normas están en [`AGENTS.md`](AGENTS.md).
- **Rigor**: referencias verificadas contra Crossref, arXiv y Open Library; PDFs versionados solo con licencia redistribuible; afirmaciones etiquetadas `[HECHO]`/`[PRÁCTICA]`/`[PROPUESTA]`.
- **Calidad**: la CI valida esquemas de frontmatter, enlaces, duplicados, huérfanos, índices e identificadores en cada PR.
- **Por dónde empezar a implementar**: `docs/07-gap-analysis-roadmap/roadmap.md` (Fase 4).

## Estructura
```
README.md  AGENTS.md  CHANGELOG.md  INDEX.md  llms-index.md
docs/          00-vision … 07-gap-analysis-roadmap, adr/
knowledge/     cards/{formalisms,processing,composition,platforms}, algorithms/, libraries/, benchmarks/, domain-models/
bibliography/  library.bib, manifest.csv, pdfs/ (Git LFS, solo licencias redistribuibles), processed/
schemas/       JSON Schema del frontmatter por tipo de ficha
scripts/       kb.py (validate | links | dupes | orphans | summary | index | dois | add-paper | check)
.github/       workflows (CI, revisión trimestral), ISSUE_TEMPLATE, PR template
```

## Uso rápido
```bash
pip install -r scripts/requirements.txt
python scripts/kb.py check          # lo mismo que la CI
python scripts/kb.py index          # regenera índices
python scripts/kb.py add-paper --doi 10.xxxx/yyyy --tags f:ODE
```

## Licencia del contenido
Los textos propios de este repositorio son del propietario (Pol4720). Los PDFs de terceros en `bibliography/pdfs/` conservan su licencia original, registrada por archivo en [`bibliography/manifest.csv`](bibliography/manifest.csv).
