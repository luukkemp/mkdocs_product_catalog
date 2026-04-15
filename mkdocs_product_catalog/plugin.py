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
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 24px;
  padding: 24px 0;
  justify-content: center;
}

@media (min-width: 600px) {
  .catalog-grid {
    grid-template-columns: repeat(2, minmax(200px, 1fr));
    max-width: 800px;
    margin: 0 auto;
  }
}

@media (min-width: 900px) {
  .catalog-grid {
    grid-template-columns: repeat(3, minmax(220px, 1fr));
    max-width: 1000px;
  }
}

.catalog-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 140px;
  padding: 16px 12px;
  border: 2px solid var(--md-default-fg-color--lightest, #e0e0e0);
  border-radius: 12px;
  background: var(--md-default-bg-color, #fff);
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
  gap: 10px;
  color: var(--md-default-fg-color, #333);
  font-size: 0.85rem;
  word-break: break-word;
  position: relative;
  overflow: hidden;
}

.catalog-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--md-primary-fg-color, #1976d2), transparent);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.catalog-btn:hover::before {
  transform: scaleX(1);
}

.catalog-btn:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  transform: translateY(-4px);
  border-color: var(--md-primary-fg-color, #1976d2);
}

.catalog-btn .catalog-icon {
  width: 60px;
  height: 60px;
  object-fit: contain;
  border-radius: 8px;
  transition: transform 0.2s ease;
}

.catalog-btn:hover .catalog-icon {
  transform: scale(1.05);
}

.catalog-btn .catalog-acronym {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--md-primary-fg-color, #1976d2);
  color: var(--md-primary-bg-color, #fff);
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);
}

.catalog-label {
  line-height: 1.4;
  font-weight: 500;
  padding: 4px 0;
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
  padding: 0;
  max-width: 1000px;
  width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 8px 40px rgba(0,0,0,0.25);
  display: flex;
  flex-direction: column;
}

.catalog-modal-header {
  padding: 24px 32px;
  border-bottom: 1px solid var(--md-default-fg-color--lightest, #e0e0e0);
  background: linear-gradient(135deg, var(--md-primary-fg-color, #1976d2) 0%, var(--md-primary-fg-color, #1976d2) 60%, var(--md-default-bg-color, #fff) 60%, var(--md-default-bg-color, #fff) 100%);
  color: var(--md-primary-bg-color, #fff);
}

.catalog-modal-header .catalog-modal-title {
  color: var(--md-primary-bg-color, #fff);
}



.catalog-modal-section {
  margin-bottom: 24px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border: 1px solid var(--md-default-fg-color--lightest, #e0e0e0);
}

.catalog-modal-section:last-child {
  margin-bottom: 0;
}

.catalog-modal-section-title {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--md-primary-fg-color, #1976d2);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--md-primary-fg-color, #1976d2);
  display: inline-block;
}

.catalog-modal-section-content {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--md-default-fg-color, #333);
}

.catalog-kv {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px 16px;
  font-size: 0.9rem;
  margin-top: 8px;
}

.catalog-kv dt {
  font-weight: 600;
  color: var(--md-default-fg-color--light, #666);
}

.catalog-kv dd {
  margin: 0;
}

.catalog-modal-body {
  padding: 24px 32px;
  max-height: calc(85vh - 120px);
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.catalog-modal-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.catalog-modal-section {
  margin-bottom: 24px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border: 1px solid var(--md-default-fg-color--lightest, #e0e0e0);
  break-inside: avoid;
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
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.3;
}

.catalog-modal-body {
  font-size: 0.8rem;
}

.catalog-modal-body p {
  margin: 6px 0;
  font-size: 0.8rem;
}

.catalog-modal-section {
  margin-bottom: 14px;
}

.catalog-modal-section-title {
  font-weight: 600;
  font-size: 0.7rem;
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
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--md-default-fg-color--lightest, #e8e8e8);
  font-size: 0.7rem;
  margin: 2px;
}

.catalog-doc-link {
  margin: 6px 0;
  padding: 6px 0;
  border-bottom: 1px solid var(--md-default-fg-color--lightest, #e0e0e0);
}

.catalog-doc-link:last-child {
  border-bottom: none;
}

.catalog-doc-link a {
  color: var(--md-typeset-a-color, #1976d2);
  font-weight: 400;
  word-break: break-all;
  font-size: 0.8rem;
}

.catalog-doc-description {
  font-size: 0.7rem;
  color: var(--md-default-fg-color--light, #666);
  margin-top: 2px;
  font-style: italic;
}

.catalog-kv {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  font-size: 0.75rem;
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

// Handle modal opening from navigation links with hash
window.addEventListener('DOMContentLoaded', function() {
  if (window.location.hash && window.location.hash.startsWith('#modal-')) {
    var modalId = window.location.hash.substring(7); // Remove '#modal-' prefix
    var modalElement = document.getElementById('catalog-overlay-' + modalId);
    if (modalElement) {
      setTimeout(function() {
        modalElement.classList.add('active');
        document.body.style.overflow = 'hidden';
      }, 100); // Small delay to ensure page is fully loaded
    }
  }
});

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

        # Add anchor ID for navigation linking
        anchor_id = slugify(title)
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

        description = p.get("description", "")
        url = p.get("url", "")
        documentation = p.get("documentation", [])  # Support both string and array
        repository = p.get("repository", [])  # Support both string and array
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

        # Handle single repository URL (backward compatibility) - only if no repository array
        if isinstance(repository, str) and repository:
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Repository</div>'
                f'<p><a href="{repository}" target="_blank" rel="noopener">{repository}</a></p>'
                f"</div>"
            )
        
        # Handle single documentation URL (backward compatibility) - only if no documentation array
        if isinstance(documentation, str) and documentation:
            sections.append(
                f'<div class="catalog-modal-section">'
                f'<div class="catalog-modal-section-title">Documentation</div>'
                f'<p><a href="{documentation}" target="_blank" rel="noopener">{documentation}</a></p>'
                f"</div>"
            )
        
        # Handle multiple repository links with optional descriptions
        if isinstance(repository, list) and repository:
            repos_html = []
            for repo in repository:
                if isinstance(repo, dict):
                    url = repo.get("url", "")
                    repo_title = repo.get("title", url)
                    description = repo.get("description", "")
                    if url:
                        repo_html = f'<div class="catalog-doc-link">'
                        repo_html += f'<a href="{url}" target="_blank" rel="noopener">{repo_title}</a>'
                        if description:
                            repo_html += f'<div class="catalog-doc-description">{description}</div>'
                        repo_html += '</div>'
                        repos_html.append(repo_html)
                elif isinstance(repo, str):
                    # Simple string URL (backward compatibility)
                    repos_html.append(f'<div class="catalog-doc-link"><a href="{repo}" target="_blank" rel="noopener">{repo}</a></div>')
            
            if repos_html:
                sections.append(
                    f'<div class="catalog-modal-section">'
                    f'<div class="catalog-modal-section-title">Repository</div>'
                    + '\n'.join(repos_html) +
                    f"</div>"
                )
        
        # Handle multiple documentation links with optional descriptions
        if isinstance(documentation, list) and documentation:
            links_html = []
            for link in documentation:
                if isinstance(link, dict):
                    url = link.get("url", "")
                    link_title = link.get("title", url)  # Fixed: renamed variable to avoid shadowing
                    description = link.get("description", "")
                    if url:
                        link_html = f'<div class="catalog-doc-link">'
                        link_html += f'<a href="{url}" target="_blank" rel="noopener">{link_title}</a>'
                        if description:
                            link_html += f'<div class="catalog-doc-description">{description}</div>'
                        link_html += '</div>'
                        links_html.append(link_html)
                elif isinstance(link, str):
                    # Simple string URL (backward compatibility)
                    links_html.append(f'<div class="catalog-doc-link"><a href="{link}" target="_blank" rel="noopener">{link}</a></div>')
            
            if links_html:
                sections.append(
                    f'<div class="catalog-modal-section">'
                    f'<div class="catalog-modal-section-title">Documentation</div>'
                    + '\n'.join(links_html) +
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

        # Organize sections into specific order
        left_column_sections = []  # For description, url, owners, metadata
        right_column_sections = []  # For repository, documentation
        
        # Categorize sections based on their content
        for section in sections:
            section_title = section.split('catalog-modal-section-title">')[1].split('<')[0] if 'catalog-modal-section-title' in section else ""
            
            # Left column sections (in order): Description, URL, Owners, Metadata
            if section_title in ['Description', 'URL', 'Owners', 'Metadata']:
                left_column_sections.append(section)
            # Right column sections (in order): Repository, Documentation
            elif section_title in ['Repository', 'Documentation']:
                right_column_sections.append(section)
        
        # Combine all sections maintaining the desired order
        left_column = left_column_sections
        right_column = right_column_sections
        
        # For single column layout, combine left then right
        if not right_column:
            body = (
                f'<div class="catalog-modal-column">' + '\n'.join(left_column) + '</div>'
            )
        else:
            body = (
                f'<div class="catalog-modal-column">' + '\n'.join(left_column) + '</div>' +
                f'<div class="catalog-modal-column">' + '\n'.join(right_column) + '</div>'
            )

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
            
            # Support both absolute paths (relative to docs_dir) and relative paths (relative to current file)
            # Check if path starts with ./ or ../ (relative to current file)
            if rel_dir.startswith('./') or rel_dir.startswith('../'):
                # Relative to current markdown file
                current_file_dir = os.path.dirname(page.file.abs_src_path) if hasattr(page.file, 'abs_src_path') else os.path.dirname(page.file.src_path)
                yaml_dir = os.path.normpath(os.path.join(current_file_dir, rel_dir))
                
                # Debug logging
                print(f"🔍 Product Catalog Debug (relative path):")
                print(f"   - Content tag found: <!-- product-catalog: {rel_dir} -->")
                print(f"   - Current file directory: {current_file_dir}")
                print(f"   - Resolved YAML directory: {yaml_dir}")
            else:
                # Absolute path relative to docs_dir (original behavior)
                yaml_dir = os.path.join(self._docs_dir, rel_dir)
                
                # Debug logging
                print(f"🔍 Product Catalog Debug (absolute path):")
                print(f"   - Content tag found: <!-- product-catalog: {rel_dir} -->")
                print(f"   - Docs directory: {self._docs_dir}")
                print(f"   - Resolved YAML directory: {yaml_dir}")
            
            print(f"   - Directory exists: {os.path.exists(yaml_dir)}")
            
            if os.path.exists(yaml_dir):
                print(f"   - Directory contents: {os.listdir(yaml_dir) if os.path.isdir(yaml_dir) else 'Not a directory'}")
            
            products = load_products(yaml_dir)
            print(f"   - Products loaded: {len(products)}")
            for p in products:
                print(f"     • {p.get('title', 'Untitled')}")
            
            return render_catalog_html(products, id_prefix=slugify(rel_dir) + "-")

        return _CONTENT_TAG_RE.sub(replace_tag, html)

    def on_nav(self, nav, config, files):
        """Add catalog services to the navigation."""
        from mkdocs.structure.nav import Section, Page
        

        
        # Scan for catalog directories in the docs
        catalog_services = []
        docs_dir = config["docs_dir"]
        
        # Look for <!-- product-catalog: dir --> comments in markdown files
        import re
        catalog_pattern = re.compile(r'<!--\s*product-catalog:\s*([^\s>]+)\s*-->')
        

        
        for file in files:
            if hasattr(file, 'src_path') and file.src_path.endswith('.md'):
                try:
                    # Use abs_src_path if available, otherwise src_path
                    file_path = getattr(file, 'abs_src_path', file.src_path)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    match = catalog_pattern.search(content)
                    if match:
                        catalog_dir = match.group(1)
                        
                        # Support both absolute and relative paths in navigation generation
                        if catalog_dir.startswith('./') or catalog_dir.startswith('../'):
                            # Relative to current markdown file
                            current_file_dir = os.path.dirname(file_path)
                            yaml_dir = os.path.normpath(os.path.join(current_file_dir, catalog_dir))
                        else:
                            # Absolute path relative to docs_dir
                            yaml_dir = os.path.join(docs_dir, catalog_dir)
                        
                        # Debug logging for navigation generation
                        print(f"🔧 Nav Generation Debug:")
                        print(f"   - File: {file_path}")
                        print(f"   - Catalog dir from tag: {catalog_dir}")
                        print(f"   - Resolved YAML dir: {yaml_dir}")
                        print(f"   - YAML dir exists: {os.path.exists(yaml_dir)}")
                        
                        if os.path.isdir(yaml_dir):
                            products = load_products(yaml_dir)
                            print(f"   - Products found: {len(products)}")

                            # Clean up catalog_dir for modal_id generation (remove relative path indicators)
                            clean_catalog_dir = catalog_dir.replace('./', '').replace('../', '').lstrip('/')
                            
                            catalog_services.extend([
                                {
                                    'title': p.get('title', 'Unknown Service'),
                                    'page': file.src_path,
                                    'modal_id': f"{slugify(clean_catalog_dir)}-{slugify(p.get('title', 'unknown'))}-{idx}"
                                }
                                for idx, p in enumerate(products)
                            ])
                        else:
                            print(f"   ⚠️  YAML directory not found!")
                except Exception as e:
                    # Log file reading errors
                    print(f"   ❌ Error reading file {file_path}: {e}")
                    # Silently ignore files that can't be read
                    pass
        

        
        # Group services by their source page to maintain separate catalogs
        from mkdocs.structure.nav import Link, Section
        from collections import defaultdict
        
        # Group services by their source page (which contains the catalog tag)
        page_catalogs = defaultdict(list)
        for service in catalog_services:
            page_path = service['page']
            page_catalogs[page_path].append(service)
        
        # Create catalog sections for each page
        for page_path, services in page_catalogs.items():
            # Extract catalog directory from the first service's modal_id
            # This is more reliable than hardcoding page names
            catalog_dir = "services"  # default fallback
            if services and 'modal_id' in services[0]:
                modal_id = services[0]['modal_id']
                # Extract catalog prefix from modal_id (format: catalog_dir-title-index)
                if '-' in modal_id:
                    catalog_dir = modal_id.split('-')[0]
                # Handle legacy format with paths
                elif '/' in modal_id:
                    parts = modal_id.split('/')
                    if parts[-1] and '-' in parts[-1]:
                        catalog_dir = parts[-1].split('-')[0]
            
            # Determine catalog name from the actual page title (not filename)
            # Read the markdown file to extract the actual page title
            catalog_name = "Service Catalog"  # Default fallback
            try:
                # Ensure page_path is absolute for file reading
                if not os.path.isabs(page_path):
                    page_path = os.path.join(docs_dir, page_path)
                
                with open(page_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract the first heading (page title)
                    import re
                    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    if title_match:
                        page_title = title_match.group(1).strip()
                        # Use the actual page title for the catalog name
                        catalog_name = page_title
            except Exception as e:
                # Fallback to filename-based name if we can't read the file
                print(f"Warning: Could not read page title from {page_path}: {e}")
                page_filename = os.path.basename(page_path)
                catalog_name_base = page_filename.replace('_catalog.md', '').replace('.md', '').replace('_', ' ').replace('-', ' ')
                catalog_name = f"{catalog_name_base.title()} Catalog"
            
            # Determine overview URL from the page path
            # Extract the directory path relative to docs/
            # Ensure page_path is absolute for correct relative path calculation
            if not os.path.isabs(page_path):
                page_path = os.path.join(docs_dir, page_path)
            
            rel_path = os.path.relpath(page_path, docs_dir)
            if rel_path.startswith('..'):
                # Fallback if path is outside docs_dir
                overview_url = "ats/infrastructure_service/service_catalog"
            else:
                # Convert to URL path (remove .md extension)
                url_path = os.path.splitext(rel_path)[0]
                overview_url = url_path.replace(os.sep, '/')
            
            # Create Services subsection for this catalog
            services_section = Section(title="Services", children=[])
            
            for service in services:
                title = service['title']
                # Generate modal_id the same way as in render_catalog_html: catalog_dir + slugified title + index
                # But first, extract the actual modal_id from the service if it exists
                modal_id = service.get('modal_id', '')
                if modal_id:
                    # Extract just the last part after the final slash/dash
                    if '/' in modal_id:
                        modal_id = modal_id.split('/')[-1]
                    elif 'catalog/' in modal_id:
                        modal_id = modal_id.split('catalog/')[-1]
                else:
                    modal_id = f"{catalog_dir}-{slugify(title)}-{services.index(service)}"
                
                # Create a Link object that links to the page with modal hash
                service_link = Link(
                    title=title,
                    url=f"{overview_url}#modal-" + modal_id
                )
                services_section.children.append(service_link)
            
            # Create Overview subsection
            overview_link = Link(title="Overview", url=overview_url)
            
            # Create the catalog section
            catalog_section = Section(title=catalog_name, children=[overview_link, services_section])
            
            # Find existing navigation item for this catalog
            # Look for either:
            # 1. A section that contains our overview page as a child
            # 2. A simple link that points directly to our overview page
            existing_item = None
            existing_item_index = -1
            
            for idx, item in enumerate(nav.items):
                # Case 1: Section containing our overview page
                if hasattr(item, 'children') and item.children:
                    for child in item.children:
                        if (hasattr(child, 'url') and 
                            child.url and 
                            overview_url in child.url):
                            existing_item = item
                            existing_item_index = idx
                            break
                    if existing_item:
                        break
                
                # Case 2: Simple link pointing to our overview page
                elif (hasattr(item, 'url') and 
                      item.url and 
                      overview_url in item.url):
                    existing_item = item
                    existing_item_index = idx
                    break
            
            if existing_item:
                if hasattr(existing_item, 'children'):
                    # Existing section - update its children
                    existing_item.children = catalog_section.children
                    print(f"Updated existing catalog section: {existing_item.title}")
                else:
                    # Existing simple link - replace with our section
                    # Preserve the user's custom title
                    catalog_section.title = existing_item.title
                    nav.items[existing_item_index] = catalog_section
                    print(f"Replaced simple link with catalog section: {catalog_section.title}")
                    print(f"  - Replaced item at index {existing_item_index}")
                    print(f"  - Original item: {existing_item}")
                    print(f"  - New item: {catalog_section}")
            else:
                # Add new section
                nav.items.append(catalog_section)
                print(f"Added new catalog section: {catalog_name}")
                print(f"  - No existing section found for {overview_url}")
                print(f"  - Available nav items: {[getattr(item, 'title', 'No title') for item in nav.items]}")
        
        return nav

    def on_post_build(self, config):
        if self._tmpdir and os.path.isdir(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
