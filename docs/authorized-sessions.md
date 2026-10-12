# Authorized authenticated captures

REPO ALFA can load a Playwright `storage_state` JSON that you created from a browser session you are authorized to use.

```bash
repo-alfa forensic https://app.example.com \
  --storage-state ./my-authorized-state.json
```

The same option is available on `capture`, `deep`, `forensic`, `exhaustive` and `reconstruct`.

## Privacy behavior

The input storage-state file may contain session material. Treat it like a credential and do not commit it to Git. REPO ALFA uses it only to initialize the local Playwright browser context. Persisted evidence redacts request/response authorization and cookie headers, and cookie output stores metadata/attributes rather than cookie values.

## UI-state exploration

By default the browser capture explores a bounded set of low-risk UI disclosure surfaces:

- elements with `role="tab"`;
- buttons with `aria-expanded`;
- `summary` elements.

It does not automatically submit forms or click arbitrary action buttons. Each explored state can preserve a DOM snapshot and screenshot under `ui/states/`.

Control it with:

```bash
repo-alfa deep https://app.example.com --max-ui-states 50
repo-alfa deep https://app.example.com --no-explore-ui
```

This feature is intended for applications you own or are authorized to analyze. It is not an authentication-bypass mechanism.
