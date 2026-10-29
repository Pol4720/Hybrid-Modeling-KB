#!/usr/bin/env python3
"""kb.py — herramienta de mantenimiento del repositorio Hybrid-Modeling-KB.

Subcomandos:
  validate   valida frontmatter contra schemas/*.schema.json, ids únicos, refs y related existentes
  links      comprueba enlaces relativos Markdown
  dupes      detecta duplicados (clave, DOI, arXiv, título) en el manifiesto y en library.bib
  orphans    fichas sin enlaces entrantes, claves bib sin uso, PDFs fuera del manifiesto
  summary    comprueba que cada documento tenga "## Resumen ejecutivo" de <=10 líneas
  index      regenera INDEX.md por carpeta y llms-index.md (usa --check para solo verificar)
  dois       verifica DOIs/arXiv del manifiesto (offline: formato; --online: Crossref/arXiv)
  add-paper  añade una referencia verificada (manifest + bib + ficha PAP-)
  check      validate + links + dupes + orphans + summary + index --check + dois (offline)

Dependencias: pyyaml, jsonschema (requests solo para --online / add-paper).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
MANIFEST = ROOT / "bibliography" / "manifest.csv"
BIB = ROOT / "bibliography" / "library.bib"
PROCESSED = ROOT / "bibliography" / "processed"
PDFS = ROOT / "bibliography" / "pdfs"
CARD_DIRS = ["docs", "knowledge", "bibliography/processed"]
SKIP_NAMES = {"INDEX.md"}
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
PREFIX = {
    "formalism": "FRM-", "processing": "PRC-", "composition": "CMP-", "platform": "PLT-",
    "algorithm": "ALG-", "library": "LIB-", "benchmark": "BEN-", "domain-model": "MOD-",
    "domain-pack": "DPK-", "paper": "PAP-", "adr": "ADR-", "doc": "DOC-", "gap": "GAP-",
}
MANIFEST_FIELDS = [
    "key", "id", "doi", "arxiv", "isbn", "url", "title", "authors", "year", "venue", "type",
    "verification", "verified_via", "verified_on", "title_similarity", "access", "license",
    "redistributable", "oa_url", "pdf_path", "sha256", "size_bytes", "tags", "card", "notes",
]


# ----------------------------------------------------------------------------- utilidades
def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT).as_posix()


def read_fm(path: Path):
    txt = path.read_text(encoding="utf-8")
    m = FM_RE.match(txt)
    if not m:
        return None, txt
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"{rel(path)}: YAML inválido: {e}") from e
    return data, txt[m.end():]


def iter_md():
    for d in CARD_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.md")):
            if p.name in SKIP_NAMES:
                continue
            yield p


def all_cards():
    return {p: read_fm(p) for p in iter_md()}


def bib_keys() -> set[str]:
    if not BIB.exists():
        return set()
    return set(re.findall(r"^@\w+\{([^,\s]+),", BIB.read_text(encoding="utf-8"), flags=re.M))


def read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"<[^>]+>", "", s)).split())


def title_sim(a: str, b: str) -> float:
    a, b = norm_title(a), norm_title(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


class Report:
    def __init__(self, name):
        self.name, self.errors, self.warnings = name, [], []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def show(self) -> bool:
        status = "OK" if not self.errors else "FALLO"
        print(f"[{self.name}] {status} — {len(self.errors)} errores, {len(self.warnings)} avisos")
        for e in self.errors[:200]:
            print(f"  ERROR  {e}")
        for w in self.warnings[:30]:
            print(f"  aviso  {w}")
        if len(self.warnings) > 30:
            print(f"  … {len(self.warnings) - 30} avisos más")
        return not self.errors


# ----------------------------------------------------------------------------- validate
def load_schemas():
    out = {}
    for p in SCHEMAS.glob("*.schema.json"):
        out[p.name.replace(".schema.json", "")] = json.loads(p.read_text(encoding="utf-8"))
    return out


def cmd_validate(args) -> bool:
    import jsonschema

    rep = Report("validate")
    schemas = load_schemas()
    common = schemas.get("common")
    cards = all_cards()
    ids: dict[str, str] = {}
    keys = bib_keys()
    for p, (fm, _body) in cards.items():
        r = rel(p)
        if fm is None:
            rep.err(f"{r}: sin frontmatter YAML")
            continue
        typ = fm.get("type")
        schema = schemas.get(str(typ))
        if schema is None or typ == "common":
            rep.err(f"{r}: type desconocido '{typ}'")
            continue
        full = {"allOf": [common, schema]} if common else schema
        v = jsonschema.Draft202012Validator(full)
        for e in sorted(v.iter_errors(json.loads(json.dumps(fm, default=str))), key=str):
            loc = "/".join(map(str, e.path)) or "(raíz)"
            rep.err(f"{r}: {loc}: {e.message}")
        i = fm.get("id")
        if i:
            if not str(i).startswith(PREFIX.get(typ, "")):
                rep.err(f"{r}: id '{i}' no usa el prefijo {PREFIX.get(typ)} del tipo {typ}")
            if i in ids:
                rep.err(f"{r}: id duplicado '{i}' (también en {ids[i]})")
            ids[i] = r
    for p, (fm, _b) in cards.items():
        if not fm:
            continue
        for ref in fm.get("refs", []) or []:
            if ref not in keys:
                rep.err(f"{rel(p)}: refs '{ref}' no existe en library.bib")
        for rid in fm.get("related", []) or []:
            if rid not in ids:
                rep.err(f"{rel(p)}: related '{rid}' no existe")
        sup = fm.get("superseded_by")
        if sup and sup not in ids:
            rep.err(f"{rel(p)}: superseded_by '{sup}' no existe")
    return rep.show()


# ----------------------------------------------------------------------------- links
def slugify(h: str) -> str:
    h = h.strip().lower()
    h = re.sub(r"[`*_~]", "", h)
    h = re.sub(r"[^\w\- ]", "", h, flags=re.U)
    return h.replace(" ", "-")


def anchors_of(path: Path) -> set[str]:
    txt = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    return {slugify(m) for m in re.findall(r"^#{1,6}\s+(.+?)\s*$", txt, flags=re.M)}


def md_files():
    return [p for p in ROOT.rglob("*.md") if ".git" not in p.parts and "node_modules" not in p.parts]


def strip_code(txt: str) -> str:
    txt = re.sub(r"```.*?```", "", txt, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", txt)


def cmd_links(args) -> bool:
    rep = Report("links")
    for p in md_files():
        txt = strip_code(p.read_text(encoding="utf-8"))
        for target in LINK_RE.findall(txt) + IMG_RE.findall(txt):
            if re.match(r"^(https?:|mailto:)", target) or target == "#":
                continue
            path_part, _, anchor = target.partition("#")
            if path_part.startswith("/"):
                rep.err(f"{rel(p)}: enlace absoluto (usa relativos) -> {target}")
                continue
            dest = (p.parent / path_part).resolve() if path_part else p.resolve()
            if path_part and not dest.exists():
                rep.err(f"{rel(p)}: enlace roto -> {target}")
                continue
            if anchor and dest.suffix == ".md" and anchor not in anchors_of(dest):
                rep.warn(f"{rel(p)}: ancla no encontrada -> {target}")
    return rep.show()


# ----------------------------------------------------------------------------- dupes
def cmd_dupes(args) -> bool:
    rep = Report("dupes")
    rows = read_manifest()
    for field in ("key", "id", "doi", "arxiv", "isbn"):
        seen = {}
        for r in rows:
            v = (r.get(field) or "").strip().lower()
            if not v:
                continue
            if v in seen:
                rep.err(f"manifest: {field} duplicado '{v}' ({seen[v]} y {r['key']})")
            seen[v] = r["key"]
    seen_t = {}
    for r in rows:
        t = norm_title(r.get("title", ""))
        if t and t in seen_t:
            rep.warn(f"manifest: título repetido '{r['title'][:60]}' ({seen_t[t]} y {r['key']})")
        seen_t[t] = r["key"]
    bib = BIB.read_text(encoding="utf-8") if BIB.exists() else ""
    ks = re.findall(r"^@\w+\{([^,\s]+),", bib, flags=re.M)
    for k in sorted({k for k in ks if ks.count(k) > 1}):
        rep.err(f"library.bib: clave duplicada {k}")
    mk = {r["key"] for r in rows}
    for k in sorted(set(ks) - mk):
        rep.err(f"library.bib: clave {k} no está en manifest.csv")
    for k in sorted(mk - set(ks)):
        rep.err(f"manifest.csv: clave {k} no está en library.bib")
    return rep.show()


# ----------------------------------------------------------------------------- orphans
def cmd_orphans(args) -> bool:
    rep = Report("orphans")
    linked: set[Path] = set()
    for p in md_files():
        for t in LINK_RE.findall(strip_code(p.read_text(encoding="utf-8"))):
            if t.startswith(("http", "mailto", "#")):
                continue
            d = (p.parent / t.split("#")[0]).resolve()
            if d != p.resolve():
                linked.add(d)
    for p in iter_md():
        if p.resolve() not in linked:
            rep.err(f"{rel(p)}: huérfano (ningún documento lo enlaza; ejecuta `kb.py index`)")
    used = set()
    for _p, (fm, body) in all_cards().items():
        if fm:
            used.update(fm.get("refs", []) or [])
            if fm.get("bibkey"):
                used.add(fm["bibkey"])
        used.update(re.findall(r"\[@([A-Za-z0-9_:\-]+)\]", body))
    rows = read_manifest()
    for r in rows:
        if r["key"] not in used:
            rep.warn(f"bib: {r['key']} no se usa en ninguna ficha")
    in_manifest = {r.get("pdf_path") for r in rows if r.get("pdf_path")}
    if PDFS.exists():
        for f in PDFS.glob("*.pdf"):
            if rel(f) not in in_manifest:
                rep.err(f"{rel(f)}: PDF no registrado en manifest.csv")
    for r in rows:
        pp = r.get("pdf_path")
        if pp and not (ROOT / pp).exists():
            rep.err(f"manifest: {r['key']} apunta a PDF inexistente {pp}")
        if pp and r.get("redistributable") != "yes":
            rep.err(f"manifest: {r['key']} versiona PDF con licencia no redistribuible ({r.get('license')})")
    return rep.show()


# ----------------------------------------------------------------------------- summary
def cmd_summary(args) -> bool:
    rep = Report("summary")
    targets = [p for p in (ROOT / "docs").rglob("*.md") if p.name != "INDEX.md"]
    targets += [ROOT / n for n in ("README.md", "AGENTS.md") if (ROOT / n).exists()]
    for p in targets:
        _fm, body = read_fm(p)
        m = re.search(r"^##\s+Resumen ejecutivo\s*\n(.*?)(?=^#{1,2}\s|\Z)", body, flags=re.M | re.S)
        if not m:
            rep.err(f"{rel(p)}: falta '## Resumen ejecutivo'")
            continue
        lines = [ln for ln in m.group(1).strip().splitlines() if ln.strip()]
        if len(lines) > 10:
            rep.err(f"{rel(p)}: resumen ejecutivo de {len(lines)} líneas (>10)")
    return rep.show()


# ----------------------------------------------------------------------------- index
INDEX_HEADER = "<!-- Generado por scripts/kb.py index. No editar a mano. -->\n"


def build_indexes() -> dict[Path, str]:
    out: dict[Path, str] = {}
    cards = {p: fm for p, (fm, _b) in all_cards().items() if fm}
    dirs = set()
    for base in CARD_DIRS:
        b = ROOT / base
        if b.exists():
            dirs.add(b)
            dirs.update(x for x in b.rglob("*") if x.is_dir() and "pdfs" not in x.parts)
    for d in sorted(dirs):
        items = sorted([p for p in cards if p.parent == d], key=lambda p: str(cards[p].get("id", p.name)))
        subdirs = sorted([x for x in d.iterdir() if x.is_dir() and x.name != "pdfs"])
        lines = [INDEX_HEADER, f"# Índice — `{rel(d)}`\n"]
        if not items and not subdirs:
            lines.append("_Sin fichas todavía._\n")
        if subdirs:
            lines.append("## Subcarpetas\n")
            for s in subdirs:
                n = sum(1 for p in cards if s in p.parents)
                lines.append(f"- [{s.name}/]({s.name}/INDEX.md) — {n} fichas")
            lines.append("")
        if items:
            lines.append("## Fichas\n")
            lines.append("| ID | Título | Estado | Tags |")
            lines.append("|---|---|---|---|")
            for p in items:
                fm = cards[p]
                tags = ", ".join(map(str, fm.get("tags", []) or []))[:80]
                title = str(fm.get("title", p.stem)).replace("|", "\\|")
                lines.append(f"| `{fm.get('id', '?')}` | [{title}]({p.name}) | {fm.get('status', '')} | {tags} |")
            lines.append("")
        out[d / "INDEX.md"] = "\n".join(lines)
    ll = [INDEX_HEADER, "# llms-index — mapa compacto del repositorio\n",
          "Formato: `ID | tipo | ruta | título`. Punto de entrada para agentes: [AGENTS.md](AGENTS.md).\n", "```"]
    for p in sorted(cards, key=lambda p: (str(cards[p].get("type")), str(cards[p].get("id")))):
        fm = cards[p]
        ll.append(f"{fm.get('id')} | {fm.get('type')} | {rel(p)} | {fm.get('title')}")
    ll.append("```\n")
    out[ROOT / "llms-index.md"] = "\n".join(ll)
    return out


def cmd_index(args) -> bool:
    rep = Report("index")
    for path, content in build_indexes().items():
        cur = path.read_text(encoding="utf-8") if path.exists() else None
        if cur != content:
            if args.check:
                rep.err(f"{rel(path)} desactualizado (ejecuta `python scripts/kb.py index`)")
            else:
                path.write_text(content, encoding="utf-8", newline="\n")
                print(f"  escrito {rel(path)}")
    return rep.show()


# ----------------------------------------------------------------------------- dois
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ARXIV_RE = re.compile(r"^(\d{4}\.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})$")


def crossref(doi: str):
    import requests

    r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=30,
                     headers={"User-Agent": "Hybrid-Modeling-KB/1.0"})
    if r.status_code != 200:
        return None
    m = r.json()["message"]
    t = (m.get("title") or [""])[0]
    sub = m.get("subtitle") or [""]
    return {"title": t + (": " + sub[0] if sub and sub[0] else ""), "raw_title": t, "msg": m}


def arxiv_meta(aid: str):
    import requests

    r = requests.get("https://export.arxiv.org/oai2", timeout=30, params={
        "verb": "GetRecord", "identifier": f"oai:arXiv.org:{aid}", "metadataPrefix": "arXiv"})
    if r.status_code != 200 or "<title>" not in r.text:
        return None
    t = re.search(r"<title>(.*?)</title>", r.text, flags=re.S).group(1)
    lic = re.search(r"<license>(.*?)</license>", r.text)
    return {"title": " ".join(t.split()), "license": lic.group(1) if lic else None, "raw": r.text}


def cmd_dois(args) -> bool:
    rep = Report("dois")
    rows = read_manifest()
    for r in rows:
        doi, ax = (r.get("doi") or "").strip(), (r.get("arxiv") or "").strip()
        if doi and not DOI_RE.match(doi):
            rep.err(f"{r['key']}: DOI con formato inválido '{doi}'")
        if ax and not ARXIV_RE.match(ax):
            rep.err(f"{r['key']}: arXiv id con formato inválido '{ax}'")
        if r.get("verification") not in ("VERIFIED", "UNVERIFIED"):
            rep.err(f"{r['key']}: verification debe ser VERIFIED|UNVERIFIED")
        if r.get("verification") == "VERIFIED" and not (doi or ax or r.get("isbn")):
            rep.err(f"{r['key']}: VERIFIED sin DOI/arXiv/ISBN")
        if r.get("access") not in ("OA", "OA-LINK", "PAYWALLED", "WEB"):
            rep.err(f"{r['key']}: access inválido '{r.get('access')}'")
        if r.get("pdf_path") and not re.fullmatch(r"[0-9a-f]{64}", r.get("sha256") or ""):
            rep.err(f"{r['key']}: PDF sin sha256 válido")
    if args.online:
        sample = rows if not args.sample else rows[: args.sample]
        for r in sample:
            try:
                if r.get("doi"):
                    meta = crossref(r["doi"])
                elif r.get("arxiv"):
                    meta = arxiv_meta(r["arxiv"])
                else:
                    continue
            except Exception as e:
                rep.warn(f"{r['key']}: no se pudo consultar ({e})")
                continue
            if meta is None:
                (rep.warn if r.get("verification") == "UNVERIFIED" else rep.err)(
                    f"{r['key']}: identificador no resuelve en la fuente")
                continue
            s = max(title_sim(r["title"], meta["title"]), title_sim(r["title"], meta.get("raw_title", "")))
            if s < 0.8:
                rep.err(f"{r['key']}: título no coincide (sim={s:.2f})")
    return rep.show()


# ----------------------------------------------------------------------------- add-paper
def bibtex_escape(s: str) -> str:
    return (s or "").replace("{", "").replace("}", "").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")


BIBTYPE = {"book": "book", "monograph": "book", "edited-book": "book", "reference-book": "book",
           "book-chapter": "incollection", "book-part": "incollection", "proceedings-article": "inproceedings",
           "journal-article": "article", "posted-content": "misc", "preprint": "misc", "web": "misc"}


def bib_entry(row: dict) -> str:
    typ = BIBTYPE.get(row.get("type", ""), "misc")
    f = {"title": "{" + bibtex_escape(row["title"]) + "}",
         "author": bibtex_escape(" and ".join(a for a in (row.get("authors") or "").split("; ") if a)),
         "year": row.get("year", "")}
    if row.get("venue"):
        field = {"article": "journal", "inproceedings": "booktitle", "incollection": "booktitle",
                 "book": "publisher"}.get(typ, "howpublished")
        f[field] = bibtex_escape(row["venue"])
    for k in ("doi", "isbn"):
        if row.get(k):
            f[k] = row[k]
    if row.get("arxiv"):
        f["eprint"], f["archiveprefix"] = row["arxiv"], "arXiv"
    if row.get("url"):
        f["url"] = row["url"]
    f["note"] = f"verification={row.get('verification')}; access={row.get('access')}"
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f.items() if v)
    return f"@{typ}{{{row['key']},\n{body}\n}}\n"


def write_manifest(rows):
    with MANIFEST.open("w", encoding="utf-8", newline="") as f:  # csv gestiona fin de línea
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(rows)


def cmd_add_paper(args) -> bool:
    rep = Report("add-paper")
    rows = read_manifest()
    today = dt.date.today().isoformat()
    row = {k: "" for k in MANIFEST_FIELDS}
    if args.doi:
        meta = crossref(args.doi)
        if not meta:
            rep.err(f"DOI {args.doi} no resuelve en Crossref; regístralo a mano como UNVERIFIED")
            return rep.show()
        m = meta["msg"]
        auth = [(a.get("family") or a.get("name", "")) + (", " + a["given"] if a.get("given") else "")
                for a in m.get("author", [])]
        year = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
        row.update(doi=args.doi.lower(), title=meta["title"], authors="; ".join(auth), year=str(year or ""),
                   venue=(m.get("container-title") or [m.get("publisher", "")])[0], type=m.get("type", ""),
                   verified_via="crossref")
    elif args.arxiv:
        meta = arxiv_meta(args.arxiv)
        if not meta:
            rep.err(f"arXiv {args.arxiv} no resuelve")
            return rep.show()
        auth = re.findall(r"<keyname>(.*?)</keyname>", meta["raw"])
        year = re.search(r"<created>(\d{4})", meta["raw"])
        row.update(arxiv=args.arxiv, title=meta["title"], authors="; ".join(auth),
                   year=year.group(1) if year else "", venue="arXiv", type="preprint",
                   verified_via="arxiv-oai", license=meta.get("license") or "")
    else:
        rep.err("usa --doi o --arxiv")
        return rep.show()
    first = (row["authors"].split(",")[0] or "anon")
    key = args.key or (re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode().lower()) + row["year"])
    while any(r["key"] == key for r in rows):
        key += "b"
    row.update(key=key, id=f"PAP-{key}", verification="VERIFIED", verified_on=today, title_similarity="1.00",
               access=args.access, redistributable="no", tags=" ".join(args.tags or []),
               card=f"bibliography/processed/{key}.md")
    rows.append(row)
    write_manifest(rows)
    with BIB.open("a", encoding="utf-8") as f:
        f.write("\n" + bib_entry(row))
    card = PROCESSED / f"{key}.md"
    fm = {"id": row["id"], "type": "paper", "title": row["title"], "status": "draft", "updated": today,
          "bibkey": key, "verification": "VERIFIED", "access": args.access, "tags": args.tags or [],
          "refs": [key]}
    card.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n"
                    "## Resumen propio\nPENDIENTE.\n\n## Relevancia para la plataforma\nPENDIENTE.\n",
                    encoding="utf-8", newline="\n")
    print(f"añadido {key}: {row['title'][:70]} → ejecuta `kb.py index`")
    return rep.show()


# ----------------------------------------------------------------------------- check
def cmd_check(args) -> bool:
    args.check = True
    args.online = False
    oks = [cmd_validate(args), cmd_links(args), cmd_dupes(args), cmd_orphans(args), cmd_summary(args),
           cmd_index(args), cmd_dois(args)]
    print("\nRESULTADO:", "OK" if all(oks) else "FALLO")
    return all(oks)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "links", "dupes", "orphans", "summary", "check"):
        sp.add_parser(name)
    pi = sp.add_parser("index")
    pi.add_argument("--check", action="store_true")
    pd = sp.add_parser("dois")
    pd.add_argument("--online", action="store_true")
    pd.add_argument("--sample", type=int, default=0)
    pa = sp.add_parser("add-paper")
    pa.add_argument("--doi")
    pa.add_argument("--arxiv")
    pa.add_argument("--key")
    pa.add_argument("--tags", nargs="*")
    pa.add_argument("--access", default="PAYWALLED", choices=["OA", "OA-LINK", "PAYWALLED", "WEB"])
    args = ap.parse_args(argv)
    args.check = getattr(args, "check", False)
    args.online = getattr(args, "online", False)
    args.sample = getattr(args, "sample", 0)
    fn = {"validate": cmd_validate, "links": cmd_links, "dupes": cmd_dupes, "orphans": cmd_orphans,
          "summary": cmd_summary, "index": cmd_index, "dois": cmd_dois, "add-paper": cmd_add_paper,
          "check": cmd_check}[args.cmd]
    return 0 if fn(args) else 1


if __name__ == "__main__":
    sys.exit(main())
