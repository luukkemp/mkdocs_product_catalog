import glob
import html
import logging
import os

import yaml

from .utils import catalog_id_prefix, linkify, make_acronym, slugify

log = logging.getLogger("mkdocs.plugins.product-catalog")


def load_products(yaml_dir: str) -> list:
    """Load all product dicts from .yaml/.yml files in yaml_dir, sorted by filename."""
    products = []
    if not os.path.isdir(yaml_dir):
        return products
    yaml_files = sorted(
        glob.glob(os.path.join(yaml_dir, "*.yaml"))
        + glob.glob(os.path.join(yaml_dir, "*.yml"))
    )
    for path in yaml_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            log.warning(f"product-catalog: skipping malformed YAML file {path}: {exc}")
            continue
        except OSError as exc:
            log.warning(f"product-catalog: cannot read {path}: {exc}")
            continue
        if isinstance(data, dict):
            products.append(data)
        else:
            log.debug(f"product-catalog: skipping {path} — expected a YAML mapping, got {type(data).__name__}")
    return products


def render_catalog_html(products: list, id_prefix: str = "") -> str:
    """Render catalog HTML: hidden search index + button grid + modals.

    No <style> or <script> tags are emitted — those are loaded as separate
    static assets so the MkDocs search indexer never processes them.
    """
    buttons = []
    modals = []
    search_texts = []

    for idx, p in enumerate(products):
        raw_title = p.get("title", f"Product {idx + 1}")
        title = html.escape(str(raw_title))
        uid = f"{id_prefix}{slugify(raw_title)}-{idx}"
        icon = html.escape(str(p.get("icon", "")))
        acronym = make_acronym(raw_title)

        # --- Button ---
        if icon:
            icon_html = f'<img class="catalog-icon" src="{icon}" alt="{title}">'
        else:
            icon_html = f'<span class="catalog-acronym">{acronym}</span>'

        anchor_id = slugify(raw_title)
        buttons.append(
            f'<div id="{anchor_id}">'
            f'<button class="catalog-btn" onclick="openCatalogModal(\'{uid}\')">'
            f"  {icon_html}"
            f'  <span class="catalog-label">{title}</span>'
            f"</button>"
            f"</div>"
        )

        # --- Modal ---
        modal_icon_html = (
            f'<img class="catalog-icon" src="{icon}" alt="{title}">'
            if icon
            else f'<span class="catalog-acronym">{acronym}</span>'
        )

        raw_description = p.get("description", "")
        description = html.escape(str(raw_description)) if raw_description else ""
        raw_url = p.get("url", "")
        url = html.escape(str(raw_url)) if raw_url else ""
        documentation = p.get("documentation") or []
        repository = p.get("repository") or []
        owners = p.get("owners") or []
        metadata = p.get("metadata") or {}

        left_sections = []
        right_sections = []

        if description:
            left_sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Description</div>'
                f"<p>{description}</p>"
                f"</div>"
            )

        if url:
            left_sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">URL</div>'
                f'<p><a href="{url}" target="_blank" rel="noopener">{url}</a></p>'
                f"</div>"
            )

        repo_html = _render_links(repository, "Repository")
        if repo_html:
            right_sections.append(repo_html)

        doc_html = _render_links(documentation, "Documentation")
        if doc_html:
            right_sections.append(doc_html)

        if owners:
            tags = "".join(
                f'<span class="catalog-tag">{html.escape(str(o))}</span>'
                for o in owners
            )
            left_sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Owners</div>'
                f"<p>{tags}</p>"
                f"</div>"
            )

        if metadata:
            kv_items = "".join(
                f"<dt>{html.escape(str(k))}</dt>"
                f"<dd>{linkify(html.escape(str(v)))}</dd>"
                for k, v in metadata.items()
            )
            left_sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Metadata</div>'
                f'<dl class="catalog-kv">{kv_items}</dl>'
                f"</div>"
            )

        if right_sections:
            body = (
                f'<div class="catalog-modal-column">' + "\n".join(left_sections) + "</div>"
                + f'<div class="catalog-modal-column">' + "\n".join(right_sections) + "</div>"
            )
        else:
            body = f'<div class="catalog-modal-column">' + "\n".join(left_sections) + "</div>"

        modals.append(
            f'<div id="catalog-overlay-{uid}" class="catalog-overlay"'
            f" onclick=\"if(event.target===this)closeCatalogModal('{uid}')\">"
            f'<div class="catalog-modal">'
            f'  <div class="catalog-modal-actions">'
            f'    <button class="catalog-modal-share" onclick="copyCatalogLink(this)" aria-label="Copy link"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></svg></button>'
            f'    <button class="catalog-modal-close" onclick="closeCatalogModal(\'{uid}\')" aria-label="Close">&times;</button>'
            f'  </div>'
            f'  <div class="catalog-modal-header">'
            f"    {modal_icon_html}"
            f'    <div class="catalog-modal-title">{title}</div>'
            f"  </div>"
            f'  <div class="catalog-modal-body">{body}</div>'
            f"</div>"
            f"</div>"
        )

        search_texts.append(raw_title)
        if raw_description:
            search_texts.append(raw_description)
        for o in owners:
            search_texts.append(str(o))

    grid = '<div class="catalog-grid">\n' + "\n".join(buttons) + "\n</div>"
    search_index = (
        '<div class="catalog-search-index">\n'
        + "\n".join(f"<p>{html.escape(t)}</p>" for t in search_texts)
        + "\n</div>"
    )
    return search_index + "\n" + grid + "\n\n" + "\n".join(modals)


def _render_links(value, section_title: str) -> str:
    """Render a documentation or repository field (string or list) as HTML section."""
    if not value:
        return ""

    items_html = []

    if isinstance(value, str):
        escaped = html.escape(value)
        items_html.append(
            f'<div class="catalog-doc-link">'
            f'<a href="{escaped}" target="_blank" rel="noopener">{escaped}</a>'
            f"</div>"
        )
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                item_url = html.escape(str(item.get("url", "")))
                item_title = html.escape(str(item.get("title", item_url)))
                item_desc = html.escape(str(item.get("description", "")))
                if not item_url:
                    continue
                entry = (
                    f'<div class="catalog-doc-link">'
                    f'<a href="{item_url}" target="_blank" rel="noopener">{item_title}</a>'
                )
                if item_desc:
                    entry += f'<div class="catalog-doc-description">{item_desc}</div>'
                entry += "</div>"
                items_html.append(entry)
            elif isinstance(item, str) and item:
                escaped = html.escape(item)
                items_html.append(
                    f'<div class="catalog-doc-link">'
                    f'<a href="{escaped}" target="_blank" rel="noopener">{escaped}</a>'
                    f"</div>"
                )

    if not items_html:
        return ""

    return (
        f'<div class="catalog-modal-section">'
        f'<div class="catalog-modal-section-title">{section_title}</div>'
        + "\n".join(items_html)
        + "</div>"
    )
