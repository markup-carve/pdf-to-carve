## Math, Diagrams and Charts

Math and diagram fences are rendered in the browser, at print time: KaTeX typesets the math, Mermaid draws the diagrams, Chart.js paints the charts. All three settle under one window.\_\_carveReady promise that print\_cdp.py awaits, so nothing is half-drawn when the page is captured. Without the corresponding library installed, each construct degrades to its readable source

## Inline and display math

The mass-energy relation $E = m c ^ { 2 }$ appears inline in a sentence, while the Gaussian integral is shown as a centered display equation:

$$
\int _ { - \infty } ^ { \infty } e ^ { - x ^ { 2 } } d x = { \sqrt { \pi } }
$$

Another inline example: the quadratic roots $x = ( - b \pm \sqrt { b ^ { 2 } - 4 a c } ) / 2 a$ .

## Diagrams

A flowchart, rendered to inline SVG by Mermaid:

![](images/92f9dabed0bc05a62a4289f4c129c2ef3e325486928dd3822d2315c0a0acfd10.jpg)

A second one, showing how the backends feed the same pipeline:

![](images/7426020535a7ae64224ad3bd797e91ec17aa3c28e9fd492e364eea07a8cfe57a.jpg)

## Charts

A chart fence carries a Chart.js config as JSON, drawn to a <canvas> :
