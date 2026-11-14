# -*- coding: utf-8 -*-
"""A/B 开环漂移数据的高级统计分析（ICCAI 用）
方法：Pearson/Spearman 相关、Silverman 双模 bootstrap 检验、GMM(BIC)、
      Runs 检验(非平稳)、lag-1 自相关、Mann-Whitney、多元回归、bootstrap CI。
"""
import sys
import numpy as np
from scipy import stats
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ---------------- 数据 ----------------
# A 系列（trim+47，开环 120s，全右偏）
A = dict(
    Vpre =np.array([3.913, 4.105, 4.091, 4.083, 4.072, 4.058]),
    Vpost=np.array([3.895, 4.093, 4.081, 4.073, 4.064, 4.057]),
    x    =np.array([50.0,  33.5,  15.0,  34.5,  27.5,  20.0]),
    y    =np.array([21.5,  39.0,  57.0,  48.5,  49.0,  25.0]),
)

# B 系列（trim+50，开环 120s，双模）
B = dict(
    Vpre =np.array([4.136,4.111,4.180,4.134,4.115,4.174,4.133,4.113,4.176,4.141,
                    4.117,4.170,4.131,4.111,4.168,4.129,4.108,4.168,4.130,4.108]),
    Vpost=np.array([4.107,4.099,4.136,4.113,4.098,4.133,4.117,4.093,4.140,4.115,
                    4.100,4.131,4.109,4.094,4.128,4.106,4.095,4.130,4.103,4.095]),
    x    =np.array([-5,-5,-7.5,-1.5,28,15,30,13.5,-7,-3,25,39,36,-1.5,-14,-11.5,
                    20,28.5,56.5,35.5]),
    y    =np.array([63,43,66,66,50.5,65,50,59,43,66,56,43.5,49,67,58.5,64,37,60,37,64]),
)
B['dV'] = (B['Vpre'] - B['Vpost']) * 1000.0  # mV
B['order'] = np.arange(1, 21)
A['dV'] = (A['Vpre'] - A['Vpost']) * 1000.0

def corr(x, y, name):
    if len(x) < 3 or np.allclose(x, x[0]) or np.allclose(y, y[0]):
        print(f"  {name}: n={len(x)} 常量/样本不足，跳过")
        return None
    rp, pp = stats.pearsonr(x, y)
    rs, ps = stats.spearmanr(x, y)
    print(f"  {name}: n={len(x)} | Pearson r={rp:+.3f} p={pp:.3f} | Spearman rho={rs:+.3f} p={ps:.3f}")
    return rp, pp, rs, ps

def bootstrap_ci(x, y, B=2000, seed=0, method='pearson'):
    rng = np.random.default_rng(seed)
    n = len(x); vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        if method == 'pearson':
            r, _ = stats.pearsonr(x[idx], y[idx])
        else:
            r, _ = stats.spearmanr(x[idx], y[idx])
        if np.isfinite(r):
            vals.append(r)
    vals = np.array(vals)
    return np.percentile(vals, [2.5, 97.5])

# ---------------- KDE 模态计数 & Silverman 临界带宽 ----------------
def kde_modes(data, h, grid=4000):
    """Gaussian KDE 在给定带宽 h 下的局部极大值个数"""
    lo, hi = data.min()-3*h, data.max()+3*h
    g = np.linspace(lo, hi, grid)
    if h <= 0:
        return 0, g
    # 向量化 KDE
    d = g[:, None] - data[None, :]
    dens = np.exp(-0.5*(d/h)**2).sum(axis=1) / (len(data)*h*np.sqrt(2*np.pi))
    # 局部极大值
    nm = 0
    for i in range(1, grid-1):
        if dens[i] > dens[i-1] and dens[i] >= dens[i+1]:
            nm += 1
    return nm, g

def critical_bandwidth(data, k=1, lo=1e-4, hi=None):
    """最小的带宽使 KDE 模态数 <= k（Silverman 临界带宽 h_k）"""
    if hi is None:
        hi = np.std(data)*5 + 1e-3
    # 先找上界：足够大的 h 只有 1 个模态
    h = hi
    while kde_modes(data, h)[0] > k and h < 1e4:
        h *= 2
    hi = h
    for _ in range(60):  # 二分
        mid = (lo+hi)/2
        if kde_modes(data, mid)[0] <= k:
            hi = mid
        else:
            lo = mid
    return hi

def silverman_test(data, B=500, seed=1, k=1):
    """Silverman(1981) 双模检验：H0=单峰，p 小则拒绝单峰(双模)。
    返回 (h_crit_obs, p_value)"""
    rng = np.random.default_rng(seed)
    n = len(data)
    h_obs = critical_bandwidth(data, k)
    cnt = 0
    for _ in range(B):
        idx = rng.integers(0, n, n)
        try:
            hb = critical_bandwidth(data[idx], k)
        except Exception:
            continue
        if hb >= h_obs:
            cnt += 1
    p = (cnt + 1) / (B + 1)
    return h_obs, p

# ---------------- 1D GMM (EM) ----------------
def gmm_fit(data, k=2, maxit=200, tol=1e-8, seed=0):
    rng = np.random.default_rng(seed)
    n = len(data)
    x = data.reshape(-1, 1)
    # 初始化
    if k == 1:
        means = np.array([data.mean()])
    else:
        q = np.quantile(data, np.linspace(0, 1, k+2)[1:-1])
        means = q.reshape(-1).astype(float)
    vars_ = np.full(k, np.var(data)*(0.5+0.5/k))
    pi = np.full(k, 1.0/k)
    ll_old = -np.inf
    for _ in range(maxit):
        # E-step
        resp = np.zeros((n, k))
        for j in range(k):
            resp[:, j] = pi[j] * np.exp(-0.5*((data-means[j])**2)/vars_[j]) / np.sqrt(2*np.pi*vars_[j])
        s = resp.sum(axis=1, keepdims=True)
        s[s == 0] = 1e-300
        resp /= s
        # M-step
        Nk = resp.sum(axis=0) + 1e-300
        means = (resp * x).sum(axis=0) / Nk
        vars_ = (resp * (x - means)**2).sum(axis=0) / Nk + 1e-6
        pi = Nk / Nk.sum()
        # log-likelihood（混合分布，正确形式）
        dens = np.zeros(n)
        for j in range(k):
            dens += pi[j]*np.exp(-0.5*((data-means[j])**2)/vars_[j])/np.sqrt(2*np.pi*vars_[j])
        ll = np.sum(np.log(dens + 1e-300))
        if abs(ll - ll_old) < tol:
            break
        ll_old = ll
    nparam = k*2 + (k-1)  # means + vars + weights(独立个数 k-1)
    bic = nparam*np.log(n) - 2*ll
    aic = 2*nparam - 2*ll
    return dict(means=means, vars=vars_, pi=pi, ll=ll, bic=bic, aic=aic, nparam=nparam)

# ---------------- Runs 检验（非平稳/聚集） ----------------
def runs_test(data):
    """对正负号序列做 Wald-Wolfowitz runs 检验。返回 (R, E, Var, Z, p)"""
    s = np.sign(data)
    s = s[s != 0]
    n1 = int((s > 0).sum()); n2 = int((s < 0).sum())
    R = 1 + int(np.sum(s[1:] != s[:-1]))
    if n1 == 0 or n2 == 0:
        return R, np.nan, np.nan, np.nan, np.nan
    E = 2.0*n1*n2/(n1+n2) + 1
    Var = 2.0*n1*n2*(2.0*n1*n2-n1-n2)/((n1+n2)**2*(n1+n2-1))
    Z = (R - E)/np.sqrt(Var)
    p = 2*stats.norm.sf(abs(Z))
    return R, E, Var, Z, p

def lag1_autocorr(x):
    x = x - x.mean()
    return np.sum(x[:-1]*x[1:])/np.sum(x*x)

# ================= 输出 =================
print("="*70)
print("【1】描述统计")
print("="*70)
for nm, d in [("A(trim+47)", A), ("B(trim+50)", B)]:
    print(f"{nm}: n={len(d['x'])}")
    print(f"  x:  min={d['x'].min():+.1f} max={d['x'].max():+.1f} mean={d['x'].mean():+.2f} std={d['x'].std(ddof=1):.2f}")
    print(f"  |x|: mean={np.abs(d['x']).mean():.2f} std={np.abs(d['x']).std(ddof=1):.2f}")
    print(f"  y:  mean={d['y'].mean():.1f} std={d['y'].std(ddof=1):.1f}")
    print(f"  Vpre: mean={d['Vpre'].mean():.4f} 范围 [{d['Vpre'].min():.4f},{d['Vpre'].max():.4f}]")

print()
print("="*70)
print("【2】相关分析（x 横向漂移 与 各变量）")
print("="*70)
print("--- A 系列（trim+47，n=6）---")
corr(A['x'], A['Vpre'], "x vs Vpre")
corr(A['x'][1:], A['Vpre'][1:], "x vs Vpre (去低电点,n=5)")
corr(A['x'], A['y'], "x vs y")
corr(A['Vpre'], A['y'], "Vpre vs y")
print("--- B 系列（trim+50，n=20）---")
corr(B['x'], B['Vpre'], "x vs Vpre")
corr(np.abs(B['x']), B['Vpre'], "|x| vs Vpre")
corr(B['x'], B['Vpost'], "x vs Vpost")
corr(B['x'], B['dV'], "x vs dV(mV)")
corr(B['x'], B['y'], "x vs y")
corr(B['x'], B['order'], "x vs trial顺序")
corr(B['y'], B['Vpre'], "y vs Vpre")

print()
print("--- B 系列 关键相关的 bootstrap 95% CI（看稳定性）---")
for (name, a, b) in [("x~Vpre", B['x'], B['Vpre']),
                     ("|x|~Vpre", np.abs(B['x']), B['Vpre']),
                     ("x~y", B['x'], B['y']),
                     ("x~顺序", B['x'], B['order'])]:
    ci = bootstrap_ci(a, b)
    print(f"  {name}: Pearson 95% CI = [{ci[0]:+.3f}, {ci[1]:+.3f}]")

print()
print("="*70)
print("【3】双模性检验（B 系列）")
print("="*70)
h_obs, p_silv = silverman_test(B['x'], B=1000)
print(f"  Silverman 双模 bootstrap 检验: 临界带宽 h_crit={h_obs:.3f}, p={p_silv:.3f}")
print(f"    (p<0.05 拒绝单峰 H0 → 支持双模；p 大则无法拒绝单峰)")
for k in (1, 2, 3):
    m = gmm_fit(B['x'], k=k)
    print(f"  GMM k={k}: BIC={m['bic']:.1f} AIC={m['aic']:.1f} LL={m['ll']:.1f} "
          f"means={np.round(m['means'],1)} vars={np.round(m['vars'],1)} pi={np.round(m['pi'],2)}")
# 用最大后验分类
m2 = gmm_fit(B['x'], k=2)
resp = np.zeros((len(B['x']), 2))
for j in range(2):
    resp[:, j] = m2['pi'][j]*np.exp(-0.5*((B['x']-m2['means'][j])**2)/m2['vars'][j])/np.sqrt(2*np.pi*m2['vars'][j])
lab = resp.argmax(axis=1)
print(f"  GMM k=2 分类: 左模 {int((lab==0).sum())} 组, 右模 {int((lab==1).sum())} 组")

print()
print("="*70)
print("【4】非平稳性 / 时序结构（B 系列）")
print("="*70)
R, E, V, Z, p_runs = runs_test(B['x'])
print(f"  Runs 检验(正负号): R={R}, E[R]={E:.2f}, Z={Z:+.2f}, p={p_runs:.3f}")
print(f"    (p<0.05 → 符号聚集，非独立随机 → 有时序结构/非平稳)")
print(f"  lag-1 自相关 r1 = {lag1_autocorr(B['x']):+.3f}")
print(f"  x 序列: {B['x'].tolist()}")

print()
print("="*70)
print("【5】A vs B 分布比较（注意：trim 不同，混杂）")
print("="*70)
U, p_u = stats.mannwhitneyu(A['x'], B['x'], alternative='two-sided')
t, p_t = stats.ttest_ind(A['x'], B['x'], equal_var=False)
print(f"  Mann-Whitney U: p={p_u:.3f} | Welch t: t={t:+.2f}, p={p_t:.3f}")
print(f"  A x 均值={A['x'].mean():+.1f} (全右) vs B x 均值={B['x'].mean():+.1f} (双模)")
print(f"  ⚠️ A=trim+47, B=trim+50，两实验条件不同，此比较不能归因于单一变量")

print()
print("="*70)
print("【6】多元线性回归 x ~ Vpre + order（B 系列）")
print("="*70)
X = np.column_stack([np.ones(len(B['x'])), B['Vpre'], B['order']])
beta, res, rank, sv = np.linalg.lstsq(X, B['x'], rcond=None)
pred = X @ beta
sse = np.sum((B['x']-pred)**2)
sst = np.sum((B['x']-B['x'].mean())**2)
R2 = 1 - sse/sst
n, p = len(B['x']), 3
adjR2 = 1 - (1-R2)*(n-1)/(n-p)
# 标准误 & t 检验
dof = n - p
sigma2 = sse/dof
XtX_inv = np.linalg.inv(X.T @ X)
se = np.sqrt(np.diag(sigma2 * XtX_inv))
tv = beta/se
pv = 2*stats.t.sf(np.abs(tv), dof)
print(f"  R²={R2:.3f}  adjR²={adjR2:.3f}  (n={n})")
for name, b_, se_, t_, p_ in zip(['截距','Vpre','顺序'], beta, se, tv, pv):
    print(f"  {name}: beta={b_:+.3f} ± {se_:.3f}  t={t_:+.2f}  p={p_:.3f}")
print("  注: 截距=0 处 Vpre 无量纲意义(需中心化)；中心化后看斜率更直观")
Xc = np.column_stack([np.ones(n), B['Vpre']-B['Vpre'].mean(), B['order']-B['order'].mean()])
beta_c, *_ = np.linalg.lstsq(Xc, B['x'], rcond=None)
print(f"  中心化回归: 截距={beta_c[0]:+.2f}cm(均值处), Vpre斜率={beta_c[1]:+.1f}cm/V, 顺序斜率={beta_c[2]:+.2f}cm/组")
