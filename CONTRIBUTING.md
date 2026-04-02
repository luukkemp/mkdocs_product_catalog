# Contributing

## Development setup

Clone the repository and install the package in editable mode with dev dependencies:

```bash
git clone <repo-url>
cd mkdocs-product-catalog
pip install -e ".[dev]"
```

## Project structure

```
mkdocs_product_catalog/   # Python package (the plugin source)
  __init__.py
  plugin.py
tests/
  unit_tests/             # pytest unit tests
    test_plugin.py
  test_site/              # minimal MkDocs site for manual testing
    mkdocs.yml
    docs/
      index.md
      catalog/
```

## Running tests

```bash
pytest tests/unit_tests/
```

## Manual testing

Build the test site to verify end-to-end behaviour:

```bash
cd tests/test_site
mkdocs build
```

The generated `tests/test_site/site/` directory is gitignored.

Or run a temporary mkdocs server.

```bash
cd tests/test_site
mkdocs serve
```

## Making changes

The plugin logic lives entirely in `mkdocs_product_catalog/plugin.py`. The file is structured as follows:

| Section | What it contains |
|---|---|
| `CATALOG_CSS` / `CATALOG_JS` | Static assets written to the site at build time |
| `make_acronym`, `slugify`, `linkify` | Pure utility functions |
| `load_products` | Reads `.yaml`/`.yml` files from a directory |
| `render_catalog_html` | Builds the button grid, modals, and search index HTML |
| `ProductCatalogPlugin` | MkDocs plugin hooks |

When adding a new YAML field, the change touches two places: `render_catalog_html` (to render it in the modal) and `test_plugin.py` (to assert it appears in the output).

## Adding a product field

1. Add a section in `render_catalog_html` following the pattern of the existing fields (`url`, `documentation`, `repository`, etc.).
2. Add a corresponding test in `TestRenderCatalogHtml`.
3. Update `README.md` to document the new field in the YAML format table.

## Submitting changes

Open a pull request against the main branch. Please include:
- A description of what changed and why
- Passing tests (`pytest tests/unit_tests/`)
- Updated documentation if the behaviour visible to users changed
