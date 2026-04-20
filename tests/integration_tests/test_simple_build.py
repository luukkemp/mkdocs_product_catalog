"""Integration tests: full MkDocs build with the product-catalog plugin."""

import os
import subprocess
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_SITE_DIR = os.path.join(TESTS_DIR, "test_site")


def _build(mkdocs_yml: str = "mkdocs.yml", strict: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "mkdocs", "build", "-f", mkdocs_yml]
    if strict:
        cmd.append("--strict")
    return subprocess.run(cmd, cwd=TEST_SITE_DIR, capture_output=True, text=True)


class TestSimpleBuild:
    def test_build_succeeds(self):
        result = _build()
        assert result.returncode == 0, (
            f"mkdocs build failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    def test_catalog_html_in_output(self):
        _build()
        site_dir = os.path.join(TEST_SITE_DIR, "site")
        services_html = os.path.join(site_dir, "services", "index.html")
        assert os.path.exists(services_html), "services/index.html not built"
        content = open(services_html, encoding="utf-8").read()
        assert 'class="catalog-grid"' in content
        assert "Alpha Service" in content
        assert "Beta Tool" in content

    def test_css_asset_in_output(self):
        _build()
        site_dir = os.path.join(TEST_SITE_DIR, "site")
        css_path = os.path.join(site_dir, "assets", "product-catalog.css")
        assert os.path.exists(css_path), "CSS asset not copied to site"
        content = open(css_path, encoding="utf-8").read()
        assert "catalog-grid" in content

    def test_js_asset_in_output(self):
        _build()
        site_dir = os.path.join(TEST_SITE_DIR, "site")
        js_path = os.path.join(site_dir, "assets", "product-catalog.js")
        assert os.path.exists(js_path), "JS asset not copied to site"
        content = open(js_path, encoding="utf-8").read()
        assert "openCatalogModal" in content

    def test_modals_present_in_output(self):
        _build()
        site_dir = os.path.join(TEST_SITE_DIR, "site")
        content = open(os.path.join(site_dir, "services", "index.html"), encoding="utf-8").read()
        assert "catalog-overlay" in content
        assert "catalog-modal" in content

    def test_no_debug_print_in_output(self):
        result = _build()
        # Debug prints should not appear in stderr/stdout during a normal build
        assert "🔍 Product Catalog Debug" not in result.stdout
        assert "🔍 Product Catalog Debug" not in result.stderr
        assert "🔧 Nav Generation Debug" not in result.stdout
        assert "🔧 Nav Generation Debug" not in result.stderr

    def test_html_escaping_in_output(self):
        """Products with HTML chars in titles are safely escaped in catalog HTML.

        Both the catalog HTML section (modal/grid) and nav links must not
        render unescaped HTML tags from YAML titles.
        """
        import yaml

        orig_catalog = os.path.join(TEST_SITE_DIR, "docs", "catalog")
        tmp_yaml = os.path.join(orig_catalog, "_xss_test.yaml")
        try:
            with open(tmp_yaml, "w") as f:
                yaml.dump({"title": "<script>alert(1)</script>", "description": "xss"}, f)
            _build()
            site_dir = os.path.join(TEST_SITE_DIR, "site")
            content = open(os.path.join(site_dir, "services", "index.html"), encoding="utf-8").read()

            # The catalog-grid section must not contain unescaped <script>
            grid_start = content.find('class="catalog-grid"')
            grid_end = content.find("catalog-overlay", grid_start)
            catalog_section = content[grid_start:grid_end]
            assert "<script>alert(1)</script>" not in catalog_section, \
                "XSS title must be escaped in catalog-grid HTML"

            # The modal section must also be escaped
            modal_start = content.find('class="catalog-overlay"')
            modal_end = content.find("catalog-search-index", modal_start)
            modal_section = content[modal_start:modal_end] if modal_end > modal_start else \
                content[modal_start:modal_start + 2000]
            assert "<script>alert(1)</script>" not in modal_section, \
                "XSS title must be escaped in modal HTML"

            # Escaped form must be present somewhere in the page
            assert "&lt;script&gt;" in content, \
                "HTML-escaped title must appear in the page"
        finally:
            if os.path.exists(tmp_yaml):
                os.unlink(tmp_yaml)
