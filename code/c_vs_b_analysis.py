# -*- coding: utf-8 -*-
"""C(粉面) vs B(干净地面) 开环漂移对比（ICCAI 用）
核心问题：滑石粉(均匀降摩擦) 是否放大横向漂移？
方法：描述统计、|x| 与 x 的 Mann-Whitney / Welch t、bootstrap 均值差 CI、
      组内 电压~漂移/前进距离 相关、左右漂移量级不对称。
"""
import sys
import numpy as np
from scipy import stats
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# B 系列（trim+50，干净地面，n=20）
B = dict(
    x    = np.array([-5,-5,-7.5,-1.5,28,15,30,13.5,-7,-3,25,39,36,-1.5,-14,-11.5,
                     20,28.5,56.5,35.5]),
    y    = np.array([63,43,66,66,50.5,65,50,59,43,66,56,43.5,49,67,58.5,64,37,60,37,64]),
    Vpre = np.array([4.136,4.111,4.180,4.134,4.115,4.174,4.133,4.113,4.176,4.141,
                     4.117,4.170,4.131,4.111,4.168,4.129,4.108,4.168,4.130,4.108]),
)

# C 系列（trim+50，粉面/滑石粉，n=10）
C = dict(
    x    = np.array([-13,-13.5,13,27,3,-2,-6,-0.5,5.5,34.5]),
    y    = np.array([43,55,51,43.5,55,28,57,53,53,48]),
    Vpre = np.array([4.148,4.121,4.100,4.161,4.114,4.094,4.172,4.125,4.110,4.092]),
)

def corr(a, b, name):
    if len(a) < 3 or np.allclose(a, a[0]) or np.allclose(b, b[0]):
        print(f"  {name}: n={len(a)} 常量/样本不足，跳过")
        return
    rp, pp = stats.pearsonr(a, b)
    rs, ps = stats.spearmanr(a, b)
    print(f"  {name}: n={len(a)} | Pearson r={rp:+.3f} p={pp:.3f} | Spearman rho={rs:+.3f} p={ps:.3f}")

def mw_welch(a, b, name):
    a = np.asarray(a, float); b = np.asarray(b, float)
    U, p_u = stats.mannwhitneyu(a, b, alternative='two-sided')
    t, p_t = stats.ttest_ind(a, b, equal_var=False)
    print(f"  {name}: Mann-Whitney U p={p_u:.4f} | Welch t={t:+.3f} p={p_t:.4f}")
    print(f"          C: mean={a.mean():+.2f} median={np.median(a):+.2f} n={len(a)}")
    print(f"          B: mean={b.mean():+.2f} median={np.median(b):+.2f} n={len(b)}")

def boot_diff_ci(a, b, B=20000, seed=0):
    rng = np.random.default_rng(seed)
    a = np.asarray(a, float); b = np.asarray(b, float)
    na, nb = len(a), len(b)
    diffs = np.empty(B)
    for i in range(B):
        sa = a[rng.integers(0, na, na)]
        sb = b[rng.integers(0, nb, nb)]
        diffs[i] = sa.mean() - sb.mean()
    return diffs

print("="*72)
print("【1】描述统计")
print("="*72)
for nm, d in [("B(干净地面)", B), ("C(粉面)", C)]:
    ax = np.abs(d['x'])
    print(f"{nm}: n={len(d['x'])}")
    print(f"  x : min={d['x'].min():+.1f} max={d['x'].max():+.1f} mean={d['x'].mean():+.2f} std={d['x'].std(ddof=1):.2f}")
    print(f"  |x|: mean={ax.mean():.2f} std={ax.std(ddof=1):.2f} median={np.median(ax):.2f}")
    print(f"  y : mean={d['y'].mean():.1f} std={d['y'].std(ddof=1):.1f} min={d['y'].min():.1f} max={d['y'].max():.1f}")
    print(f"  Vpre: mean={d['Vpre'].mean():.4f} 范围[{d['Vpre'].min():.4f},{d['Vpre'].max():.4f}]")

print()
print("="*72)
print("【2】核心对比：C(粉面) vs B(干净) 的横向漂移")
print("="*72)
print("--- |x|（漂移量级，论文主指标）---")
mw_welch(np.abs(C['x']), np.abs(B['x']), "|x|")
print("--- x（带符号漂移，方向）---")
mw_welch(C['x'], B['x'], "x")

print()
print("  |x| 均值差 bootstrap 95% CI（C - B，负值=C 更小）:")
d = boot_diff_ci(np.abs(C['x']), np.abs(B['x']))
lo, hi = np.percentile(d, [2.5, 97.5])
p_two = 2*min((d < 0).mean(), (d > 0).mean())
print(f"    均值差 = {d.mean():+.2f} cm, 95% CI = [{lo:+.2f}, {hi:+.2f}], 双侧 p={p_two:.4f}")
print(f"    (CI 全在 0 左侧 → C 显著小于 B；跨 0 → 无显著差异)")

print()
print("="*72)
print("【3】C 系列组内：电压 ~ 漂移 / 前进距离")
print("="*72)
corr(C['x'], C['Vpre'], "x vs Vpre")
corr(np.abs(C['x']), C['Vpre'], "|x| vs Vpre")
corr(C['y'], C['Vpre'], "y vs Vpre")
corr(C['x'], C['y'], "x vs y")
# 低电(<=4.10) vs 满电(>4.10) 的 y 与 |x|
low = C['Vpre'] <= 4.10
print(f"  按 Vpre<=4.10 分组:")
print(f"    满电组 n={int((~low).sum())}: y mean={C['y'][~low].mean():.1f}, |x| mean={np.abs(C['x'][~low]).mean():.2f}")
print(f"    低电组 n={int(low.sum())}:   y mean={C['y'][low].mean():.1f}, |x| mean={np.abs(C['x'][low]).mean():.2f}")
if low.sum() >= 2 and (~low).sum() >= 2:
    U, pu = stats.mannwhitneyu(C['y'][low], C['y'][~low], alternative='two-sided')
    print(f"    y(满电 vs 低电) Mann-Whitney p={pu:.4f}")

print()
print("="*72)
print("【4】左右漂移量级不对称（C 系列）")
print("="*72)
right = C['x'][C['x'] > 0]; left = C['x'][C['x'] < 0]
print(f"  右偏 {len(right)} 组: mean |x|={np.abs(right).mean():.2f}  值={right.tolist()}")
print(f"  左偏 {len(left)} 组: mean |x|={np.abs(left).mean():.2f}  值={left.tolist()}")
if len(right) >= 2 and len(left) >= 2:
    U, pu = stats.mannwhitneyu(np.abs(right), np.abs(left), alternative='two-sided')
    print(f"  右偏量级 vs 左偏量级 Mann-Whitney p={pu:.4f}")
print(f"  (B 系列对照: 右偏 {int((B['x']>0).sum())} 组 mean|R|={np.abs(B['x'][B['x']>0]).mean():.2f}, "
      f"左偏 {int((B['x']<0).sum())} 组 mean|L|={np.abs(B['x'][B['x']<0]).mean():.2f})")
