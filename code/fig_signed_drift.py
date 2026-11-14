# -*- coding: utf-8 -*-
"""
ICCAI 论文数据图（新增）：带符号横向漂移 x 的双模分布（B 系列，n=20）
回应审稿意见 #4：明确 "bimodal" 指带符号 x 的左/右两簇（非 |x| 双峰），
并给出图形证据（直方图 + 核密度 + 两簇均值 + 间隙标注）。
输出 300 dpi PNG。
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import os, shutil, tempfile

# ---- B 系列带符号 x（cm，+右 / -左，n=20）----
x = np.array([-5, -5, -7.5, -1.5, 28, 15, 30, 13.5, -7, -3,
              25, 39, 36, -1.5, -14, -11.5, 20, 28.5, 56.5, 35.5])
left = x[x < 0]
right = x[x > 0]

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
RED = "#d62728"; BLUE = "#1f77b4"; GRAY = "#777777"

fig, ax = plt.subplots(figsize=(6.2, 3.9), dpi=300)

# 直方图（带符号 x）
bins = np.arange(-20, 65, 7.5)
ax.hist(x, bins=bins, color=GRAY, alpha=0.45, edgecolor="black", linewidth=0.5,
        density=True, label="Signed drift (n = 20)")

# 核密度估计，展示双峰
kde = stats.gaussian_kde(x, bw_method=0.45)
xs = np.linspace(-20, 62, 400)
ax.plot(xs, kde(xs), color="black", lw=1.6, label="Kernel density")

# 两簇均值
lm, rm = left.mean(), right.mean()
ax.axvline(lm, color=BLUE, ls="--", lw=1.2)
ax.axvline(rm, color=RED, ls="--", lw=1.2)

# 顶部标注两簇
ax.annotate("Left mode\n(n = 9, mean %.1f cm)" % lm, xy=(lm, kde(lm)[0]),
            xytext=(-16, 0.052), fontsize=8, color=BLUE, ha="left")
ax.annotate("Right mode\n(n = 11, mean %.1f cm)" % rm, xy=(rm, kde(rm)[0]),
            xytext=(18, 0.052), fontsize=8, color=RED, ha="left")

# 间隙标注
ax.annotate("", xy=(-1.5, 0.055), xytext=(13.5, 0.055),
            arrowprops=dict(arrowstyle="<->", color="black", lw=1.0))
ax.text(6.0, 0.057, "gap", fontsize=8, ha="center", color="black")

ax.set_xlabel("Signed lateral drift x (cm, + right / - left)", fontsize=10)
ax.set_ylabel("Density", fontsize=10)
ax.set_ylim(0, 0.065)
ax.set_xlim(-20, 62)
ax.legend(fontsize=8, loc="upper right", frameon=False)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()

_TMP = tempfile.mkdtemp()
tmp = os.path.join(_TMP, "fig_signed_drift.png")
fig.savefig(tmp, dpi=300, bbox_inches="tight")
# 输出到 02_数据图 与 03_初稿/figs（供编译）
out_dirs = [
    os.path.dirname(os.path.abspath(__file__)),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "03_初稿", "figs"),
]
for d in out_dirs:
    d = os.path.normpath(d)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(tmp, os.path.join(d, "fig_signed_drift.png"))
plt.close(fig)
print("saved fig_signed_drift.png to:", out_dirs)
print("left n=%d mean=%.2f  right n=%d mean=%.2f" % (len(left), lm, len(right), rm))
