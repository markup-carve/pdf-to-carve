CARVE-PDF · CLIENT-SIDE RENDERERS

# **Math, Diagrams and Charts**


Math and diagram fences are rendered **in the browser**, at print time: KaTeX typesets the math, Mermaid draws the

diagrams, Chart.js paints the charts. All three settle under one `window.__carveReady` promise that `print_cdp.py`

awaits, so nothing is half-drawn when the page is captured. Without the corresponding library installed, each construct

degrades to its readable source.

## **Inline and display math**


The mass-energy relation _E_ = _mc_ <sup>2</sup> appears inline in a sentence, while the Gaussian integral is shown as a centered

display equation:



∞




- _x_ <sup>2</sup>



​ _e_                                                   - _x_ <sup>2</sup> _dx_ =
∫−∞



_π_ ​



−∞



Another inline example: the quadratic roots _x_ = (− _b_ ± _b_ <u>2</u> <u>−4</u> _ac_ ​)/2 _a_ .

## **Diagrams**


A flowchart, rendered to inline SVG by Mermaid:


A second one, showing how the backends feed the same pipeline:


Page 1 of 3


## **Charts**

A `chart` fence carries a Chart.js config as JSON, drawn to a `<canvas>` :


Page 2 of 3


Point `CARVE_KATEX`, `CARVE_MERMAID` and `CARVE_CHART` at your installs, or let `crv2pdf` probe the usual locations.


By Mark Scherer · 2026-07-20


Page 3 of 3


