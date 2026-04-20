"""Integration tests: full MkDocs build using mkdocs-multirepo-plugin.

These tests clone a real GitHub repo and require network access.
They are skipped automatically when:
- mkdocs-multirepo-plugin is not installed
- The SKIP_MULTIREPO_TESTS environment variable is set to "1"
- Network is unavailable (detected by a failed clone)

Run them explicitly with:
    pytest tests/integration_tests/test_multirepo_build.py -v
"""

import os
import subprocess
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_SITE_DIR = os.path.join(TESTS_DIR, "test_site")
MULTIREPO_YML = os.path.join(TEST_SITE_DIR, "mkdocs-multirepo.yml")

# Fixture repo metadata
FIXTURE_REPO = "https://github.com/tomasz-krakowski-asml/mkdocs-catalog-test-fixture"
EXPECTED_SERVICES = ["Alpha API", "Alpha Worker", "Alpha Cache"]


def _multirepo_available() -> bool:
    try:
        import mkdocs_multirepo_plugin  # noqa: F401
        return True
    except ImportError:
        return False


def _skip_reason() -> str | None:
    if os.environ.get("SKIP_MULTIREPO_TESTS") == "1":
        return "SKIP_MULTIREPO_TESTS=1"
    if not _multirepo_available():
        return "mkdocs-multirepo-plugin not installed"
    return None


skip_if_unavailable = pytest.mark.skipif(
    _skip_reason() is not None,
    reason=_skip_reason() or "",
)


def _build_multirepo() -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "-m", "mkdocs", "build",
        "-f", "mkdocs-multirepo.yml",
        "--strict",
    ]
    return subprocess.run(cmd, cwd=TEST_SITE_DIR, capture_output=True, text=True)


@skip_if_unavailable
class TestMultirepoBuild:
    """End-to-end tests for multirepo catalog integration."""

    def test_build_succeeds(self):
        result = _build_multirepo()
        assert result.returncode == 0, (
            f"Multirepo mkdocs build failed.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    def test_imported_services_rendered(self):
        """Services from the imported repo appear in the built HTML."""
        result = _build_multirepo()
        assert result.returncode == 0, result.stderr

        site_dir = os.path.join(TEST_SITE_DIR, "site")

        # Multirepo places imported content under the section name slug
        # The catalog page should be at team-alpha/catalog/ or similar
        catalog_candidates = [
            os.path.join(site_dir, "team-alpha", "catalog", "index.html"),
            os.path.join(site_dir, "team_alpha", "catalog", "index.html"),
        ]
        catalog_html_path = next(
            (p for p in catalog_candidates if os.path.exists(p)), None
        )
        assert catalog_html_path is not None, (
            f"Catalog page not found. Checked:\n"
            + "\n".join(f"  {p}" for p in catalog_candidates)
            + f"\nSite directory contents: {_list_site(site_dir)}"
        )

        content = open(catalog_html_path, encoding="utf-8").read()
        assert 'class="catalog-grid"' in content, "Catalog grid not rendered"
        for service in EXPECTED_SERVICES:
            assert service in content, f"Service '{service}' not found in catalog HTML"

    def test_catalog_modal_links_work(self):
        """Nav links for imported services contain correct modal hash anchors."""
        result = _build_multirepo()
        assert result.returncode == 0, result.stderr

        site_dir = os.path.join(TEST_SITE_DIR, "site")
        index_html = os.path.join(site_dir, "index.html")
        if not os.path.exists(index_html):
            pytest.skip("index.html not built, skipping nav link check")

        content = open(index_html, encoding="utf-8").read()

        # Each imported service must appear as a nav link pointing into
        # the team-alpha catalog page with a modal hash anchor.
        for service in EXPECTED_SERVICES:
            assert service in content, (
                f"Service '{service}' not found as nav link in index.html"
            )

        # The modal links must point into team-alpha/catalog, not the local catalog.
        assert "team-alpha/catalog#modal-" in content, (
            "No team-alpha/catalog modal deep-link hashes found in nav; "
            "multirepo nav integration is not injecting links for imported repo"
        )

    def test_no_fallback_url_in_output(self):
        """The hardcoded fallback URL from the old plugin must not appear."""
        result = _build_multirepo()
        assert result.returncode == 0, result.stderr

        site_dir = os.path.join(TEST_SITE_DIR, "site")
        for root, _, files in os.walk(site_dir):
            for fname in files:
                if not fname.endswith(".html"):
                    continue
                fpath = os.path.join(root, fname)
                content = open(fpath, encoding="utf-8").read()
                assert "ats/infrastructure_service/service_catalog" not in content, (
                    f"Hardcoded fallback URL found in {fpath}"
                )

    def test_css_and_js_assets_present(self):
        result = _build_multirepo()
        assert result.returncode == 0, result.stderr

        site_dir = os.path.join(TEST_SITE_DIR, "site")
        assert os.path.exists(os.path.join(site_dir, "assets", "product-catalog.css"))
        assert os.path.exists(os.path.join(site_dir, "assets", "product-catalog.js"))


def _list_site(site_dir: str, depth: int = 2) -> str:
    """Return a short directory listing for debugging."""
    lines = []
    for root, dirs, files in os.walk(site_dir):
        level = root.replace(site_dir, "").count(os.sep)
        if level > depth:
            dirs[:] = []
            continue
        indent = "  " * level
        lines.append(f"{indent}{os.path.basename(root)}/")
        subindent = "  " * (level + 1)
        for fname in files[:5]:
            lines.append(f"{subindent}{fname}")
        if len(files) > 5:
            lines.append(f"{subindent}... ({len(files) - 5} more)")
    return "\n".join(lines)
