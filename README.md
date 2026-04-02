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

```
<!-- product-catalog: dirname -->
```

`dirname` is the path to a directory of YAML files, relative to your `docs/` folder. The tag can appear on any page, any number of times, each pointing to a different directory:

```markdown
# Platform Tools

<!-- product-catalog: catalog/platform -->

# Data Tools

<!-- product-catalog: catalog/data -->
```

## Product YAML format

Each `.yaml` or `.yml` file in the directory represents one product:

```yaml
title: My Product                                  # required
description: A short description of the product.  # optional
icon: images/my_icon.png                           # optional
url: https://myproduct.example.com                 # optional
documentation: https://docs.example.com/myproduct # optional
repository: https://github.com/example/myproduct  # optional
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

### Metadata

Any metadata value that contains a URL (`http://`, `https://`) is automatically rendered as a clickable link.

## Search

Product titles, descriptions, and owner names are included in a hidden element on the page so MkDocs search can index them. Searching for a product title will surface the page it appears on.

## How it works

- The plugin scans all `.yaml` and `.yml` files in the specified directory.
- It renders a responsive button grid; each button shows the product icon or acronym and title.
- Clicking a button opens a modal with the product's description, URL, documentation, repository, owners, and metadata.
- The modal closes with the × button, by clicking the backdrop, or pressing Escape.
- Styles use MkDocs CSS custom properties and adapt to light and dark themes.
