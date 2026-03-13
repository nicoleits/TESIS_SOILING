"""
Concordancia intermetodológica: matrices y gráficos entre todas las metodologías de SR.

Usa SR semanal Q25 normalizado (analysis/stats/sr_semanal_norm.csv). PVStand e IV600
son las series ya corregidas por temperatura (SR_Pmax_corr, SR_Isc_corr, etc.).

Salidas en analysis/concordancia/:
  matriz_correlacion.csv       : correlación de Pearson entre pares
  matriz_correlacion_spearman.csv : correlación de Spearman
  matriz_ccc_lin.csv           : CCC de Lin entre pares
  concordancia_pares.csv       : por par: n, r, p, rho, CCC, bias (pp), SD dif., LoA, RMSE
  heatmap_concordancia.png     : heatmap de correlaciones Pearson con n por celda
  heatmap_ccc_lin.png          : heatmap del CCC de Lin con n por celda
  scatter_concordancia.png     : matriz de dispersión entre metodologías
  README.md                    : descripción de salidas

Uso (desde TESIS_SOILING):
  python -m analysis.concordancia.concordancia_intermetodologica
"""
import os
import sys
import logging
import itertools

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import locale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    try:
        locale.setlocale(locale.LC_NUMERIC, "es_ES.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_NUMERIC, "es_ES")
        except locale.Error:
            pass
    plt.rcParams["axes.formatter.use_locale"] = True
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

ALPHA = 0.05


def ccc_lin(x, y):
    """
    Coeficiente de Correlación de Concordancia de Lin (CCC).
    Combina precisión (r de Pearson) y exactitud (cercanía a la línea de identidad).
    CCC = 2·r·Sx·Sy / (Sx² + Sy² + (μx − μy)²)
    donde r = Pearson, Sx/Sy = desv. típ., μx/μy = medias.
    Retorna CCC (float) o NaN si no se puede calcular.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 3:
        return np.nan
    mx, my = x.mean(), y.mean()
    sx, sy = x.std(ddof=0), y.std(ddof=0)
    if sx == 0 or sy == 0:
        return np.nan
    r = np.corrcoef(x, y)[0, 1]
    ccc = (2 * r * sx * sy) / (sx**2 + sy**2 + (mx - my)**2)
    return float(ccc)


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cargar_sr_norm(csv_path=None):
    """Carga SR semanal normalizado (ancho: semana x metodología)."""
    if csv_path is None:
        root = _project_root()
        csv_path = os.path.join(root, "analysis", "stats", "sr_semanal_norm.csv")
    if not os.path.isfile(csv_path):
        raise FileNotFoundError("No se encontró %s. Ejecute antes: python -m analysis.stats.agregacion_semanal" % csv_path)
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    df.index.name = "semana"
    return df


def matriz_correlacion_y_pares(df):
    """Matrices de Pearson, Spearman, CCC de Lin y tabla de pares con bias y LoA."""
    instrumentos = [c for c in df.columns if df[c].notna().any()]
    if len(instrumentos) < 2:
        return None, None, None, None, None

    mat_r = pd.DataFrame(np.nan, index=instrumentos, columns=instrumentos)
    mat_rho = pd.DataFrame(np.nan, index=instrumentos, columns=instrumentos)
    mat_ccc = pd.DataFrame(np.nan, index=instrumentos, columns=instrumentos)
    mat_n = pd.DataFrame(0, index=instrumentos, columns=instrumentos)

    for inst in instrumentos:
        mat_r.loc[inst, inst] = 1.0
        mat_rho.loc[inst, inst] = 1.0
        mat_ccc.loc[inst, inst] = 1.0
        mat_n.loc[inst, inst] = int(df[inst].notna().sum())

    pares_rows = []
    for a, b in itertools.combinations(instrumentos, 2):
        sub = df[[a, b]].dropna()
        n = len(sub)
        if n < 3:
            continue
        r_pearson, p_pearson = stats.pearsonr(sub[a], sub[b])
        rho_spearman, p_spearman = stats.spearmanr(sub[a], sub[b])
        ccc_val = ccc_lin(sub[a].values, sub[b].values)
        mat_r.loc[a, b] = mat_r.loc[b, a] = round(float(r_pearson), 4)
        mat_rho.loc[a, b] = mat_rho.loc[b, a] = round(float(rho_spearman), 4)
        mat_ccc.loc[a, b] = mat_ccc.loc[b, a] = round(float(ccc_val), 4) if np.isfinite(ccc_val) else np.nan
        mat_n.loc[a, b] = mat_n.loc[b, a] = n

        diff = sub[a] - sub[b]
        bias = float(diff.mean())
        sd_diff = float(diff.std()) if n > 1 else 0.0
        loa_lo = bias - 1.96 * sd_diff
        loa_hi = bias + 1.96 * sd_diff
        rmse = float(np.sqrt((diff ** 2).mean()))

        pares_rows.append({
            "metodologia_A": a,
            "metodologia_B": b,
            "n_semanas": n,
            "r_pearson": round(r_pearson, 4),
            "p_pearson": round(p_pearson, 6),
            "rho_spearman": round(rho_spearman, 4),
            "CCC_Lin": round(ccc_val, 4) if np.isfinite(ccc_val) else np.nan,
            "bias_pp": round(bias, 4),
            "sd_diferencia_pp": round(sd_diff, 4),
            "LoA_inferior_pp": round(loa_lo, 4),
            "LoA_superior_pp": round(loa_hi, 4),
            "rmse_pp": round(rmse, 4),
        })

    pares = pd.DataFrame(pares_rows)
    return mat_r, mat_rho, mat_ccc, mat_n, pares


def grafico_heatmap_concordancia(mat_r, mat_n, out_path):
    """Heatmap de correlación de Pearson con n por celda."""
    n = len(mat_r)
    fig, ax = plt.subplots(figsize=(max(8, n * 1.0), max(6, n * 0.9)))
    cmap = plt.cm.RdYlGn
    im = ax.imshow(mat_r.values.astype(float), cmap=cmap, vmin=0.5, vmax=1.0, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(mat_r.columns, rotation=40, ha="right", fontsize=9)
    ax.set_yticklabels(mat_r.index, fontsize=9)

    for i in range(n):
        for j in range(n):
            r_val = mat_r.values[i, j]
            n_val = mat_n.values[i, j]
            if np.isnan(r_val):
                txt = "—"
                color = "gray"
            elif i == j:
                txt = "1"
                color = "black"
            else:
                txt = f"{r_val:.2f}\n(n={int(n_val)})"
                color = "white" if (np.isfinite(r_val) and r_val >= 0.92) else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7, color=color)

    plt.colorbar(im, ax=ax, label="r (Pearson)")
    ax.set_title("Concordancia intermetodológica — Correlación de Pearson\nSR semanal Q25 normalizado (PVStand/IV600 corregidos por T)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Heatmap concordancia: %s", out_path)


def grafico_heatmap_ccc(mat_ccc, mat_n, out_path):
    """Heatmap del CCC de Lin con n por celda."""
    n = len(mat_ccc)
    fig, ax = plt.subplots(figsize=(max(8, n * 1.0), max(6, n * 0.9)))
    cmap = plt.cm.RdYlGn
    im = ax.imshow(mat_ccc.values.astype(float), cmap=cmap, vmin=0.0, vmax=1.0, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(mat_ccc.columns, rotation=40, ha="right", fontsize=9)
    ax.set_yticklabels(mat_ccc.index, fontsize=9)

    norm_color = plt.Normalize(vmin=0.0, vmax=1.0)
    for i in range(n):
        for j in range(n):
            ccc_val = mat_ccc.values[i, j]
            n_val = mat_n.values[i, j]
            if np.isnan(ccc_val):
                txt, color = "—", "gray"
            elif i == j:
                txt, color = "1", "black"
            else:
                txt = f"{ccc_val:.2f}\n(n={int(n_val)})"
                rgba = cmap(norm_color(np.clip(float(ccc_val), 0, 1)))
                lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
                color = "black" if lum > 0.55 else "white"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7, color=color)

    plt.colorbar(im, ax=ax, label="CCC de Lin")
    ax.set_title("Concordancia intermetodológica — CCC de Lin\nSR semanal Q25 normalizado (PVStand/IV600 corregidos por T)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Heatmap CCC: %s", out_path)


def grafico_scatter_matrix(df, out_path, max_metodos=8):
    """Matriz de dispersión entre metodologías (subconjunto si hay muchas)."""
    instrumentos = [c for c in df.columns if df[c].notna().any()][:max_metodos]
    n = len(instrumentos)
    if n < 2:
        return

    fig, axes = plt.subplots(n, n, figsize=(2.2 * n, 2.2 * n))
    if n == 2:
        axes = np.array(axes).reshape(2, 2)

    for i, inst_y in enumerate(instrumentos):
        for j, inst_x in enumerate(instrumentos):
            ax = axes[i, j]
            sub = df[[inst_x, inst_y]].dropna()
            if len(sub) < 2:
                ax.set_visible(False)
                continue
            ax.scatter(sub[inst_x], sub[inst_y], alpha=0.6, s=25, c="#1f77b4", edgecolors="none")
            if i == 0:
                ax.set_title(inst_x, fontsize=8)
            if j == 0:
                ax.set_ylabel(inst_y, fontsize=8)
            ax.tick_params(labelsize=6)
            ax.set_aspect("equal", adjustable="box")
            r, _ = stats.pearsonr(sub[inst_x].values, sub[inst_y].values)
            arr = np.atleast_1d(np.asarray(r))
            r_scalar = float(arr[0]) if len(arr) > 0 else np.nan
            ax.text(0.05, 0.95, "r=%.2f" % r_scalar if np.isfinite(r_scalar) else "r=—", transform=ax.transAxes, fontsize=7, va="top")

    fig.suptitle("Concordancia intermetodológica — Dispersión por pares (SR normalizado)", fontsize=11)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Scatter matrix: %s", out_path)


def run(out_dir=None, norm_csv=None):
    """Genera matrices y gráficos de concordancia. out_dir por defecto: analysis/concordancia."""
    root = _project_root()
    if out_dir is None:
        out_dir = os.path.join(root, "analysis", "concordancia")
    os.makedirs(out_dir, exist_ok=True)

    df = cargar_sr_norm(norm_csv)
    instrumentos = [c for c in df.columns if df[c].notna().any()]
    logger.info("Metodologías: %s", instrumentos)

    mat_r, mat_rho, mat_ccc, mat_n, pares = matriz_correlacion_y_pares(df)
    if mat_r is None:
        logger.error("No hay suficientes datos para concordancia.")
        return False

    # CSV
    mat_r.to_csv(os.path.join(out_dir, "matriz_correlacion.csv"))
    mat_rho.to_csv(os.path.join(out_dir, "matriz_correlacion_spearman.csv"))
    mat_ccc.to_csv(os.path.join(out_dir, "matriz_ccc_lin.csv"))
    if pares is not None and not pares.empty:
        pares.to_csv(os.path.join(out_dir, "concordancia_pares.csv"), index=False)
    logger.info("CSV guardados en %s", out_dir)

    if MATPLOTLIB_AVAILABLE:
        grafico_heatmap_concordancia(mat_r, mat_n, os.path.join(out_dir, "heatmap_concordancia.png"))
        grafico_heatmap_ccc(mat_ccc, mat_n, os.path.join(out_dir, "heatmap_ccc_lin.png"))
        grafico_scatter_matrix(df, os.path.join(out_dir, "scatter_concordancia.png"))

    # README
    readme = os.path.join(out_dir, "README.md")
    with open(readme, "w", encoding="utf-8") as f:
        f.write("# Concordancia intermetodológica\n\n")
        f.write("Matrices y gráficos de concordancia entre todas las metodologías de SR. ")
        f.write("Datos: SR semanal Q25 normalizado (t₀=100%); PVStand e IV600 usan series **corregidas por temperatura**.\n\n")
        f.write("## Archivos\n\n")
        f.write("- **matriz_correlacion.csv**: Correlación de Pearson entre pares de metodologías.\n")
        f.write("- **matriz_correlacion_spearman.csv**: Correlación de Spearman.\n")
        f.write("- **concordancia_pares.csv**: Por par: n_semanas, r_pearson, p_pearson, rho_spearman, CCC_Lin, bias_pp, sd_diferencia_pp, LoA (±1.96 SD), rmse_pp.\n")
        f.write("- **matriz_ccc_lin.csv**: Matriz del CCC de Lin (concordancia que combina precisión y exactitud).\n")
        f.write("- **heatmap_concordancia.png**: Heatmap de correlaciones Pearson (con n por celda).\n")
        f.write("- **heatmap_ccc_lin.png**: Heatmap del CCC de Lin (con n por celda).\n")
        f.write("- **scatter_concordancia.png**: Matriz de dispersión entre metodologías.\n\n")
        f.write("## Cómo generar\n\n")
        f.write("Desde la raíz del proyecto (TESIS_SOILING):\n\n")
        f.write("```bash\npython -m analysis.concordancia.concordancia_intermetodologica\n```\n\n")
        f.write("Requiere tener generado antes `analysis/stats/sr_semanal_norm.csv` (ej. `python -m analysis.stats.agregacion_semanal`).\n")
    logger.info("README: %s", readme)

    return True


def main():
    root = _project_root()
    if os.path.basename(root) != "TESIS_SOILING" and os.path.isdir(os.path.join(root, "TESIS_SOILING")):
        root = os.path.join(root, "TESIS_SOILING")
    out_dir = os.path.join(root, "analysis", "concordancia")
    norm_csv = os.path.join(root, "analysis", "stats", "sr_semanal_norm.csv")
    if len(sys.argv) > 1:
        norm_csv = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    ok = run(out_dir=out_dir, norm_csv=norm_csv)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
