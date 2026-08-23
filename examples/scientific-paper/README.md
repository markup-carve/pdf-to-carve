# Scientific paper

This synthetic two-column page combines reading order, display math, a footnote,
and a compact results table. The ground truth uses typed math and an inline footnote.

Carve retains those meanings directly. Its Markdown export uses math and inline
footnote extensions, which are not portable across all renderers, and the table
caption survives as an ordinary paragraph after the table - Markdown tables have
no caption syntax, so the text carries over and the binding does not. This page
used to say the caption was absent, which was true of Carve 0.1.0.
