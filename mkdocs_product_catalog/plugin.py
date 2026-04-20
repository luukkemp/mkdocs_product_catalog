"""mkdocs-product-catalog plugin — main entry point."""

import importlib.resources
import logging
import os
import re
import shutil
import tempfile

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File

from .catalog import load_products, render_catalog_html
from .nav import build_catalog_nav
from .utils import catalog_id_prefix

log = logging.getLogger("mkdocs.plugins.product-catalog")

_CSS_PATH = "assets/product-catalog.css"
_JS_PATH = "assets/product-catalog.js"

# Matches <!-- product-catalog: some/dir --> (and optional no-nav) in rendered
# HTML. Python-Markdown may wrap a standalone HTML comment in a <p> tag.
_CONTENT_TAG_RE = re.compile(
    r"(?:<p[^>]*>\s*)?<!--\s*product-catalog:\s*([^\s>]+)(\s+no-nav)?\s*-->(?:\s*</p>)?"
)


def _read_asset(filename: str) -> str:
    """Read a bundled asset file from the package assets/ directory."""
    try:
        # Python 3.9+
        ref = importlib.resources.files("mkdocs_product_catalog") / "assets" / filename
        return ref.read_text(encoding="utf-8")
    except AttributeError:
        # Python 3.8 fallback
        import pkg_resources
        return pkg_resources.resource_string(
            "mkdocs_product_catalog", f"assets/{filename}"
        ).decode("utf-8")


class ProductCatalogPlugin(BasePlugin):
    config_scheme = (
        ("nav_enabled", config_options.Type(bool, default=True)),
    )

    def __init__(self):
        super().__init__()
        self._tmpdir: str | None = None
        self._docs_dir: str | None = None
        self._assets_registered: bool = False

    def on_config(self, config):
        self._docs_dir = config["docs_dir"]

        if self._tmpdir is None:
            self._tmpdir = tempfile.mkdtemp(prefix="mkdocs_product_catalog_")
            css_path = os.path.join(self._tmpdir, _CSS_PATH)
            js_path = os.path.join(self._tmpdir, _JS_PATH)
            os.makedirs(os.path.dirname(css_path), exist_ok=True)

            with open(css_path, "w", encoding="utf-8") as f:
                f.write(_read_asset("product-catalog.css"))
            with open(js_path, "w", encoding="utf-8") as f:
                f.write(_read_asset("product-catalog.js"))

        # Guard against double-registration if on_config fires multiple times
        if _CSS_PATH not in config.get("extra_css", []):
            config.setdefault("extra_css", []).append(_CSS_PATH)
        if _JS_PATH not in config.get("extra_javascript", []):
            config.setdefault("extra_javascript", []).append(_JS_PATH)

        return config

    def on_files(self, files, config):
        for rel_path in (_CSS_PATH, _JS_PATH):
            files.append(
                File(
                    path=rel_path,
                    src_dir=self._tmpdir,
                    dest_dir=config["site_dir"],
                    use_directory_urls=config["use_directory_urls"],
                )
            )
        return files

    def on_page_content(self, html, page, config, files):
        """Replace <!-- product-catalog: dir --> tags with rendered catalog HTML."""

        def replace_tag(match):
            rel_dir = match.group(1).strip()

            if rel_dir.startswith("./") or rel_dir.startswith("../"):
                current_dir = os.path.dirname(
                    getattr(page.file, "abs_src_path", None)
                    or os.path.join(self._docs_dir, page.file.src_path)
                )
                yaml_dir = os.path.normpath(os.path.join(current_dir, rel_dir))
            else:
                yaml_dir = os.path.join(self._docs_dir, rel_dir)

            log.debug(
                f"product-catalog: rendering catalog '{rel_dir}' "
                f"on page '{page.file.src_path}' → {yaml_dir}"
            )

            products = load_products(yaml_dir)
            if not products:
                log.warning(
                    f"product-catalog: no products found in '{yaml_dir}' "
                    f"(referenced from {page.file.src_path})"
                )

            return render_catalog_html(products, id_prefix=catalog_id_prefix(rel_dir))

        return _CONTENT_TAG_RE.sub(replace_tag, html)

    def on_nav(self, nav, config, files):
        return build_catalog_nav(
            nav,
            files,
            config,
            nav_enabled=self.config.get("nav_enabled", True),
        )

    def on_post_build(self, config):
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
