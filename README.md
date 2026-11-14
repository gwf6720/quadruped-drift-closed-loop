# A Minimal Heading-Feedback Loop Reduces Lateral Drift in a Low-Cost Open-Loop Quadruped

Open data and code for the ICCAI 2027 paper:

> **A Minimal Heading-Feedback Loop Reduces Lateral Drift by 86% in a Low-Cost Open-Loop Quadruped**
> Gao, W.; Liu, Z.; Pang, J.; Wan, X. — Shaanxi University of Science and Technology
> ICCAI 2027 (13th International Conference on Computing and Artificial Intelligence), Seoul, South Korea.

## Summary

A low-cost servo quadruped (STM32F103C8T6 + 4×SG90 servos + MPU6050 + JDY-31) running the stock time-based open-loop gait drifts laterally and cannot hold a straight line. Over 20 open-loop trials the absolute lateral drift is **19.15 ± 15.15 cm** (median 14.5 cm), and **85%** of runs cross the track boundary. Adding a single-axis heading-feedback P-controller (dead zone 3°, gain 0.15, output limit ±12°, applied to the left-hind servo) reduces the drift to **2.75 cm** on the mean (**86% reduction**; median 79%), with Mann-Whitney and Welch tests both at p < 0.001 and Cohen's d = 1.31; the out-of-bounds rate falls to **30%**.

## Repository layout

```
data/     Raw trial data (x, y, pre/post battery voltage, trial order) for all series
code/     Python scripts that reproduce every figure and statistical test
firmware/ Firmware sources (self-test / E1 data-collection firmware) + reference
          implementation of the heading P-controller
figures/  Generated figures used in the paper (PNG, 300 dpi)
slip_traces/  Talc-powder slip-trace photographs (Series C)
```

## Data

- `data/series_B_openloop.csv` — open-loop baseline, n = 20 (clean ground, trim {-43, 0, 50, 0}).
- `data/series_D_closedloop.csv` — closed-loop, n = 10 (heading-feedback P-controller on; otherwise identical to B).
- `data/series_C_talc.csv` — talc-powder slip-amplification, n = 10 (x, y, and pre-run voltage complete; post-run voltage recorded for C1–C5 and C10).

Columns: `trial`, `date`, `pre_v` (V), `post_v` (V), `x_cm` (lateral endpoint deviation, + right / − left), `y_cm` (forward distance). The out-of-bounds threshold is |x| = 3.75 cm (leg spacing 7.5 cm, track width 15 cm).

## Reproducing the figures and statistics

```bash
cd code
python make_figs.py          # fig1 (|x| box plot), fig2 (out-of-bounds rate), fig3 (endpoint scatter)
python fig_signed_drift.py   # signed-drift bimodal distribution (histogram + KDE)
python drift_analysis.py     # Mann-Whitney / Welch / bootstrap / Fisher tests
python c_vs_b_analysis.py    # Series C vs B comparison (Mann-Whitney / Welch / bootstrap)
```

Requires `numpy`, `scipy`, `matplotlib`.

## Heading P-controller

The closed-loop controller (Section 3.3 of the paper) is a single-axis heading-feedback P-controller:

```
u = K_P * e,  K_P = 0.15,  dead zone = 3°,  |u| <= 12°
```

where `e` is the integrated yaw error (gyro z, zero-bias subtracted during a 3 s standing phase) and `u` is applied as a trim offset on the left-hind servo. A reference implementation is in `firmware/closed_loop_controller_reference.c`. The archived on-target firmware sources (self-test / E1 data-collection firmware with the same yaw integration) are in `firmware/`.

## Citation

```bibtex
@inproceedings{gao2026heading,
  author    = {Gao, Weifeng and Liu, Zhihao and Pang, Jinwen and Wan, Xinze},
  title     = {A Minimal Heading-Feedback Loop Reduces Lateral Drift by 86\% in a Low-Cost Open-Loop Quadruped},
  booktitle = {13th International Conference on Computing and Artificial Intelligence (ICCAI 2027)},
  year      = {2027},
  address   = {Seoul, South Korea}
}
```

## License

Data and code are released under the MIT License (see LICENSE).
