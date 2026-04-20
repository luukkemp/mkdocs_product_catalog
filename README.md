# mkdocs-product-catalog

An MkDocs plugin that renders a product catalog on any page from a directory of YAML files. Each product appears as a clickable button with an icon (or acronym fallback). Clicking a button opens a lightbox modal with all product details.

## Installation

```bash
pip install mkdocs-product-catalog
```

## Usage

Add the plugin to `mkdocs.yml`:

```yaml
plugins:
  - search
  - product-catalog
```

Then place this tag anywhere in a markdown file to embed a catalog:

```html
<!-- product-catalog: dirname -->
```

`dirname` is the path to a directory of YAML files. Multiple tags can appear on the same page.

### Path resolution

**Absolute paths** (relative to `docs_dir`):
```html
<!-- product-catalog: catalog/platform_services -->
```

**Relative paths** (relative to the current file):
```html
<!-- product-catalog: ./services -->
<!-- product-catalog: ../shared/catalog -->
```

Paths starting with `./` or `../` are resolved relative to the current markdown file. All other paths are resolved from `docs_dir`. Relative paths are required when using [mkdocs-multirepo-plugin](#multirepo-compatibility).

## Navigation integration

The plugin automatically injects each catalog into the MkDocs navigation. Every product gets a nav link that opens its modal directly via a `#modal-{id}` hash anchor.

### Opt out per tag

Add `no-nav` to suppress nav injection for a specific catalog:

```html
<!-- product-catalog: ./internal no-nav -->
```

### Disable globally

```yaml
plugins:
  - product-catalog:
      nav_enabled: false
```

## Multirepo compatibility

The plugin works with [mkdocs-multirepo-plugin](https://github.com/jdoiro3/mkdocs-multirepo-plugin). Use relative paths in catalog tags so they resolve correctly inside each imported repo's temporary clone directory:

```yaml
# Root mkdocs.yml
plugins:
  - search
  - product-catalog
  - multirepo:
      cleanup: true

nav:
  - Home: index.md
  - Team Alpha: '!import https://github.com/your-org/team-alpha-docs?branch=main'
```

```markdown
<!-- In team-alpha-docs/docs/catalog.md -->
<!-- product-catalog: ./services -->
```

Nav links for imported repos are computed from MkDocs `Page.url`, so they remain correct regardless of where the plugin clones the source repository.

## Hash-based deep linking

Products can be linked to directly via `#modal-{id}` in the URL:

```
https://yoursite.com/catalog-page#modal-services-my-product-0
```

## Product YAML format

Each `.yaml` or `.yml` file in the directory represents one product:

```yaml
title: My Product                                  # required
description: A short description of the product.  # optional
icon: images/my_icon.png                           # optional
url: https://myproduct.example.com                 # optional
documentation:                                     # optional
  - url: https://docs.example.com/myproduct
    title: Official Documentation
    description: Comprehensive guide to the product
  - url: https://guide.example.com/user-guide
    title: User Guide
repository:                                        # optional
  - url: https://github.com/example/myproduct
    title: Main Repository
  - url: https://github.com/example/plugins
    title: Plugins Repository
owners:                                            # optional
  - Alice
  - Bob
metadata:                                          # optional — arbitrary key/value pairs
  team: platform
  sla: 99.9%
  dashboard: https://grafana.example.com/d/overview
```

Products are rendered in alphabetical order by filename.

### Icon

The `icon` value is used as the `src` of an `<img>` tag — use a path relative to the page the tag appears on, or an absolute URL. If omitted, an acronym (up to 3 initials) is shown in a colored circle instead.

### Documentation and Repository

Both fields support an array of links, each with an optional `title` and `description`. The legacy single-string format is also accepted:

```yaml
documentation: https://docs.example.com/myproduct
repository: https://github.com/example/myproduct
```

### Metadata

Any metadata value that contains a URL (`http://`, `https://`) is automatically rendered as a clickable link.

## Search

Product titles, descriptions, and owner names are included in a hidden element on the page so MkDocs search can index them.

## Logging

The plugin logs under the `mkdocs.plugins.product-catalog` logger. Use `mkdocs build --verbose` to see debug output.

## How it works

- The plugin scans all `.yaml` and `.yml` files in the specified directory.
- It renders a responsive button grid; each button shows the product icon or acronym and title.
- Clicking a button opens a modal with the product's description, URL, documentation, repository, owners, and metadata.
- The modal closes with the × button, by clicking the backdrop, or pressing Escape.
- Styles use MkDocs CSS custom properties and adapt to light and dark themes.
