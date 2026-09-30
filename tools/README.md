# Thrive redesign tools

The site in `../site` is generated. Edit `site.css`, `site.js` or `build.py`, then rebuild:

```sh
python3 -m venv .venv && .venv/bin/pip install beautifulsoup4 pillow
.venv/bin/python build.py            # writes ../site and ../netlify.toml
```

- `content.json` holds each page's copy and layout (sections > rows > columns > modules),
  extracted from the original Divi site by `extract.py`.
- The build reads original images and SEO tags from a checkout of the `main` branch
  (default `~/Sites/thrive-site-main`, override with `THRIVE_SRC`):
  `git worktree add ~/Sites/thrive-site-main main`
