"""First-boot seeding + path repair, so the app works on any host (Render, Docker, laptop).

Why this exists
---------------
* The demo database is built on a developer machine and stores *absolute* file paths
  (e.g. /home/user/evidenceos/data/originals/x.pdf).  On a new host those paths do not exist,
  so page images, evidence crops and report downloads fail.  `repair_paths` re-points them.
* On Render the container filesystem starts empty.  `seed_if_empty` copies the bundled demo corpus
  (seed/) into EVIDENCEOS_DATA_DIR the first time the app boots (and again whenever the disk is empty).
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from . import config

log = logging.getLogger("evidenceos.bootstrap")
SEED_DIR = Path(os.environ.get("EVIDENCEOS_SEED_DIR", config.ROOT_DIR / "seed"))


def _sqlite_file() -> Path | None:
    url = config.DATABASE_URL
    if not url.startswith("sqlite:///"):
        return None
    return Path(url[len("sqlite:///"):]).resolve()


def seed_if_empty() -> bool:
    """Copy the bundled demo corpus into the data dir if there is no database yet. Returns True if seeded."""
    dbp = _sqlite_file()
    seed_db = SEED_DIR / "evidenceos.db"
    if dbp is None or dbp.exists() or not seed_db.exists():
        return False
    log.info("empty data dir detected -> seeding demo corpus from %s", SEED_DIR)
    for sub, dst in (("originals", config.DATA_DIR / "originals"), ("reports", config.STORE_DIR / "reports")):
        src = SEED_DIR / sub
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file() and not (dst / f.name).exists():
                    shutil.copy2(f, dst / f.name)
    dbp.parent.mkdir(parents=True, exist_ok=True)
    tmp = dbp.with_suffix(".db.seeding")
    shutil.copy2(seed_db, tmp)
    os.replace(tmp, dbp)          # the DB file is written last and atomically: its existence marks "seeded"
    return True


def repair_paths(session) -> int:
    """Re-point absolute paths stored in the DB (documents, reports) to files that exist on this host."""
    from .db import Document, Report
    fixed = 0
    for d in session.query(Document).all():
        p = Path(d.storage_location or "")
        if p.exists():
            continue
        for cand in (config.DATA_DIR / "originals" / p.name,
                     config.STORE_DIR / "originals" / d.document_id / (d.original_filename or p.name)):
            if cand.exists():
                d.storage_location = str(cand)
                fixed += 1
                break
        else:
            log.warning("original file missing for %s (%s)", d.code, d.storage_location)
    for r in session.query(Report).all():
        p = Path(r.document_path or "")
        if p.exists():
            continue
        cand = config.STORE_DIR / "reports" / f"{r.report_id}.docx"
        if cand.exists():
            r.document_path = str(cand)
            fixed += 1
    if fixed:
        session.commit()
        log.info("repaired %d stored file paths", fixed)
    return fixed


def ensure_external_document(session, document_id: str, title: str, source: str, document_type: str = "external_dataset"):
    """Make sure a `documents` row exists for facts that come from an API/dataset rather than an uploaded PDF."""
    from .db import Document
    d = session.get(Document, document_id)
    if d is None:
        d = Document(document_id=document_id, code=document_id[:24], title=title, source=source, document_type=document_type,
                     status="validated", acl_level="public", page_count=0, is_scanned=False, meta={"external": True})
        session.add(d)
        session.flush()
    return d


def heal_orphan_documents(session) -> int:
    """Facts must never point at a missing document (cross-document validation would crash). Create stub rows for any that do."""
    from .db import Document, Fact
    known = {r[0] for r in session.query(Document.document_id).all()}
    missing = [r[0] for r in session.query(Fact.document_id).distinct().all() if r[0] and r[0] not in known]
    for mid in missing:
        ensure_external_document(session, mid, f"External dataset {mid}", "external")
    if missing:
        session.commit()
        log.warning("created stub document rows for orphan facts: %s", missing)
    return len(missing)
