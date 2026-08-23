# Adaptive Signals

*A compact two-column research example*

## Method

We estimate the response from noisy observations. The objective combines fit and regularization: $J(\theta)=\sum_i(y_i-f_\theta(x_i))^2+\lambda\lVert\theta\rVert^2$.

## Results

The optimum improved accuracy by 12.4%.^[Values are means over five seeded runs.]

| Condition | Accuracy | Samples |
| --- | --- | --- |
| Baseline | 81.2% | 240 |
| Adaptive | 93.6% | 240 |

Accuracy over five seeded runs
