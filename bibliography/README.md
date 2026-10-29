# Bibliografía

## Resumen ejecutivo
- [`library.bib`](library.bib) es la fuente BibTeX y [`manifest.csv`](manifest.csv) el registro con verificación, acceso, licencia y hash. Ambos tienen exactamente las mismas claves.
- Fichas procesadas en [`processed/`](processed/INDEX.md), una por referencia (`PAP-<clave>`).
- PDFs en `pdfs/` (Git LFS) **solo** cuando la licencia permite redistribución (CC-BY, CC-BY-SA, CC0, dominio público).
- Política de acceso: `OA` (redistribuible, PDF versionado), `OA-LINK` (lectura libre, no redistribuible: se guarda el enlace y el `sha256` del archivo leído), `PAYWALLED` (metadatos + resumen propio), `WEB` (recurso web sin identificador persistente).

## Verificación
| Campo | Significado |
|---|---|
| `verification` | `VERIFIED` si el identificador resuelve en la fuente **y** el título coincide (similitud ≥0.8). Si no, `UNVERIFIED`. |
| `verified_via` | `crossref`, `arxiv-oai`, `openlibrary` o `doi.org-handle` |
| `title_similarity` | Similitud normalizada entre el título esperado y el de la fuente |
| `sha256`, `size_bytes` | Hash del PDF leído (versionado o no) |
| `license` | Licencia de la copia descargada (Unpaywall/arXiv/editor) |
| `redistributable` | `yes` solo si la licencia lo permite |

Las fichas `processing: fulltext-assisted` se redactaron leyendo el texto completo OA. Las `metadata-and-own-summary` se basan en metadatos verificados y en el conocimiento del trabajo, sin leer el texto completo; así se indica en cada ficha.
