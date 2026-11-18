"""File storage. On disk (BP_STORAGE_DIR) or inside the database (BP_STORAGE=db, the default with Postgres)."""
import os

from . import config


def _abs(rel: str) -> str:
    return os.path.join(config.storage_dir(), rel)


def _use_db() -> bool:
    return config.storage_mode() == "db"


def _scope(sess):
    """Use the caller's session when given (no commit, caller owns the transaction), else open our own."""
    from . import db
    return (sess, False) if sess is not None else (db.session(), True)


def save(rel: str, data: bytes, sess=None) -> str:
    if _use_db():
        from . import db
        s, own = _scope(sess)
        try:
            row = s.get(db.StoredFile, rel)
            if row:
                row.data = data
            else:
                s.add(db.StoredFile(path=rel, data=data))
            s.commit() if own else s.flush()
        finally:
            s.close() if own else None
        return rel
    p = _abs(rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    return rel


def read(rel: str, sess=None) -> bytes:
    if _use_db():
        from . import db
        s, own = _scope(sess)
        try:
            row = s.get(db.StoredFile, rel)
            if row is None:
                raise FileNotFoundError(rel)
            return bytes(row.data)
        finally:
            s.close() if own else None
    with open(_abs(rel), "rb") as f:
        return f.read()


def delete(rel: str, sess=None) -> None:
    if _use_db():
        from . import db
        s, own = _scope(sess)
        try:
            row = s.get(db.StoredFile, rel)
            if row:
                s.delete(row)
                s.commit() if own else s.flush()
        finally:
            s.close() if own else None
        return
    try:
        os.remove(_abs(rel))
    except FileNotFoundError:
        pass
