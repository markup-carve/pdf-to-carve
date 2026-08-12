## **Math, Diagrams and Charts**

Math and diagram fences are rendered **in the browser**, at print time: KaTeX typesets the math, Mermaid draws the diagrams, Chart.js paints the charts. All three settle under one window.\_\_carveReady promise that print\_cdp.py awaits, so nothing is half-drawn when the page is captured. Without the corresponding library installed, each construct degrades to its readable source.

## **Inline and display math**

The mass-energy relation appears inline in a sentence, while the Gaussian integral is shown as a centered display equation: *E* = *mc* 2

Another inline example: the quadratic roots . *x* = (−*b* ± *b* − 4*ac*)/2*a* 2

## **Diagrams**

A flowchart, rendered to inline SVG by Mermaid:

![](_page_0_Diagram_9.jpeg)

A second one, showing how the backends feed the same pipeline:

∫ *<sup>e</sup> dx* <sup>=</sup> −∞ ∞ −*x* 2 *π*

![](_page_1_Diagram_0.jpeg)

## **Charts**

A chart fence carries a Chart.js config as JSON, drawn to a <canvas> :

![](_page_2_Figure_0.jpeg)
