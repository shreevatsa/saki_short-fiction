# Story annotations web page

This is a static page that loads `annotations/stories.json` and shows all 142 stories, sortable and filterable.

## Run locally

From the repo root:

```sh
python3 -m http.server
```

Then open:

```text
http://localhost:8000/web/
```

The page will also try to load `annotations/wikisource_urls.json` (if present) to show Wikisource links.

