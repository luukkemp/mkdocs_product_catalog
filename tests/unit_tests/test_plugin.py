import re
import pytest

from mkdocs_product_catalog.plugin import (
    _CONTENT_TAG_RE,
    linkify,
    load_products,
    make_acronym,
    render_catalog_html,
    slugify,
)


# ── make_acronym ──────────────────────────────────────────────────────────────

class TestMakeAcronym:
    def test_single_word(self):
        assert make_acronym("Product") == "P"

    def test_two_words(self):
        assert make_acronym("My Product") == "MP"

    def test_three_words(self):
        assert make_acronym("Data Pipeline Service") == "DPS"

    def test_more_than_three_words_capped_at_three(self):
        assert make_acronym("One Two Three Four") == "OTT"

    def test_empty_string(self):
        assert make_acronym("") == "?"

    def test_none(self):
        assert make_acronym(None) == "?"

    def test_special_characters_only(self):
        assert make_acronym("--- !!!") == "?"

    def test_numbers_included(self):
        assert make_acronym("Product 2 Alpha") == "P2A"

    def test_uppercase_preserved(self):
        assert make_acronym("azure devops") == "AD"


# ── slugify ───────────────────────────────────────────────────────────────────

class TestSlugify:
    def test_simple(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self):
        assert slugify("My Product!") == "my-product"

    def test_multiple_spaces_become_one_hyphen(self):
        assert slugify("a   b") == "a-b"

    def test_no_leading_trailing_hyphens(self):
        assert slugify("  hello  ") == "hello"

    def test_empty_string(self):
        assert slugify("") == "item"

    def test_none(self):
        assert slugify(None) == "item"

    def test_already_slugified(self):
        assert slugify("my-product") == "my-product"


# ── linkify ───────────────────────────────────────────────────────────────────

class TestLinkify:
    def test_plain_text_unchanged(self):
        assert linkify("just some text") == "just some text"

    def test_https_url_wrapped(self):
        result = linkify("https://example.com")
        assert 'href="https://example.com"' in result
        assert ">https://example.com<" in result
        assert 'target="_blank"' in result
        assert 'rel="noopener"' in result

    def test_http_url_wrapped(self):
        result = linkify("http://example.com")
        assert 'href="http://example.com"' in result

    def test_ftp_url_wrapped(self):
        result = linkify("ftp://files.example.com")
        assert 'href="ftp://files.example.com"' in result

    def test_text_with_embedded_url(self):
        result = linkify("See https://example.com for details")
        assert 'href="https://example.com"' in result
        assert "See " in result
        assert "for details" in result

    def test_non_url_unchanged(self):
        assert linkify("99.9%") == "99.9%"

    def test_numeric_value_converted_to_string(self):
        assert linkify(42) == "42"


# ── load_products ─────────────────────────────────────────────────────────────

class TestLoadProducts:
    def test_nonexistent_directory_returns_empty(self, tmp_path):
        assert load_products(str(tmp_path / "does_not_exist")) == []

    def test_empty_directory_returns_empty(self, tmp_path):
        assert load_products(str(tmp_path)) == []

    def test_loads_yaml_file(self, tmp_path):
        (tmp_path / "product.yaml").write_text("title: My Product\ndescription: Desc\n")
        products = load_products(str(tmp_path))
        assert len(products) == 1
        assert products[0]["title"] == "My Product"

    def test_loads_yml_extension(self, tmp_path):
        (tmp_path / "product.yml").write_text("title: Other Product\n")
        products = load_products(str(tmp_path))
        assert len(products) == 1

    def test_loads_both_extensions(self, tmp_path):
        (tmp_path / "a.yaml").write_text("title: A\n")
        (tmp_path / "b.yml").write_text("title: B\n")
        products = load_products(str(tmp_path))
        assert len(products) == 2

    def test_sorted_alphabetically_by_filename(self, tmp_path):
        (tmp_path / "b_product.yaml").write_text("title: B\n")
        (tmp_path / "a_product.yaml").write_text("title: A\n")
        products = load_products(str(tmp_path))
        assert products[0]["title"] == "A"
        assert products[1]["title"] == "B"

    def test_non_dict_yaml_skipped(self, tmp_path):
        (tmp_path / "list.yaml").write_text("- item1\n- item2\n")
        (tmp_path / "product.yaml").write_text("title: Real Product\n")
        products = load_products(str(tmp_path))
        assert len(products) == 1
        assert products[0]["title"] == "Real Product"


# ── render_catalog_html ───────────────────────────────────────────────────────

class TestRenderCatalogHtml:
    def test_empty_products_renders_empty_grid(self):
        html = render_catalog_html([])
        assert 'class="catalog-grid"' in html
        assert 'catalog-btn' not in html

    def test_product_with_icon_renders_img(self):
        html = render_catalog_html([{"title": "My App", "icon": "logo.png"}])
        assert '<img class="catalog-icon" src="logo.png"' in html

    def test_product_without_icon_renders_acronym(self):
        html = render_catalog_html([{"title": "My App"}])
        assert '<span class="catalog-acronym">MA</span>' in html

    def test_description_in_modal(self):
        html = render_catalog_html([{"title": "T", "description": "A great tool"}])
        assert "A great tool" in html

    def test_url_in_modal(self):
        html = render_catalog_html([{"title": "T", "url": "https://example.com"}])
        assert 'href="https://example.com"' in html

    def test_documentation_in_modal(self):
        html = render_catalog_html([{"title": "T", "documentation": "https://docs.example.com"}])
        assert 'href="https://docs.example.com"' in html

    def test_repository_in_modal(self):
        html = render_catalog_html([{"title": "T", "repository": "https://github.com/x/y"}])
        assert 'href="https://github.com/x/y"' in html

    def test_owners_rendered_as_tags(self):
        html = render_catalog_html([{"title": "T", "owners": ["Alice", "Bob"]}])
        assert '<span class="catalog-tag">Alice</span>' in html
        assert '<span class="catalog-tag">Bob</span>' in html

    def test_metadata_plain_value(self):
        html = render_catalog_html([{"title": "T", "metadata": {"team": "platform"}}])
        assert "<dt>team</dt><dd>platform</dd>" in html

    def test_metadata_url_value_linkified(self):
        html = render_catalog_html([{"title": "T", "metadata": {"dash": "https://grafana.example.com"}}])
        assert 'href="https://grafana.example.com"' in html

    def test_no_style_or_script_tags(self):
        html = render_catalog_html([{"title": "T"}])
        assert "<style" not in html
        assert "<script" not in html

    def test_no_h2_tags(self):
        # h2 would cause MkDocs search to split the page per product
        html = render_catalog_html([{"title": "T"}])
        assert "<h2" not in html

    def test_search_index_contains_title(self):
        html = render_catalog_html([{"title": "Unique Product Name"}])
        idx_start = html.index('class="catalog-search-index"')
        idx_end = html.index("catalog-grid")
        search_section = html[idx_start:idx_end]
        assert "Unique Product Name" in search_section

    def test_search_index_contains_description(self):
        html = render_catalog_html([{"title": "T", "description": "Searchable description"}])
        idx_start = html.index('class="catalog-search-index"')
        idx_end = html.index("catalog-grid")
        assert "Searchable description" in html[idx_start:idx_end]

    def test_search_index_contains_owners(self):
        html = render_catalog_html([{"title": "T", "owners": ["Carol"]}])
        idx_start = html.index('class="catalog-search-index"')
        idx_end = html.index("catalog-grid")
        assert "Carol" in html[idx_start:idx_end]

    def test_id_prefix_applied_to_modal_id(self):
        html = render_catalog_html([{"title": "My App"}], id_prefix="tools-")
        assert 'id="catalog-overlay-tools-my-app-0"' in html

    def test_multiple_products_unique_ids(self):
        html = render_catalog_html([{"title": "Alpha"}, {"title": "Beta"}])
        assert 'catalog-overlay-alpha-0' in html
        assert 'catalog-overlay-beta-1' in html

    def test_missing_optional_fields_render_cleanly(self):
        # Only title provided — optional sections must not appear
        html = render_catalog_html([{"title": "Minimal"}])
        assert "catalog-modal-section-title" not in html


# ── _CONTENT_TAG_RE ───────────────────────────────────────────────────────────

class TestContentTagRe:
    def test_matches_bare_comment(self):
        m = _CONTENT_TAG_RE.search("<!-- product-catalog: my-dir -->")
        assert m is not None
        assert m.group(1) == "my-dir"

    def test_matches_comment_wrapped_in_p(self):
        m = _CONTENT_TAG_RE.search("<p><!-- product-catalog: tools --></p>")
        assert m is not None
        assert m.group(1) == "tools"

    def test_matches_comment_with_extra_whitespace(self):
        m = _CONTENT_TAG_RE.search("<!--  product-catalog:  some/path  -->")
        assert m is not None
        assert m.group(1) == "some/path"

    def test_does_not_match_unrelated_comment(self):
        assert _CONTENT_TAG_RE.search("<!-- regular html comment -->") is None

    def test_extracts_nested_path(self):
        m = _CONTENT_TAG_RE.search("<!-- product-catalog: catalog/tools -->")
        assert m.group(1) == "catalog/tools"
