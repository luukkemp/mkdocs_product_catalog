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

`dirname` is the path to a directory of YAML files, relative to your `docs/` folder.

**Important**: Each catalog tag should be on a separate page. While you can technically place multiple catalog tags on the same page, this is not recommended because:

1. **Navigation Confusion**: Multiple catalogs on one page create ambiguous navigation structure
2. **User Experience**: Users expect each catalog to have its own dedicated page
3. **Maintenance**: Separate pages make it easier to manage and update catalogs independently

**Recommended approach**: Create separate pages for each catalog:

```markdown
# Platform Tools (platform_tools.md)

<!-- product-catalog: catalog/platform -->
```

```markdown
# Data Tools (data_tools.md)

<!-- product-catalog: catalog/data -->
```

## Product YAML format

Each `.yaml` or `.yml` file in the directory represents one product:

```yaml
title: My Product                                  # required
description: A short description of the product.  # optional
icon: images/my_icon.png                           # optional
url: https://myproduct.example.com                 # optional
documentation:                                    # optional - array format
  - url: https://docs.example.com/myproduct       # URL required
    title: Official Documentation                   # optional title override
    description: Comprehensive guide to the product # optional description
  - url: https://guide.example.com/user-guide       # Multiple links supported
    title: User Guide                                # Custom display title
    description: Step-by-step tutorials               # Additional context
repository:                                      # optional - array format
  - url: https://github.com/example/myproduct      # URL required
    title: Main Repository                          # optional title override
    description: Official source code repository     # optional description
  - url: https://github.com/example/plugins         # Multiple repos supported
    title: Plugins Repository                       # Custom display title
    description: Official and community plugins      # Additional context
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

Both `documentation` and `repository` fields support array format for multiple links:

```yaml
documentation:
  - url: https://docs.example.com          # Required: URL
    title: Official Documentation           # Optional: Custom display title
    description: Comprehensive API reference # Optional: Additional context
  - url: https://guides.example.com
    title: Getting Started Guide
    description: Beginner tutorials
```

Each array item creates a separate link in the modal with optional title and description.

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
