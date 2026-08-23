# Financial report

This synthetic report combines a numeric table, list, and visually distinct caution.
Carve represents the caution as an admonition. In the official Markdown export it
degrades to a bold label and paragraph, because ordinary Markdown has no
corresponding structure.

The table caption survives as text and loses its binding: Markdown tables have no
caption syntax, so the export writes the caption as an ordinary paragraph after
the table, which reads as a caption and is not one. This page used to say the
caption was absent, and its snapshot showed that - both were true of Carve
0.1.0, and the export learned to carry the text since.
