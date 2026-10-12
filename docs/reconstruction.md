# Reconstruction

REPO ALFA can build a local preview from frontend artifacts that were actually captured from the browser-visible application.

```bash
repo-alfa reconstruct https://example.com
```

The reconstruction engine:

- prefers the rendered DOM and falls back to the raw HTML;
- reads `assets/manifest.json`;
- copies captured assets into the reconstruction tree;
- rewrites `src`, `href`, `poster`, `data-src`, `srcset` and inline CSS `url(...)` references when a matching captured asset exists;
- writes `reconstruction.json` with provenance and rewrite counts;
- writes a small local `serve.py` helper.

Run the local preview:

```bash
cd output/example.com/reconstructed
python serve.py
```

Then open `http://127.0.0.1:8000`.

## Fidelity

A static reconstruction can reproduce only frontend resources and states that were captured. Server-side rendering logic, private APIs, authenticated backend state and unobserved runtime transitions are not synthesized. Use `repo-alfa visual-diff` to quantify screenshot similarity between the original capture and a reconstructed render.
