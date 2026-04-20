import re

_URL_RE = re.compile(r'(https?://\S+|ftp://\S+)')


def make_acronym(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title or "?")
    letters = [w[0].upper() for w in words if w]
    return "".join(letters[:3]) or "?"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "item").lower()).strip("-")


def catalog_id_prefix(catalog_dir: str) -> str:
    """Return the id_prefix used for modal IDs given a catalog directory path.

    This is the single source of truth used by both HTML rendering and nav
    link generation to ensure they always produce matching modal IDs.
    """
    return slugify(catalog_dir) + "-"


def linkify(value: str) -> str:
    """Wrap URLs in a string with <a> tags. Input must already be HTML-escaped."""
    return _URL_RE.sub(
        lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>',
        str(value),
    )
