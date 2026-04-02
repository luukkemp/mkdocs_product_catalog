import os
import re
import glob
import yaml
import tempfile
import shutil

from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File


# ── Static assets (written to separate files, never inlined into page content) ──

CATALOG_CSS = """\
.catalog-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 0;
}

.catalog-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 120px;
  min-height: 120px;
  padding: 12px 8px;
  border: 1px solid var(--md-default-fg-color--lightest, #e0e0e0);
  border-radius: 8px;
  background: var(--md-default-bg-color, #fff);
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.15s;
  text-align: center;
  gap: 8px;
  color: var(--md-default-fg-color, #333);
  font-size: 0.75rem;
  word-break: break-word;
}

.catalog-btn:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

.catalog-btn .catalog-icon {
  width: 56px;
  height: 56px;
  object-fit: contain;
  border-radius: 4px;
}

.catalog-btn .catalog-acronym {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--md-primary-fg-color, #1976d2);
  color: var(--md-primary-bg-color, #fff);
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.catalog-btn .catalog-label {
  line-height: 1.3;
}

/* Modal overlay */
.catalog-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 9999;
  align-items: center;
  justify-content: center;
}

.catalog-overlay.active {
  display: flex;
}

.catalog-modal {
  background: var(--md-default-bg-color, #fff);
  color: var(--md-default-fg-color, #333);
  border-radius: 12px;
  padding: 28px 32px;
  max-width: 560px;
  width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 8px 40px rgba(0,0,0,0.25);
}

.catalog-modal-close {
  position: absolute;
  top: 12px;
  right: 16px;
  font-size: 1.5rem;
  cursor: pointer;
  background: none;
  border: none;
  color: var(--md-default-fg-color, #333);
  line-height: 1;
  padding: 4px;
  border-radius: 4px;
}

.catalog-modal-close:hover {
  background: var(--md-default-fg-color--lightest, #e0e0e0);
}

.catalog-modal-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.catalog-modal-header .catalog-icon {
  width: 64px;
  height: 64px;
  object-fit: contain;
  border-radius: 4px;
  flex-shrink: 0;
}

.catalog-modal-header .catalog-acronym {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--md-primary-fg-color, #1976d2);
  color: var(--md-primary-bg-color, #fff);
  font-size: 1.5rem;
  font-weight: 700;
  flex-shrink: 0;
}

/* Modal title uses a div, not a heading, to avoid MkDocs search splitting the
   page into extra sections for every product. */
.catalog-modal-title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.3;
}

.catalog-modal-body p {
  margin: 6px 0;
  font-size: 0.9rem;
}

.catalog-modal-section {
  margin-bottom: 14px;
}

.catalog-modal-section-title {
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--md-default-fg-color--light, #666);
  margin-bottom: 4px;
}

.catalog-modal-section a {
  color: var(--md-typeset-a-color, #1976d2);
  word-break: break-all;
}

.catalog-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  background: var(--md-default-fg-color--lightest, #e8e8e8);
  font-size: 0.8rem;
  margin: 2px;
}

.catalog-kv {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  font-size: 0.85rem;
}

.catalog-kv dt {
  font-weight: 600;
  color: var(--md-default-fg-color--light, #666);
}

.catalog-kv dd {
  margin: 0;
}

/* Hidden search index: visible to the MkDocs search indexer but not rendered */
.catalog-search-index {
  display: none;
}
"""

CATALOG_JS = """\
function openCatalogModal(id) {
  document.getElementById('catalog-overlay-' + id).classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeCatalogModal(id) {
  document.getElementById('catalog-overlay-' + id).classList.remove('active');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.catalog-overlay.active').forEach(function(el) {
      el.classList.remove('active');
    });
    document.body.style.overflow = '';
  }
});
"""

_CSS_PATH = "assets/product-catalog.css"
_JS_PATH = "assets/product-catalog.js"

# Matches http(s):// or ftp:// URLs in a string
_URL_RE = re.compile(r'(https?://\S+|ftp://\S+)')

# Matches <!-- product-catalog: some/dir --> in rendered HTML.
# Python-Markdown may wrap a standalone comment in a <p> tag, so we handle both.
_CONTENT_TAG_RE = re.compile(
    r'(?:<p[^>]*>\s*)?<!--\s*product-catalog:\s*([^\s>]+)\s*-->(?:\s*</p>)?'
)


def make_acronym(title):
    words = re.findall(r"[A-Za-z0-9]+", title or "?")
    letters = [w[0].upper() for w in words if w]
    return "".join(letters[:3]) or "?"


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "item").lower()).strip("-")


def linkify(value):
    """Wrap any URLs in a string value with <a> tags."""
    return _URL_RE.sub(
        lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>',
        str(value),
    )


def load_products(yaml_dir):
    """Load and return all products from .yaml/.yml files in yaml_dir."""
    products = []
    if not os.path.isdir(yaml_dir):
        return products
    yaml_files = sorted(
        glob.glob(os.path.join(yaml_dir, "*.yaml"))
        + glob.glob(os.path.join(yaml_dir, "*.yml"))
    )
    for path in yaml_files:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            products.append(data)
    return products


def render_catalog_html(products, id_prefix=""):
    """Render catalog HTML: hidden search index + button grid + modals.

    No <style> or <script> tags are emitted here — those are loaded as
    separate static assets so the MkDocs search indexer never sees them.
    """
    buttons = []
    modals = []
    search_texts = []

    for idx, p in enumerate(products):
        title = p.get("title", f"Product {idx+1}")
        uid = f"{id_prefix}{slugify(title)}-{idx}"
        icon = p.get("icon", "")
        acronym = make_acronym(title)

        # --- Button ---
        if icon:
            icon_html = f'<img class="catalog-icon" src="{icon}" alt="{title}">'
        else:
            icon_html = f'<span class="catalog-acronym">{acronym}</span>'

        buttons.append(
            f'<button class="catalog-btn" onclick="openCatalogModal(\'{uid}\')">'
            f"  {icon_html}"
            f'  <span class="catalog-label">{title}</span>'
            f"</button>"
        )

        # --- Modal ---
        modal_icon_html = (
            f'<img class="catalog-icon" src="{icon}" alt="{title}">'
            if icon
            else f'<span class="catalog-acronym">{acronym}</span>'
        )

        description = p.get("description", "")
        url = p.get("url", "")
        documentation = p.get("documentation", "")
        repository = p.get("repository", "")
        owners = p.get("owners") or []
        metadata = p.get("metadata") or {}

        sections = []

        if description:
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Description</div>'
                f"<p>{description}</p>"
                f"</div>"
            )

        if url:
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">URL</div>'
                f'<p><a href="{url}" target="_blank" rel="noopener">{url}</a></p>'
                f"</div>"
            )

        if documentation:
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Documentation</div>'
                f'<p><a href="{documentation}" target="_blank" rel="noopener">{documentation}</a></p>'
                f"</div>"
            )

        if repository:
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Repository</div>'
                f'<p><a href="{repository}" target="_blank" rel="noopener">{repository}</a></p>'
                f"</div>"
            )

        if owners:
            tags = "".join(f'<span class="catalog-tag">{o}</span>' for o in owners)
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Owners</div>'
                f"<p>{tags}</p>"
                f"</div>"
            )

        if metadata:
            kv_items = "".join(
                f"<dt>{k}</dt><dd>{linkify(v)}</dd>" for k, v in metadata.items()
            )
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Metadata</div>'
                f'<dl class="catalog-kv">{kv_items}</dl>'
                f"</div>"
            )

        body = "\n".join(sections)

        # Use <div class="catalog-modal-title"> instead of <h2> so MkDocs
        # search does not treat each product as a new page section.
        modals.append(
            f'<div id="catalog-overlay-{uid}" class="catalog-overlay" '
            f"onclick=\"if(event.target===this)closeCatalogModal('{uid}')\">"
            f'<div class="catalog-modal">'
            f'  <button class="catalog-modal-close" onclick="closeCatalogModal(\'{uid}\')" aria-label="Close">&times;</button>'
            f'  <div class="catalog-modal-header">'
            f"    {modal_icon_html}"
            f'    <div class="catalog-modal-title">{title}</div>'
            f"  </div>"
            f'  <div class="catalog-modal-body">{body}</div>'
            f"</div>"
            f"</div>"
        )

        # Collect plain text so MkDocs search can find products by name/description
        search_texts.append(title)
        if description:
            search_texts.append(description)
        for o in owners:
            search_texts.append(str(o))

    grid = (
        '<div class="catalog-grid">\n'
        + "\n".join(buttons)
        + "\n</div>"
    )

    # This div is hidden by CSS but its text is indexed by MkDocs search
    search_index = (
        '<div class="catalog-search-index">\n'
        + "\n".join(f"<p>{t}</p>" for t in search_texts)
        + "\n</div>"
    )

    return search_index + "\n" + grid + "\n\n" + "\n".join(modals)


class ProductCatalogPlugin(BasePlugin):
    config_scheme = ()

    def __init__(self):
        super().__init__()
        self._tmpdir = None
        self._docs_dir = None

    def on_config(self, config):
        self._tmpdir = tempfile.mkdtemp(prefix="mkdocs_product_catalog_")
        self._docs_dir = config["docs_dir"]

        # Write static CSS and JS files to the temp dir
        css_path = os.path.join(self._tmpdir, _CSS_PATH)
        js_path = os.path.join(self._tmpdir, _JS_PATH)
        os.makedirs(os.path.dirname(css_path), exist_ok=True)

        with open(css_path, "w", encoding="utf-8") as f:
            f.write(CATALOG_CSS)
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(CATALOG_JS)

        # Register with MkDocs so it emits <link> and <script> tags on every page
        config["extra_css"].append(_CSS_PATH)
        config["extra_javascript"].append(_JS_PATH)

        return config

    def on_files(self, files, config):
        # Add the static CSS/JS assets
        for rel_path in (_CSS_PATH, _JS_PATH):
            files.append(File(
                path=rel_path,
                src_dir=self._tmpdir,
                dest_dir=config["site_dir"],
                use_directory_urls=config["use_directory_urls"],
            ))
        return files

    def on_page_content(self, html, page, config, files):
        """Replace <!-- product-catalog: dirname --> tags in the rendered HTML.

        Place the tag in any markdown page to embed a catalog there.
        dirname is resolved relative to docs_dir. Example:

            <!-- product-catalog: my-catalog -->

        Injection happens post-markdown so Python-Markdown never touches the
        catalog HTML.
        """
        def replace_tag(match):
            rel_dir = match.group(1).strip()
            yaml_dir = os.path.join(self._docs_dir, rel_dir)
            products = load_products(yaml_dir)
            return render_catalog_html(products, id_prefix=slugify(rel_dir) + "-")

        return _CONTENT_TAG_RE.sub(replace_tag, html)

    def on_post_build(self, config):
        if self._tmpdir and os.path.isdir(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
