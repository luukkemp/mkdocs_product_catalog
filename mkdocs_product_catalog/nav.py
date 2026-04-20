"""Navigation integration for mkdocs-product-catalog.

Runs during on_nav (before on_page_content). Scans markdown source files for
catalog tags, resolves product YAMLs, and adds nav sections that deep-link
directly into each product's modal.

Key design:
- Uses page.url from MkDocs nav (computed correctly even with multirepo).
- Uses page.title from nav config (falls back to H1 extraction if not set).
- Processes ALL catalog tags per page via re.findall (not just the first).
- Groups all catalogs on the same page into a single nav section.
- Skips tags annotated with ``no-nav``.
- Deduplicates: if an existing nav item already points to a page, updates
  its children rather than appending a duplicate.
"""

import html as _html
import logging
import os
import re
from collections import defaultdict

from .catalog import load_products
from .utils import catalog_id_prefix, slugify

log = logging.getLogger("mkdocs.plugins.product-catalog")

# Matches <!-- product-catalog: some/dir --> and
# <!-- product-catalog: some/dir no-nav --> in raw markdown.
_TAG_RE = re.compile(
    r"<!--\s*product-catalog:\s*([^\s>]+)(\s+no-nav)?\s*-->"
)

# Matches the first H1 in a markdown file for title fallback.
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def build_catalog_nav(nav, files, config: dict, nav_enabled: bool = True):
    """Inject catalog service links into the MkDocs navigation.

    Args:
        nav: MkDocs Nav object (modified in-place and returned).
        files: MkDocs Files collection.
        config: MkDocs config dict.
        nav_enabled: If False, skip nav integration entirely.

    Returns:
        The (modified) nav object.
    """
    if not nav_enabled:
        return nav

    from mkdocs.structure.nav import Link, Section

    docs_dir = config["docs_dir"]
    page_map = _collect_pages(nav.items)

    # Accumulate: src_path -> list of (catalog_dir, products)
    page_catalogs: dict[str, list] = defaultdict(list)

    for file in files:
        if not (hasattr(file, "src_path") and file.src_path.endswith(".md")):
            continue

        file_path = getattr(file, "abs_src_path", None)
        if not file_path:
            file_path = os.path.join(docs_dir, file.src_path)
        if not os.path.isfile(file_path):
            continue

        try:
            content = open(file_path, encoding="utf-8").read()
        except OSError as exc:
            log.warning(f"product-catalog: cannot read {file_path}: {exc}")
            continue

        tags = _TAG_RE.findall(content)
        if not tags:
            continue

        for catalog_dir, no_nav_flag in tags:
            if no_nav_flag.strip():
                log.debug(f"product-catalog: skipping nav for '{catalog_dir}' (no-nav)")
                continue

            yaml_dir = _resolve_yaml_dir(catalog_dir, file_path, docs_dir)
            if not os.path.isdir(yaml_dir):
                log.warning(
                    f"product-catalog: catalog directory not found: {yaml_dir} "
                    f"(referenced from {file.src_path})"
                )
                continue

            products = load_products(yaml_dir)
            if not products:
                log.debug(f"product-catalog: no products found in {yaml_dir}")
                continue

            page_catalogs[file.src_path].append((catalog_dir, products))
            log.debug(
                f"product-catalog: found {len(products)} products in '{catalog_dir}' "
                f"on page {file.src_path}"
            )

    for src_path, catalogs in page_catalogs.items():
        page = page_map.get(src_path)
        if page is None:
            log.warning(
                f"product-catalog: page '{src_path}' has catalog tags but is not "
                f"present in nav — skipping nav integration for this page"
            )
            continue

        overview_url = page.url.rstrip("/")
        # page.title is set from nav: config if present; otherwise None at this
        # point (H1 is read later during page building).
        catalog_name = page.title or _extract_h1(
            getattr(page.file, "abs_src_path", None)
        ) or _title_from_src_path(src_path)

        # Collect all services from all catalogs on this page
        all_service_links = []
        for catalog_dir, products in catalogs:
            prefix = catalog_id_prefix(catalog_dir)
            for idx, p in enumerate(products):
                raw_title = p.get("title", f"Product {idx + 1}")
                modal_id = f"{prefix}{slugify(raw_title)}-{idx}"
                all_service_links.append(
                    Link(
                        title=_html.escape(str(raw_title)),
                        url=f"{overview_url}#modal-{modal_id}",
                    )
                )

        services_section = Section(title="Services", children=all_service_links)
        overview_link = Link(title="Overview", url=overview_url)
        catalog_section = Section(
            title=catalog_name,
            children=[overview_link, services_section],
        )

        container, existing_idx, existing_item = _find_nav_item_for_url(nav.items, overview_url)

        if existing_item is not None:
            catalog_section.title = existing_item.title or catalog_name
            if container is nav.items or len(container) > 1:
                # Keep the catalog wrapped in a named section when the page is at
                # root level (title would be lost otherwise) or when it has
                # siblings (bare Overview/Services would pollute the parent).
                container[existing_idx] = catalog_section
                log.debug(
                    f"product-catalog: replaced nav item '{existing_item.title}' "
                    f"with catalog section '{catalog_section.title}'"
                )
            else:
                # Page is the sole child of its parent section: splice Overview +
                # Services directly so the parent acts as the catalog section
                # without an extra wrapper layer.
                container[existing_idx : existing_idx + 1] = catalog_section.children
                log.debug(
                    f"product-catalog: injected catalog children into parent section "
                    f"(replacing '{existing_item.title}')"
                )
        else:
            nav.items.append(catalog_section)
            log.debug(f"product-catalog: added nav section '{catalog_name}'")

    return nav


# ── helpers ──────────────────────────────────────────────────────────────────

def _collect_pages(nav_items) -> dict:
    """Recursively collect src_path -> Page from nav items."""
    pages = {}
    for item in nav_items or []:
        if hasattr(item, "file") and item.file:
            pages[item.file.src_path] = item
        if hasattr(item, "children") and item.children:
            pages.update(_collect_pages(item.children))
    return pages


def _find_nav_item_for_url(nav_items, url: str):
    """Recursively find a nav item matching url at any depth.

    Returns (container, index, item) where container is the list that holds
    the found item, so the caller can replace it in-place at the right level.
    Returns (None, None, None) when not found.
    """
    for idx, item in enumerate(nav_items or []):
        if hasattr(item, "url") and item.url and item.url.rstrip("/") == url:
            return nav_items, idx, item
        if hasattr(item, "children") and item.children:
            result = _find_nav_item_for_url(item.children, url)
            if result[0] is not None:
                return result
    return None, None, None


def _resolve_yaml_dir(catalog_dir: str, file_path: str, docs_dir: str) -> str:
    """Resolve a catalog dir tag to an absolute filesystem path."""
    if catalog_dir.startswith("./") or catalog_dir.startswith("../"):
        current_dir = os.path.dirname(file_path)
        return os.path.normpath(os.path.join(current_dir, catalog_dir))
    return os.path.join(docs_dir, catalog_dir)


def _extract_h1(file_path: str | None) -> str | None:
    """Extract the first H1 heading from a markdown file, or None."""
    if not file_path or not os.path.isfile(file_path):
        return None
    try:
        content = open(file_path, encoding="utf-8").read()
        m = _H1_RE.search(content)
        return m.group(1).strip() if m else None
    except OSError:
        return None


def _title_from_src_path(src_path: str) -> str:
    """Derive a human-readable title from a file src_path as last resort."""
    name = os.path.splitext(os.path.basename(src_path))[0]
    return name.replace("_", " ").replace("-", " ").title()
