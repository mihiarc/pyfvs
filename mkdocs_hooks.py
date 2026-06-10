"""MkDocs build hooks.

Workaround for a pymdown-extensions + Pygments incompatibility:
`pymdownx.highlight` passes ``filename=None`` to Pygments' ``HtmlFormatter``
for code blocks without an explicit title, and current Pygments releases call
``html.escape(None)`` on that value, which raises ``AttributeError``. Coerce a
``None`` filename to an empty string so the documentation builds cleanly.

Referenced from ``mkdocs.yml`` via the top-level ``hooks:`` key.
"""

from pygments.formatters.html import HtmlFormatter

_original_init = HtmlFormatter.__init__


def _patched_init(self, **options):
    if options.get("filename") is None:
        options["filename"] = ""
    _original_init(self, **options)


# Apply once at import time, before any Markdown conversion runs.
if getattr(HtmlFormatter.__init__, "__name__", "") != "_patched_init":
    HtmlFormatter.__init__ = _patched_init
