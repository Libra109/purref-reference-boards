"""PureRef 2.x .pur core — Python (stdlib-only) port of LazyRef purcore.

Mirrors the Rust implementation's read/write paths:
  container  : 108-byte header + thumbnail chunk, spliced SQLite DB, md5 checksum
  scene_db   : 7-table SQLite schema; blob columns stored as TEXT (latin-1 quirk)
  blobs      : QDataStream QVariant envelopes (Qt5 type ids, stream version 19)

Only the standard library is used (sqlite3, hashlib, struct).
"""

import hashlib
import os
import sqlite3
import struct
import tempfile

# ------------------------------------------------------------------ checksum

def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()

def md5_hex_from(data: bytes, offset: int) -> str:
    return hashlib.md5(data[offset:]).hexdigest()

# ------------------------------------------------------------------ blobs

TYPE_TRANSFORM = 80        # Qt5 QTransform
TYPE_QRECTF = 20           # Qt5 QRectF
TYPE_USER = 1024           # QMetaType::User (named types)
TYPE_USER_QT6 = 65536      # accepted on read, never written


def bytes_to_stored_text(b: bytes) -> str:
    """Serialized bytes -> TEXT column value (QString::fromLatin1)."""
    return b.decode("latin-1")


def stored_text_to_bytes(s: str) -> bytes:
    """TEXT column value -> serialized bytes ('?' for chars > 0xFF)."""
    return bytes((ord(c) if ord(c) <= 0xFF else 0x3F) for c in s)


def encode_variant(type_id: int, payload: bytes, name: str | None, is_null: int = 0) -> bytes:
    out = bytearray()
    out += struct.pack(">I", type_id)
    out += struct.pack(">b", is_null)
    if name is not None:
        nb = name.encode("utf-8") + b"\x00"
        out += struct.pack(">I", len(nb))
        out += nb
    out += payload
    return bytes(out)


def decode_variant(b: bytes):
    """Returns (type_id, name, is_null, payload)."""
    type_id = struct.unpack_from(">I", b, 0)[0]
    is_null = struct.unpack_from(">b", b, 4)[0]
    off = 5
    name = None
    if type_id in (TYPE_USER, TYPE_USER_QT6):
        n = struct.unpack_from(">I", b, off)[0]
        off += 4
        assert 1 <= n <= len(b) - off, f"bad variant name length {n}"
        name = b[off:off + n - 1].decode("utf-8", errors="replace")
        off += n
    return type_id, name, is_null, b[off:]


# QTransform: tuple of 9 floats (m11 m12 m13 m21 m22 m23 m31 m32 m33)
def encode_transform(t) -> bytes:
    return encode_variant(TYPE_TRANSFORM, struct.pack(">9d", *t), None)


def decode_transform(b: bytes):
    type_id, name, is_null, p = decode_variant(b)
    assert type_id == TYPE_TRANSFORM and name is None and is_null == 0 and len(p) == 72, \
        f"not a QTransform variant (type={type_id} name={name!r} null={is_null} payload={len(p)})"
    return struct.unpack(">9d", p)


# QRectF: tuple (x, y, w, h)
def encode_rect_f(r) -> bytes:
    return encode_variant(TYPE_QRECTF, struct.pack(">4d", *r), None)


def decode_rect_f(b: bytes):
    type_id, name, is_null, p = decode_variant(b)
    assert type_id == TYPE_QRECTF and name is None and is_null == 0 and len(p) == 32, \
        f"not a QRectF variant (type={type_id} name={name!r} null={is_null} payload={len(p)})"
    return struct.unpack(">4d", p)


# BigRational: dict(num_sign, num_limbs, den_sign, den_limbs); limbs are u32 LE-order values
def encode_big_rational(r) -> bytes:
    p = bytearray()
    p += struct.pack(">i", r["num_sign"])
    p += struct.pack(">Q", len(r["num_limbs"]))
    for limb in r["num_limbs"]:
        p += struct.pack(">I", limb)
    p += struct.pack(">i", r["den_sign"])
    p += struct.pack(">Q", len(r["den_limbs"]))
    for limb in r["den_limbs"]:
        p += struct.pack(">I", limb)
    return encode_variant(TYPE_USER, bytes(p), "BigRational")


def decode_big_rational(b: bytes):
    type_id, name, is_null, p = decode_variant(b)
    assert type_id == TYPE_USER and name == "BigRational" and is_null == 0, \
        f"not a BigRational variant (type={type_id} name={name!r} null={is_null})"
    off = 0
    num_sign = struct.unpack_from(">i", p, off)[0]; off += 4
    num_limbs, off = _read_limbs(p, off)
    den_sign = struct.unpack_from(">i", p, off)[0]; off += 4
    den_limbs, off = _read_limbs(p, off)
    assert off == len(p), "trailing bytes in BigRational payload"
    return {"num_sign": num_sign, "num_limbs": num_limbs,
            "den_sign": den_sign, "den_limbs": den_limbs}


def _read_limbs(p: bytes, off: int):
    n = struct.unpack_from(">Q", p, off)[0]
    off += 8
    assert n <= 999, f"implausible BigRational limb count {n}"
    limbs = [struct.unpack_from(">I", p, off + 4 * i)[0] for i in range(n)]
    return limbs, off + 4 * n


# QPainterPath: dict(elements=[(type, x, y), ...], c_start, fill_rule)
def encode_path(path) -> bytes:
    elements = path["elements"]
    if not elements:
        return encode_variant(TYPE_USER, struct.pack(">I", 0), "QPainterPath")
    out = bytearray()
    out += struct.pack(">I", len(elements))
    for (etype, x, y) in elements:
        out += struct.pack(">i", etype)
        out += struct.pack(">d", x)
        out += struct.pack(">d", y)
    out += struct.pack(">i", path["c_start"])
    out += struct.pack(">i", path["fill_rule"])
    return encode_variant(TYPE_USER, bytes(out), "QPainterPath")


def decode_path(b: bytes):
    type_id, name, is_null, p = decode_variant(b)
    assert type_id == TYPE_USER and name == "QPainterPath" and is_null == 0, \
        f"not a QPainterPath variant (type={type_id} name={name!r} null={is_null})"
    n = struct.unpack_from(">i", p, 0)[0]
    assert 0 <= n <= (len(p) - 4) // 20, f"implausible QPainterPath element count {n}"
    off = 4
    elements = []
    for _ in range(n):
        etype = struct.unpack_from(">i", p, off)[0]
        x = struct.unpack_from(">d", p, off + 4)[0]
        y = struct.unpack_from(">d", p, off + 12)[0]
        elements.append((etype, x, y))
        off += 20
    if n > 0:
        c_start = struct.unpack_from(">i", p, off)[0]
        fill_rule = struct.unpack_from(">i", p, off + 4)[0]
    else:
        c_start, fill_rule = 0, 0
    return {"elements": elements, "c_start": c_start, "fill_rule": fill_rule}

# ------------------------------------------------------------------ container

FILE_VERSION = "2.1"
APP_VERSION = "2.1.3"
HEADER_LENGTH = 108


def _write_qstring(buf: bytearray, off: int, s: str) -> None:
    sb = s.encode("utf-16-be")
    struct.pack_into(">I", buf, off, len(sb))
    buf[off + 4:off + 4 + len(sb)] = sb


def _read_qstring(b: bytes, off: int):
    n = struct.unpack_from(">I", b, off)[0]
    s = b[off + 4:off + 4 + n].decode("utf-16-be", errors="replace")
    return s, 4 + n


def parse_header(b: bytes) -> dict:
    assert len(b) >= HEADER_LENGTH, f"file too small for a 2.x container: {len(b)} B"
    file_version, _ = _read_qstring(b, 0)
    color_a, color_b = struct.unpack_from(">hh", b, 10)
    db_size = struct.unpack_from(">q", b, 14)[0]
    app_version, _ = _read_qstring(b, 22)
    checksum_len = struct.unpack_from(">I", b, 36)[0]
    assert checksum_len == 64, f"unexpected checksum field length {checksum_len} (expected 64)"
    checksum = b[40:104].decode("utf-16-be", errors="replace")
    thumbnail_length = struct.unpack_from(">I", b, 104)[0]
    assert HEADER_LENGTH + thumbnail_length <= len(b), \
        f"bad thumbnail length {thumbnail_length} (file {len(b)} B)"
    return {
        "file_version": file_version,
        "color_a": color_a,
        "color_b": color_b,
        "db_size": db_size,
        "app_version": app_version,
        "checksum": checksum,
        "thumbnail_length": thumbnail_length,
        "chunk_length": HEADER_LENGTH + thumbnail_length,
    }


def detect_format(b: bytes) -> str:
    version, _ = _read_qstring(b, 0)
    try:
        major = int(version.split(".")[0])
    except ValueError:
        major = 0
    return "V2" if major >= 2 else "Legacy"


def verify_checksum(b: bytes) -> bool:
    assert len(b) >= HEADER_LENGTH, f"file too small: {len(b)} B"
    return md5_hex_from(b, 104) == parse_header(b)["checksum"]


def extract_thumbnail(b: bytes) -> bytes:
    h = parse_header(b)
    return b[HEADER_LENGTH:HEADER_LENGTH + h["thumbnail_length"]]


def extract_database(b: bytes) -> bytes:
    h = parse_header(b)
    db_size, c_len = h["db_size"], h["chunk_length"]
    assert 0 <= db_size and db_size >= c_len and db_size <= len(b) \
        and db_size + c_len == len(b), \
        f"inconsistent container: dbSize={db_size} cLen={c_len} file={len(b)} B"
    return b[db_size:] + b[c_len:db_size]


def build_container(db_bytes: bytes, thumbnail: bytes) -> bytes:
    db_size = len(db_bytes)
    c_len = HEADER_LENGTH + len(thumbnail)
    assert db_size >= c_len, \
        f"DB ({db_size} B) smaller than container chunk ({c_len} B) — cannot splice head copy"
    out = bytearray(db_size + c_len)  # zero-filled
    _write_qstring(out, 0, FILE_VERSION)
    # colorA / colorB stay 0
    struct.pack_into(">Q", out, 14, db_size)
    _write_qstring(out, 22, APP_VERSION)
    struct.pack_into(">I", out, 36, 64)  # checksum field byte length
    struct.pack_into(">I", out, 104, len(thumbnail))
    out[HEADER_LENGTH:HEADER_LENGTH + len(thumbnail)] = thumbnail
    out[c_len:db_size] = db_bytes[c_len:db_size]          # DB after the chunk
    out[db_size:db_size + c_len] = db_bytes[:c_len]       # head copy at the tail
    checksum = md5_hex_from(bytes(out), 104)
    assert len(checksum) == 32
    for i, ch in enumerate(checksum.encode("ascii")):
        out[40 + 2 * i + 1] = ch  # UTF-16BE: high bytes stay 0
    return bytes(out)

# ------------------------------------------------------------------ scene_db

APPLICATION_ID = 940753918   # 0x3812c3fe
USER_VERSION = 200101        # 0x30da5

SCHEMA = [
    "CREATE TABLE images (width INTEGER,checksum TEXT,format TEXT,source TEXT,height INTEGER,data BLOB,source_type INTEGER,origin TEXT,id INTEGER PRIMARY KEY);",
    "CREATE TABLE items_groups (lock_mode INTEGER,background_color TEXT,id INTEGER PRIMARY KEY);",
    "CREATE TABLE items_drawings (strokes BLOB,id INTEGER PRIMARY KEY);",
    "CREATE TABLE items_notes (fixed_size TEXT,background_color TEXT,text_color TEXT,style INTEGER,text TEXT,id INTEGER PRIMARY KEY);",
    "CREATE TABLE items_images (playback_speed REAL,playback_frame INTEGER,playback_state INTEGER,image_bounds BLOB,image_transform BLOB,flags INTEGER,image INTEGER,id INTEGER PRIMARY KEY);",
    "CREATE TABLE items (comment INTEGER,opacity REAL,z REAL,locked INTEGER,parent INTEGER,sort_order BLOB,transform BLOB,name TEXT,id INTEGER PRIMARY KEY);",
    "CREATE TABLE metadata (thumbnail BLOB,saved INTEGER,last_load_checksum TEXT,last_load_path TEXT,last_save_path TEXT,vertical_scroll INTEGER,scene_rect TEXT,view_transform TEXT,application_version TEXT,horizontal_scroll INTEGER,id INTEGER PRIMARY KEY);",
]


def _stored(blob: bytes | None):
    return None if blob is None else bytes_to_stored_text(blob)


def create_schema(conn: sqlite3.Connection) -> None:
    # isolation_level=None (autocommit): each statement commits on its own,
    # mirroring the Rust create_schema (pragma batch, per-DDL execute, id pragmas).
    for pragma in ("PRAGMA encoding = 'UTF-8'",
                   "PRAGMA journal_mode = DELETE",
                   "PRAGMA synchronous = EXTRA",
                   "PRAGMA auto_vacuum = 1"):
        conn.execute(pragma)
    for ddl in SCHEMA:
        conn.execute(ddl)
    conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    conn.execute(f"PRAGMA user_version = {USER_VERSION}")


def write_scene(conn: sqlite3.Connection, scene: dict) -> None:
    """Three transactions, mirroring purcore scene_db::write."""
    conn.execute("BEGIN")
    for i in scene["images"]:
        conn.execute(
            "INSERT INTO images(id,width,height,checksum,format,source,source_type,origin,data)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (i["id"], i["width"], i["height"], i["checksum"], i["format"], i["source"],
             i["source_type"], i["origin"], i["data"]))
    conn.execute("COMMIT")

    conn.execute("BEGIN")
    for it in scene["items"]:
        conn.execute(
            "INSERT INTO items(id,name,transform,sort_order,z,opacity,parent,locked,comment)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (it["id"], it["name"],
             _stored(encode_transform(it["transform"])) if it["transform"] is not None else None,
             _stored(encode_big_rational(it["sort_order"])) if it["sort_order"] is not None else None,
             it["z"], it["opacity"], it["parent"], it["locked"], it["comment"]))
    for ii in scene["items_images"]:
        conn.execute(
            "INSERT INTO items_images(id,image,image_transform,image_bounds,flags,"
            "playback_state,playback_frame,playback_speed) VALUES(?,?,?,?,?,?,?,?)",
            (ii["id"], ii["image"],
             _stored(encode_transform(ii["image_transform"])) if ii["image_transform"] is not None else None,
             _stored(encode_path(ii["image_bounds"])) if ii["image_bounds"] is not None else None,
             ii["flags"], ii["playback_state"], ii["playback_frame"], ii["playback_speed"]))
    for g in scene["groups"]:
        conn.execute("INSERT INTO items_groups(id,background_color,lock_mode) VALUES(?,?,?)",
                     (g["id"], g["background_color"], g["lock_mode"]))
    for d in scene["drawings"]:
        conn.execute("INSERT INTO items_drawings(id,strokes) VALUES(?,?)",
                     (d["id"], d["strokes"]))
    for n in scene["notes"]:
        conn.execute(
            "INSERT INTO items_notes(id,text,background_color,text_color,style,fixed_size)"
            " VALUES(?,?,?,?,?,?)",
            (n["id"], n["text"], n["background_color"], n["text_color"], n["style"],
             n["fixed_size"]))
    conn.execute("COMMIT")

    m = scene["metadata"]
    if m is not None:
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO metadata(id,thumbnail,saved,last_load_checksum,last_load_path,"
            "last_save_path,vertical_scroll,scene_rect,view_transform,application_version,"
            "horizontal_scroll) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (m["id"], m["thumbnail"], m["saved"], m["last_load_checksum"], m["last_load_path"],
             m["last_save_path"], m["vertical_scroll"],
             _stored(encode_rect_f(m["scene_rect"])) if m["scene_rect"] is not None else None,
             _stored(encode_transform(m["view_transform"])) if m["view_transform"] is not None else None,
             m["application_version"], m["horizontal_scroll"]))
        conn.execute("COMMIT")


def _as_blob(v):
    if v is None:
        return None
    if isinstance(v, str):
        b = stored_text_to_bytes(v)
    else:
        b = bytes(v)
    return b if b else None


def read_scene(conn: sqlite3.Connection) -> dict:
    def rows(sql):
        return conn.execute(sql).fetchall()

    scene = {"images": [], "items": [], "items_images": [], "groups": [],
             "drawings": [], "notes": [], "metadata": None}
    for r in rows("SELECT id,width,height,checksum,format,source,source_type,origin,data"
                  " FROM images ORDER BY id"):
        scene["images"].append({
            "id": r[0], "width": r[1], "height": r[2], "checksum": r[3], "format": r[4],
            "source": r[5], "source_type": r[6], "origin": r[7], "data": _as_blob(r[8])})
    for r in rows("SELECT id,name,transform,sort_order,z,opacity,parent,locked,comment"
                  " FROM items ORDER BY id"):
        tb, sb = _as_blob(r[2]), _as_blob(r[3])
        scene["items"].append({
            "id": r[0], "name": r[1],
            "transform": decode_transform(tb) if tb else None,
            "sort_order": decode_big_rational(sb) if sb else None,
            "z": r[4], "opacity": r[5],
            "parent": r[6] if r[6] is not None else -1,
            "locked": r[7], "comment": r[8]})
    for r in rows("SELECT id,image,image_transform,image_bounds,flags,playback_state,"
                  "playback_frame,playback_speed FROM items_images ORDER BY id"):
        tb, pb = _as_blob(r[2]), _as_blob(r[3])
        scene["items_images"].append({
            "id": r[0], "image": r[1],
            "image_transform": decode_transform(tb) if tb else None,
            "image_bounds": decode_path(pb) if pb else None,
            "flags": r[4], "playback_state": r[5], "playback_frame": r[6],
            "playback_speed": r[7]})
    for r in rows("SELECT id,background_color,lock_mode FROM items_groups ORDER BY id"):
        scene["groups"].append({"id": r[0], "background_color": r[1], "lock_mode": r[2]})
    for r in rows("SELECT id,strokes FROM items_drawings ORDER BY id"):
        scene["drawings"].append({"id": r[0], "strokes": _as_blob(r[1])})
    for r in rows("SELECT id,text,background_color,text_color,style,fixed_size"
                  " FROM items_notes ORDER BY id"):
        scene["notes"].append({"id": r[0], "text": r[1], "background_color": r[2],
                                "text_color": r[3], "style": r[4], "fixed_size": r[5]})
    meta_rows = rows("SELECT id,thumbnail,saved,last_load_checksum,last_load_path,"
                     "last_save_path,vertical_scroll,scene_rect,view_transform,"
                     "application_version,horizontal_scroll FROM metadata ORDER BY id LIMIT 1")
    if meta_rows:
        r = meta_rows[0]
        sb, tb = _as_blob(r[7]), _as_blob(r[8])
        scene["metadata"] = {
            "id": r[0], "thumbnail": _as_blob(r[1]), "saved": r[2],
            "last_load_checksum": r[3], "last_load_path": r[4], "last_save_path": r[5],
            "vertical_scroll": r[6],
            "scene_rect": decode_rect_f(sb) if sb else None,
            "view_transform": decode_transform(tb) if tb else None,
            "application_version": r[9], "horizontal_scroll": r[10]}
    return scene

# ------------------------------------------------------------------ purfile

# SQLite version stamped by the reference writer (PureRef 2.1.3 bundles 3.45.3).
REFERENCE_SQLITE_VERSION = 3045003


def write_pur(scene: dict, thumbnail: bytes) -> bytes:
    """Scene -> complete .pur file bytes (mirrors purcore PurFile::write_bytes)."""
    fd, scratch = tempfile.mkstemp(suffix=".db", prefix="purcore-py-write-")
    os.close(fd)
    os.unlink(scratch)  # sqlite creates it fresh
    try:
        conn = sqlite3.connect(scratch, isolation_level=None)
        try:
            create_schema(conn)
            write_scene(conn, scene)
        finally:
            conn.close()
        with open(scratch, "rb") as f:
            db_bytes = bytearray(f.read())
    finally:
        if os.path.exists(scratch):
            os.unlink(scratch)
    struct.pack_into(">I", db_bytes, 96, REFERENCE_SQLITE_VERSION)
    return build_container(bytes(db_bytes), thumbnail)


def read_pur(data: bytes, verify: bool = True) -> dict:
    """Complete .pur file bytes -> Scene (mirrors purcore PurFile::read_bytes)."""
    assert detect_format(data) == "V2", "legacy v1.x .pur: not a v2 Scene"
    if verify:
        assert verify_checksum(data), "container checksum mismatch (md5(file[104:]))"
    db_bytes = extract_database(data)
    fd, scratch = tempfile.mkstemp(suffix=".db", prefix="purcore-py-read-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(db_bytes)
        conn = sqlite3.connect(f"file:{scratch}?mode=ro", uri=True)
        try:
            return read_scene(conn)
        finally:
            conn.close()
    finally:
        os.unlink(scratch)
