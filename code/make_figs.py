# -*- coding: utf-8 -*-
"""
ICCAI 论文数据图（简洁版，可复现）
图1: |x| 分布对比（箱线+散点+阈值线）
图2: 出界率对比（两柱+数值）
图3: 终点散点（跑道俯视，中线+边界+两组落点）
输出 300 dpi PNG 到本目录。
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import os, shutil, tempfile

OUT = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp()  # 纯 ASCII 临时目录，规避 PIL 中文路径保存问题

def save(fig, name):
    tmp = os.path.join(_TMP, name)
    fig.savefig(tmp, dpi=300, bbox_inches="tight")
    shutil.copy2(tmp, os.path.join(OUT, name))  # shutil 用宽字符 API，中文目录 OK
    plt.close(fig)

# ---- 数据 ----
B = np.array([5, 5, 7.5, 1.5, 28, 15, 30, 13.5, 7, 3,
              25, 39, 36, 1.5, 14, 11.5, 20, 28.5, 56.5, 35.5])   # 开环 |x| n=20
D = np.array([3, 0, 0.5, 0, 3, 5, 4.5, 3, 3.5, 5])                # 闭环 |x| n=10
THRESH = 3.75  # 出界阈值

B_xy = [(-5,63),(-5,43),(-7.5,66),(-1.5,66),(28,50.5),(15,65),(30,50),(13.5,59),
        (-7,43),(-3,66),(25,56),(39,43.5),(36,49),(-1.5,67),(-14,58.5),(-11.5,64),
        (20,37),(28.5,60),(56.5,37),(35.5,64)]
D_xy = [(-3,56.5),(0,52.5),(0.5,52.5),(0,54),(-3,58),(-5,58),(4.5,43.5),
        (-3,52.5),(-3.5,58),(5,61)]

B_out = int(np.sum(B > THRESH)); D_out = int(np.sum(D > THRESH))
fisher = stats.fisher_exact([[B_out, len(B)-B_out], [D_out, len(D)-D_out]])
mw = stats.mannwhitneyu(B, D, alternative="two-sided")
print(f"B mean={np.mean(B):.2f} D mean={np.mean(D):.2f}  MW p={mw.pvalue:.5f}")
print(f"出界 B={B_out}/{len(B)} D={D_out}/{len(D)}  Fisher p={fisher.pvalue:.5f}")

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
RED = "#d62728"; BLUE = "#1f77b4"; GRAY = "#777777"

# ============ 图1: |x| 分布对比 ============
fig, ax = plt.subplots(figsize=(5.0, 4.8), dpi=300)
bp = ax.boxplot([B, D], positions=[1, 2], widths=0.45, patch_artist=True,
                showfliers=True,
                medianprops=dict(color="black", lw=2.0),
                whiskerprops=dict(color="black", lw=1.2),
                capprops=dict(color="black", lw=1.2),
                flierprops=dict(marker="o", markersize=5,
                                markerfacecolor="none", markeredgewidth=1.3,
                                linestyle="none"))
for box, c in zip(bp["boxes"], [RED, BLUE]):
    box.set_facecolor(c); box.set_alpha(0.30); box.set_edgecolor(c); box.set_linewidth(1.2)
# 离群点（空心圈）按组着色（本数据无 1.5×IQR 之外的点，通常不出现）
for flier, c in zip(bp["fliers"], [RED, BLUE]):
    flier.set(markeredgecolor=c)

# 原始散点（实心 + 黑边 + 抖动）
rng = np.random.default_rng(0)
for i, (arr, c) in enumerate([(B, RED), (D, BLUE)]):
    ax.scatter(np.full(len(arr), i+1) + rng.normal(0, 0.04, len(arr)),
               arr, s=28, c=c, alpha=0.7, edgecolors="black",
               linewidths=0.3, zorder=3)

# 均值标注（箱外上方，统一 Mean = X cm）
ax.text(1, 22.5, f"Mean = {np.mean(B):.1f} cm", fontsize=8.5, color=RED,
        ha="center", fontweight="bold")
ax.text(2, 6.5, f"Mean = {np.mean(D):.1f} cm", fontsize=8.5, color=BLUE,
        ha="center", fontweight="bold")

# 阈值线
ax.axhline(THRESH, color=GRAY, ls="--", lw=1.0)
ax.text(0.42, 4.2, "Threshold: 3.75 cm", color=GRAY, fontsize=8, ha="left")

# 显著性标记 ***（居中，不顶图框）
ax.plot([1, 2], [64, 64], color="black", lw=1.0)
ax.text(1.5, 65.5, "***", ha="center", va="bottom", fontsize=13, fontweight="bold")

ax.set_xticks([1, 2])
ax.set_xticklabels(["Open-loop\n(n = 20)", "Closed-loop\n(n = 10)"], fontsize=10)
ax.set_ylabel("Absolute lateral drift |x| (cm)", fontsize=10)
ax.set_ylim(-1, 72)
ax.set_xlim(0.35, 2.65)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
save(fig, "fig1_x_distribution.png")

# ============ 图2: 出界率对比 ============
fig, ax = plt.subplots(figsize=(3.4, 3.8), dpi=300)
labels = ["Open-loop", "Closed-loop"]
rates = [B_out/len(B)*100, D_out/len(D)*100]
bars = ax.bar(labels, rates, width=0.55, color=[RED, BLUE])
for b, r, n_out, n in zip(bars, rates, [B_out, D_out], [len(B), len(D)]):
    ax.text(b.get_x()+b.get_width()/2, r+2, f"{r:.0f}%\n({n_out}/{n})",
            ha="center", fontsize=10, fontweight="bold")
ax.set_ylabel("Out-of-bounds rate (%)", fontsize=10)
ax.set_ylim(0, 100)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
save(fig, "fig2_out_of_bounds_rate.png")

# ============ 图3: 终点散点（开环 B / 闭环 D 分开两个子图） ============
B_x = np.array([p[0] for p in B_xy]); B_y = np.array([p[1] for p in B_xy])
D_x = np.array([p[0] for p in D_xy]); D_y = np.array([p[1] for p in D_xy])

fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.0), dpi=300, sharey=True)

for ax in axes:
    ax.axvline(0, color=GRAY, lw=1.0)
    ax.axvline(-THRESH, color="#6aa84f", ls="--", lw=1.0)
    ax.axvline(THRESH, color="#6aa84f", ls="--", lw=1.0)
    ax.spines[["top", "right"]].set_visible(False)

# 左：开环 B，宽轴
ax = axes[0]
ax.scatter(B_x, B_y, s=55, c=RED, marker="o", alpha=0.7,
           edgecolors="white", linewidths=0.5, zorder=3)
ax.set_xlim(-20, 60)
ax.set_title("Open-loop (n = 20)", fontsize=11)
ax.set_xlabel("Lateral deviation x (cm)", fontsize=10)

# 右：闭环 D，窄轴放大
ax = axes[1]
ax.scatter(D_x, D_y, s=75, c=BLUE, marker="^", alpha=0.95,
           edgecolors="white", linewidths=0.5, zorder=3)
ax.set_xlim(-8, 8)
ax.set_title("Closed-loop (n = 10)", fontsize=11)
ax.set_xlabel("Lateral deviation x (cm)", fontsize=10)

axes[0].set_ylabel("Forward distance y (cm)", fontsize=10)
axes[0].text(THRESH+0.6, 66, f"±{THRESH} cm", color="#6aa84f", fontsize=8)
fig.tight_layout()
save(fig, "fig3_endpoint_scatter.png")

print("done ->", OUT)
