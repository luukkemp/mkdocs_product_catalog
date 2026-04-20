"""Tests for nav integration (nav.py).

Uses real MkDocs structure objects to test the nav builder accurately.
"""

import os

import pytest

from mkdocs.structure.nav import Link, Navigation, Section

from mkdocs_product_catalog.nav import (
    _collect_pages,
    _extract_h1,
    _find_nav_item_for_url,
    _resolve_yaml_dir,
    _title_from_src_path,
    build_catalog_nav,
)
from mkdocs_product_catalog.utils import catalog_id_prefix, slugify


class _MockFile:
    """Minimal stand-in for a MkDocs File used in nav tests."""
    def __init__(self, src_path: str, abs_src_path: str):
        self.src_path = src_path
        self.abs_src_path = abs_src_path


class _MockPage:
    """Minimal stand-in for a MkDocs Page with the attributes nav.py needs."""
    def __init__(self, src_path: str, url: str, title: str | None, abs_src_path: str):
        self.file = _MockFile(src_path, abs_src_path)
        self.url = url
        self.title = title
        # Pages don't have children — nav builder uses hasattr(item, 'file')
        # to distinguish Pages from Sections.


def _make_page(src_path: str, url: str, title: str | None, abs_src_path: str) -> _MockPage:
    return _MockPage(src_path, url, title, abs_src_path)


def _make_nav(items):
    return Navigation(items=items, pages=[])


# ── _collect_pages ────────────────────────────────────────────────────────────

class TestCollectPages:
    def test_flat_nav(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("# Hello\n")
        page = _make_page("page.md", "page/", "Hello", str(f))
        pages = _collect_pages([page])
        assert "page.md" in pages
        assert pages["page.md"] is page

    def test_nested_section(self, tmp_path):
        f = tmp_path / "sub.md"
        f.write_text("# Sub\n")
        page = _make_page("sub.md", "sub/", "Sub", str(f))
        section = Section(title="My Section", children=[page])
        pages = _collect_pages([section])
        assert "sub.md" in pages

    def test_empty_nav(self):
        assert _collect_pages([]) == {}


# ── _find_nav_item_for_url ────────────────────────────────────────────────────

class TestFindNavItemForUrl:
    def test_finds_direct_link(self):
        link = Link(title="Overview", url="team/services/")
        container, idx, item = _find_nav_item_for_url([link], "team/services")
        assert idx == 0
        assert item is link

    def test_finds_page_nested_in_section(self, tmp_path):
        f = tmp_path / "catalog.md"
        f.write_text("# Catalog\n")
        page = _make_page("catalog.md", "team/catalog/", "Catalog", str(f))
        section = Section(title="Team", children=[page])
        container, idx, item = _find_nav_item_for_url([section], "team/catalog")
        # Returns the page itself, not the parent section
        assert item is page
        assert container is section.children
        assert idx == 0

    def test_finds_page_deeply_nested(self, tmp_path):
        """Three levels deep — the multirepo nested-section scenario."""
        f = tmp_path / "catalog.md"
        f.write_text("# Catalog\n")
        page = _make_page("catalog.md", "global/team-alpha/catalog/", "Services", str(f))
        team_alpha = Section(title="Team Alpha", children=[page])
        global_cat = Section(title="Global category", children=[team_alpha])
        container, idx, item = _find_nav_item_for_url([global_cat], "global/team-alpha/catalog")
        assert item is page
        assert container is team_alpha.children
        assert idx == 0

    def test_returns_none_when_not_found(self):
        link = Link(title="Other", url="other/page/")
        container, idx, item = _find_nav_item_for_url([link], "team/services")
        assert container is None
        assert idx is None
        assert item is None

    def test_url_trailing_slash_insensitive(self):
        link = Link(title="X", url="services/")
        container, idx, item = _find_nav_item_for_url([link], "services")
        assert idx == 0


# ── _resolve_yaml_dir ─────────────────────────────────────────────────────────

class TestResolveYamlDir:
    def test_absolute_path(self, tmp_path):
        result = _resolve_yaml_dir("catalog/services", "/docs/page.md", str(tmp_path))
        assert result == str(tmp_path) + "/catalog/services"

    def test_relative_dot_slash(self, tmp_path):
        file_path = str(tmp_path / "team" / "page.md")
        result = _resolve_yaml_dir("./services", file_path, "/docs")
        expected = os.path.normpath(str(tmp_path / "team" / "services"))
        assert result == expected

    def test_relative_dot_dot(self, tmp_path):
        file_path = str(tmp_path / "team" / "sub" / "page.md")
        result = _resolve_yaml_dir("../shared", file_path, "/docs")
        expected = os.path.normpath(str(tmp_path / "team" / "shared"))
        assert result == expected


# ── _extract_h1 ──────────────────────────────────────────────────────────────

class TestExtractH1:
    def test_extracts_h1(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("# My Page Title\n\nContent here.")
        assert _extract_h1(str(f)) == "My Page Title"

    def test_returns_none_when_no_h1(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("No heading here.\n")
        assert _extract_h1(str(f)) is None

    def test_returns_none_for_missing_file(self):
        assert _extract_h1("/nonexistent/path.md") is None

    def test_returns_none_for_none_input(self):
        assert _extract_h1(None) is None


# ── _title_from_src_path ──────────────────────────────────────────────────────

class TestTitleFromSrcPath:
    def test_simple_filename(self):
        assert _title_from_src_path("services.md") == "Services"

    def test_underscores_to_spaces(self):
        assert _title_from_src_path("my_service_catalog.md") == "My Service Catalog"

    def test_nested_path_uses_filename(self):
        assert _title_from_src_path("team/sub/catalog.md") == "Catalog"


# ── build_catalog_nav ─────────────────────────────────────────────────────────

class TestBuildCatalogNav:
    def _setup_catalog(self, tmp_path, subdir: str, products: list[dict]) -> str:
        """Create YAML files and return the catalog directory path."""
        catalog_dir = tmp_path / subdir
        catalog_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(products):
            import yaml
            (catalog_dir / f"{i:02d}_{slugify(p['title'])}.yaml").write_text(
                yaml.dump(p), encoding="utf-8"
            )
        return str(catalog_dir)

    def _make_file(self, src_path: str, content: str, docs_dir: str):
        """Create a mock MkDocs File object with a real file on disk."""
        abs_path = os.path.join(docs_dir, src_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        class _FakeFile:
            pass

        f = _FakeFile()
        f.src_path = src_path
        f.abs_src_path = abs_path
        return f

    def test_adds_section_for_catalog_page(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)

        self._setup_catalog(tmp_path / "docs", "catalog/services",
                            [{"title": "Alpha"}, {"title": "Beta"}])
        content = "# My Services\n\n<!-- product-catalog: catalog/services -->\n"
        md_file = self._make_file("services.md", content, docs_dir)

        page = _make_page("services.md", "services/", "My Services",
                          md_file.abs_src_path)
        nav = _make_nav([page])

        config = {"docs_dir": docs_dir}
        result = build_catalog_nav(nav, [md_file], config, nav_enabled=True)

        # Original page replaced by catalog section
        assert any(hasattr(i, "children") for i in result.items), \
            "Expected a Section in nav"
        section = next(i for i in result.items if hasattr(i, "children"))
        assert section.title == "My Services"
        child_titles = [c.title for c in section.children]
        assert "Overview" in child_titles
        assert "Services" in child_titles

    def test_services_subsection_links_to_modals(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "svc", [{"title": "Foo"}])
        md_file = self._make_file("catalog.md",
                                  "# Cat\n<!-- product-catalog: svc -->\n", docs_dir)
        page = _make_page("catalog.md", "catalog/", "Cat", md_file.abs_src_path)
        nav = _make_nav([page])

        config = {"docs_dir": docs_dir}
        result = build_catalog_nav(nav, [md_file], config)

        section = next(i for i in result.items if hasattr(i, "children"))
        services = next(c for c in section.children if c.title == "Services")
        assert len(services.children) == 1
        link = services.children[0]
        assert link.title == "Foo"

        expected_prefix = catalog_id_prefix("svc")
        expected_modal_id = f"{expected_prefix}{slugify('Foo')}-0"
        assert f"#modal-{expected_modal_id}" in link.url

    def test_no_nav_flag_skips_nav_entry(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "svc", [{"title": "Alpha"}])
        md_file = self._make_file("catalog.md",
                                  "# Cat\n<!-- product-catalog: svc no-nav -->\n", docs_dir)
        page = _make_page("catalog.md", "catalog/", "Cat", md_file.abs_src_path)
        nav = _make_nav([page])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})

        # No new sections should have been added (page itself was there already)
        sections = [i for i in result.items if hasattr(i, "children")]
        assert len(sections) == 0, "no-nav tag should suppress nav injection"

    def test_nav_disabled_globally(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "svc", [{"title": "Alpha"}])
        md_file = self._make_file("catalog.md",
                                  "# Cat\n<!-- product-catalog: svc -->\n", docs_dir)
        page = _make_page("catalog.md", "catalog/", "Cat", md_file.abs_src_path)
        nav = _make_nav([page])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir}, nav_enabled=False)

        sections = [i for i in result.items if hasattr(i, "children")]
        assert len(sections) == 0

    def test_multiple_catalog_tags_on_same_page_combined(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "teamA", [{"title": "Alpha"}])
        self._setup_catalog(tmp_path / "docs", "teamB", [{"title": "Beta"}])
        content = (
            "# Combined\n"
            "<!-- product-catalog: teamA -->\n"
            "<!-- product-catalog: teamB -->\n"
        )
        md_file = self._make_file("combined.md", content, docs_dir)
        page = _make_page("combined.md", "combined/", "Combined", md_file.abs_src_path)
        nav = _make_nav([page])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})

        sections = [i for i in result.items if hasattr(i, "children")]
        assert len(sections) == 1, "Both catalogs from same page → one nav section"
        services = next(c for c in sections[0].children if c.title == "Services")
        link_titles = [l.title for l in services.children]
        assert "Alpha" in link_titles
        assert "Beta" in link_titles

    def test_existing_nav_link_replaced_with_section(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "svc", [{"title": "Alpha"}])
        md_file = self._make_file("catalog.md",
                                  "# Cat\n<!-- product-catalog: svc -->\n", docs_dir)
        page = _make_page("catalog.md", "catalog/", "Cat", md_file.abs_src_path)
        # User manually added a simple link with custom title in mkdocs.yml
        existing_link = Link(title="My Custom Title", url="catalog/")
        nav = _make_nav([existing_link])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})

        # Should replace simple link with section, preserving user title
        sections = [i for i in result.items if hasattr(i, "children")]
        assert len(sections) == 1
        assert sections[0].title == "My Custom Title"

    def test_existing_section_children_updated(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "svc", [{"title": "NewService"}])
        md_file = self._make_file("catalog.md",
                                  "# Cat\n<!-- product-catalog: svc -->\n", docs_dir)
        page = _make_page("catalog.md", "catalog/", "Cat", md_file.abs_src_path)
        # Parent section wraps the catalog page
        existing_section = Section(title="Parent Section", children=[page])
        nav = _make_nav([existing_section])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})

        # Parent section still at root, its child replaced with catalog section
        assert len(result.items) == 1
        assert result.items[0].title == "Parent Section"
        inner = result.items[0].children[0]
        assert hasattr(inner, "children"), "page should be replaced with a Section"
        child_titles = [c.title for c in inner.children]
        assert "Overview" in child_titles
        assert "Services" in child_titles

    def test_catalog_injected_into_nested_section(self, tmp_path):
        """Regression: catalog page nested 3 levels deep must not duplicate at root."""
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        import yaml
        svc_dir = tmp_path / "docs" / "services"
        svc_dir.mkdir(parents=True)
        (svc_dir / "alpha.yaml").write_text(yaml.dump({"title": "Alpha"}))

        md_file = self._make_file(
            "team/catalog.md",
            "# Services\n<!-- product-catalog: ./services -->\n",
            docs_dir,
        )
        abs_svc_dir = str(tmp_path / "docs" / "team" / "services")
        # Override: place YAML next to the markdown file
        os.makedirs(abs_svc_dir, exist_ok=True)
        (tmp_path / "docs" / "team" / "services" / "alpha.yaml").write_text(
            yaml.dump({"title": "Alpha"})
        )

        page = _make_page(
            "team/catalog.md", "global/team/catalog/", "Services",
            md_file.abs_src_path
        )
        team_section = Section(title="Team Alpha", children=[page])
        global_section = Section(title="Global category", children=[team_section])
        nav = _make_nav([global_section])

        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})

        # Must not duplicate at root
        assert len(result.items) == 1, (
            f"Expected 1 root item, got {len(result.items)}: "
            f"{[i.title for i in result.items]}"
        )
        assert result.items[0].title == "Global category"

        # Catalog section must be inside Team Alpha
        team = result.items[0].children[0]
        assert team.title == "Team Alpha"
        inner = team.children[0]
        assert hasattr(inner, "children"), "Services page should become a Section"
        child_titles = [c.title for c in inner.children]
        assert "Overview" in child_titles
        assert "Services" in child_titles

    def test_page_not_in_nav_is_skipped(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "svc", [{"title": "Alpha"}])
        md_file = self._make_file("catalog.md",
                                  "# Cat\n<!-- product-catalog: svc -->\n", docs_dir)
        # Nav is empty — page is not listed
        nav = _make_nav([])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})
        assert result.items == []

    def test_missing_catalog_dir_logs_warning_no_crash(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        md_file = self._make_file("catalog.md",
                                  "# Cat\n<!-- product-catalog: nonexistent/dir -->\n",
                                  docs_dir)
        page = _make_page("catalog.md", "catalog/", "Cat", md_file.abs_src_path)
        nav = _make_nav([page])
        # Must not raise
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})
        assert result is nav

    def test_relative_path_resolved_from_file(self, tmp_path):
        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        # YAML files live next to the markdown file
        team_dir = tmp_path / "docs" / "team"
        team_dir.mkdir()
        import yaml
        (team_dir / "services" / "alpha.yaml").parent.mkdir()
        (team_dir / "services" / "alpha.yaml").write_text(
            yaml.dump({"title": "Alpha"}), encoding="utf-8"
        )
        md_file = self._make_file(
            "team/catalog.md",
            "# Team\n<!-- product-catalog: ./services -->\n",
            docs_dir,
        )
        page = _make_page("team/catalog.md", "team/catalog/", "Team", md_file.abs_src_path)
        nav = _make_nav([page])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})

        sections = [i for i in result.items if hasattr(i, "children")]
        assert len(sections) == 1
        services = next(c for c in sections[0].children if c.title == "Services")
        assert services.children[0].title == "Alpha"

    def test_modal_id_matches_render_catalog_html(self, tmp_path):
        """Modal IDs in nav links must match those generated by render_catalog_html."""
        from mkdocs_product_catalog.catalog import render_catalog_html

        docs_dir = str(tmp_path / "docs")
        os.makedirs(docs_dir)
        self._setup_catalog(tmp_path / "docs", "my/catalog", [{"title": "My Service"}])
        md_file = self._make_file("page.md",
                                  "# Page\n<!-- product-catalog: my/catalog -->\n",
                                  docs_dir)
        page = _make_page("page.md", "page/", "Page", md_file.abs_src_path)
        nav = _make_nav([page])
        result = build_catalog_nav(nav, [md_file], {"docs_dir": docs_dir})

        section = next(i for i in result.items if hasattr(i, "children"))
        services = next(c for c in section.children if c.title == "Services")
        nav_link_url = services.children[0].url

        # Render HTML with the same prefix and verify the modal ID matches
        products = [{"title": "My Service"}]
        html = render_catalog_html(products, id_prefix=catalog_id_prefix("my/catalog"))
        # Extract the modal ID from the HTML
        import re
        match = re.search(r'id="catalog-overlay-([^"]+)"', html)
        assert match, "HTML must contain a catalog-overlay element"
        html_modal_id = match.group(1)

        assert f"#modal-{html_modal_id}" in nav_link_url, (
            f"Nav link URL '{nav_link_url}' must contain '#modal-{html_modal_id}'"
        )
