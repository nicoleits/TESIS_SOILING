"""
Análisis de correlación cruzada entre instrumentos de soiling.

Usa el SR semanal Q25 (sr_semanal_norm.csv; IV600 Pmax/Isc sin normalizar, resto t₀=100%) para calcular la
correlación de Pearson entre todos los pares de instrumentos. Solo se usan
las semanas donde ambos instrumentos tienen dato simultáneamente (pairwise
complete observations).

Métricas por par:
  - Correlación de Pearson (r)
  - p-valor asociado
  - n (semanas en común)
  - Bias: media(A − B) en pp normalizados
  - RMSE: raíz del error cuadrático medio entre ambas series

Salidas en analysis/correlacion/:
  correlacion_matrix.csv          : matriz r de Pearson (n×n)
  correlacion_pvalues.csv         : matriz de p-valores (n×n)
  correlacion_pares.csv           : tabla larga con r, p, n, bias, RMSE por par
  correlacion_heatmap_r.png       : heatmap de correlaciones
  correlacion_heatmap_p.png       : heatmap de p-valores
  correlacion_scatter_matrix.png  : matriz de dispersión entre pares
  correlacion_report.md           : reporte interpretado

Uso (desde TESIS_SOILING):
  python -m analysis.correlacion.correlacion_cruzada
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

from analysis.plot_metodos import (
    color_metodo,
    configure_matplotlib_for_thesis,
    etiqueta_metodo_mathtext,
    ticklabels_mathtext,
    titulo_reemplazar_iv600_pmax_isc,
)

try:
    import locale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib import patheffects
    from matplotlib.ticker import FuncFormatter
    try:
        locale.setlocale(locale.LC_NUMERIC, "es_ES.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_NUMERIC, "es_ES")
        except locale.Error:
            pass
    configure_matplotlib_for_thesis()

    def _formatter_coma(x, pos=None):
        return f"{x:.2f}".replace(".", ",")

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    LinearSegmentedColormap = None
    patheffects = None
    FuncFormatter = None
    _formatter_coma = None

ALPHA = 0.05


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

def cargar_norm(norm_csv):
    df = pd.read_csv(norm_csv, index_col=0, parse_dates=True)
    df.index.name = "semana"
    return df


# ---------------------------------------------------------------------------
# Métricas por par
# ---------------------------------------------------------------------------

def calcular_pares(df):
    instrumentos = df.columns.tolist()
    rows = []
    for a, b in itertools.combinations(instrumentos, 2):
        sub = df[[a, b]].dropna()
        n = len(sub)
        if n < 4:
            continue
        r, p = stats.pearsonr(sub[a], sub[b])
        diff = sub[a] - sub[b]
        bias = diff.mean()
        rmse = np.sqrt((diff ** 2).mean())
        rows.append({
            "instrumento_A": a,
            "instrumento_B": b,
            "n_semanas": n,
            "r_pearson": round(r, 4),
            "p_valor": round(p, 6),
            "significativo": p < ALPHA,
            "bias_pp": round(bias, 4),
            "rmse_pp": round(rmse, 4),
        })
    return pd.DataFrame(rows).sort_values("r_pearson", ascending=False)


def matriz_correlacion(df):
    instrumentos = df.columns.tolist()
    mat_r = pd.DataFrame(np.nan, index=instrumentos, columns=instrumentos)
    mat_p = pd.DataFrame(np.nan, index=instrumentos, columns=instrumentos)
    mat_n = pd.DataFrame(0,    index=instrumentos, columns=instrumentos)

    for inst in instrumentos:
        mat_r.loc[inst, inst] = 1.0
        mat_p.loc[inst, inst] = 0.0
        mat_n.loc[inst, inst] = df[inst].notna().sum()

    for a, b in itertools.combinations(instrumentos, 2):
        sub = df[[a, b]].dropna()
        n = len(sub)
        if n < 4:
            continue
        r, p = stats.pearsonr(sub[a], sub[b])
        mat_r.loc[a, b] = mat_r.loc[b, a] = round(r, 4)
        mat_p.loc[a, b] = mat_p.loc[b, a] = round(p, 6)
        mat_n.loc[a, b] = mat_n.loc[b, a] = n

    return mat_r, mat_p, mat_n


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def heatmap_correlacion(mat_r, mat_n, out_path):
    n = len(mat_r)
    fig, ax = plt.subplots(figsize=(max(7, n * 1.1), max(6, n)))

    cmap = plt.cm.RdYlGn
    im = ax.imshow(mat_r.values.astype(float), cmap=cmap, vmin=-1, vmax=1, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(ticklabels_mathtext(mat_r.columns), rotation=35, ha="right", fontsize=12)
    ax.set_yticklabels(ticklabels_mathtext(mat_r.index), fontsize=12)

    for i in range(n):
        for j in range(n):
            r_val = mat_r.values[i, j]
            n_val = mat_n.values[i, j]
            if np.isnan(r_val):
                txt = "—"
                color = "gray"
            elif i == j:
                txt = "1,000"
                color = "black"
            else:
                txt = f"{r_val:.3f}\n(n={int(n_val)})".replace(".", ",")
                color = "black" if abs(r_val) < 0.85 else "white"
            ax.text(j, i, txt, ha="center", va="center", fontsize=11, color=color)

    cbar = plt.colorbar(im, ax=ax, label="r de Pearson")
    if _formatter_coma is not None:
        cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.2f}".replace(".", ",")))
    ax.set_title(
        titulo_reemplazar_iv600_pmax_isc(
            "Correlación de Pearson entre instrumentos\n(SR semanal Q25; IV600 Pmax/Isc valor absoluto)"
        ),
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Heatmap correlación: %s", out_path)


def _cmap_pvalores_claro():
    """Colormap para p-valores: verde/rojo distinguibles pero no oscuros; texto con borde blanco."""
    base = plt.cm.RdYlGn_r
    # Tramo 35%-82%: evita extremos muy oscuros
    colores = base(np.linspace(0.35, 0.82, 256))
    # Mezcla 55% color + 45% blanco
    blanco = np.array([1.0, 1.0, 1.0, 1.0])
    colores = colores * 0.55 + blanco * 0.45
    colores = np.clip(colores, 0, 1)
    return LinearSegmentedColormap.from_list("pvalores_claro", colores, N=256)


def heatmap_pvalores(mat_p, out_path):
    """
    Heatmap de p-valores en escala lineal (0 a 0,1). Verde claro = p bajo, rojo claro = p alto.
    """
    n = len(mat_p)
    fig, ax = plt.subplots(figsize=(max(7, n * 1.1), max(6, n)))

    # Escala lineal: p en [0, 0.1]; diagonal no se pinta
    mat_plot = mat_p.values.astype(float).copy()
    for i in range(n):
        for j in range(n):
            if i == j:
                mat_plot[i, j] = np.nan
            elif np.isfinite(mat_plot[i, j]) and mat_plot[i, j] <= 0:
                mat_plot[i, j] = 0.0  # p≈0 → verde
    # Mismo colormap que heatmap de r (RdYlGn): verde = p bajo, rojo = p alto
    plot_val = np.clip(mat_plot, 0.0, 0.1)
    cmap = plt.cm.RdYlGn_r
    im = ax.imshow(plot_val, cmap=cmap, vmin=0, vmax=0.1, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(ticklabels_mathtext(mat_p.columns), rotation=35, ha="right", fontsize=12)
    ax.set_yticklabels(ticklabels_mathtext(mat_p.index), fontsize=12)

    # Misma lógica que heatmap_r: negro en tonos medios, blanco en extremos (verde/rojo oscuros)
    norm = plt.Normalize(vmin=0, vmax=0.1)
    for i in range(n):
        for j in range(n):
            val = mat_p.values[i, j]
            if np.isnan(val):
                txt, color = "—", "gray"
            elif i == j:
                txt, color = "—", "gray"
            elif np.isfinite(val) and val <= 0:
                txt, color = "p≈0", "white"
            elif val < 0.001:
                txt, color = "p<0,001", "white"
            else:
                txt = ("p=" + f"{val:.3f}".replace(".", ","))
                rgba = cmap(norm(np.clip(float(val), 0, 0.1)))
                lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
                color = "black" if lum > 0.55 else "white"
            ax.text(j, i, txt, ha="center", va="center", fontsize=11, color=color)

    cbar = plt.colorbar(im, ax=ax, label="p-valor")
    if _formatter_coma is not None:
        cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.3f}".replace(".", ",")))
    ax.set_title("P-valores de correlación de Pearson entre instrumentos",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Heatmap p-valores: %s", out_path)


def scatter_matrix(df, out_path):
    instrumentos = df.columns.tolist()
    n = len(instrumentos)

    fig, axes = plt.subplots(n, n, figsize=(2.5 * n, 2.5 * n))

    for i, inst_y in enumerate(instrumentos):
        for j, inst_x in enumerate(instrumentos):
            ax = axes[i, j]
            if i == j:
                # Diagonal: histograma
                vals = df[inst_x].dropna()
                ax.hist(vals, bins=12, color=color_metodo(inst_x), alpha=0.7, edgecolor="none")
                ax.set_title(etiqueta_metodo_mathtext(inst_x), fontsize=10, fontweight="bold")
            else:
                sub = df[[inst_x, inst_y]].dropna()
                if len(sub) >= 4:
                    ax.scatter(sub[inst_x], sub[inst_y],
                               s=8, alpha=0.6, color=color_metodo(inst_x))
                    # línea de regresión
                    m, b = np.polyfit(sub[inst_x], sub[inst_y], 1)
                    xr = np.linspace(sub[inst_x].min(), sub[inst_x].max(), 50)
                    ax.plot(xr, m * xr + b, "k-", linewidth=0.8, alpha=0.7)
                    r, p = stats.pearsonr(sub[inst_x], sub[inst_y])
                    r_txt = "r=" + f"{r:.2f}".replace(".", ",")
                    ax.text(0.05, 0.92, r_txt, transform=ax.transAxes,
                            fontsize=9, va="top",
                            color="green" if abs(r) >= 0.7 else "red")
            if _formatter_coma is not None:
                ax.xaxis.set_major_formatter(FuncFormatter(_formatter_coma))
                ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
            ax.tick_params(labelsize=9)
            if j == 0:
                ax.set_ylabel(etiqueta_metodo_mathtext(inst_y), fontsize=10)
            if i == n - 1:
                ax.set_xlabel(etiqueta_metodo_mathtext(inst_x), fontsize=10)

    fig.suptitle(
        titulo_reemplazar_iv600_pmax_isc(
            "Matriz de dispersión — SR semanal Q25 (IV600 Pmax/Isc valor absoluto)"
        ),
        fontsize=14, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()
    logger.info("Scatter matrix: %s", out_path)


# ---------------------------------------------------------------------------
# Reporte Markdown
# ---------------------------------------------------------------------------

def interpretar_r(r):
    ar = abs(r)
    if ar >= 0.90:
        return "muy alta"
    elif ar >= 0.75:
        return "alta"
    elif ar >= 0.50:
        return "moderada"
    elif ar >= 0.25:
        return "baja"
    else:
        return "muy baja / nula"


def generar_reporte(df_pares, mat_r, out_path, modo_txt):
    lines = [
        "# Análisis de Correlación Cruzada entre Instrumentos",
        "",
        f"**Variable:** SR semanal Q25 ({modo_txt})  ",
        f"**Método:** Correlación de Pearson pairwise (solo semanas con dato en ambos instrumentos)  ",
        f"**Nivel de significancia:** α = {ALPHA}",
        "",
        "---",
        "## Tabla de correlaciones por par (ordenado por r)",
        "",
        "| Par | n semanas | r Pearson | Interpretación | p-valor | Sig. | Bias (pp) | RMSE (pp) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, row in df_pares.iterrows():
        sig = "✓" if row["significativo"] else "✗"
        interp = interpretar_r(row["r_pearson"])
        lines.append(
            f"| {row['instrumento_A']} vs {row['instrumento_B']} "
            f"| {int(row['n_semanas'])} "
            f"| {row['r_pearson']:.4f} "
            f"| {interp} "
            f"| {row['p_valor']:.4f} "
            f"| {sig} "
            f"| {row['bias_pp']:.3f} "
            f"| {row['rmse_pp']:.3f} |"
        )

    # Grupos de alta correlación
    alta = df_pares[(df_pares["r_pearson"] >= 0.75) & df_pares["significativo"]]
    baja = df_pares[df_pares["r_pearson"] < 0.50]

    lines += [
        "",
        "---",
        "## Pares con correlación alta (r ≥ 0.75, significativa)",
        "",
    ]
    if alta.empty:
        lines.append("_Ningún par alcanzó r ≥ 0.75._")
    else:
        for _, row in alta.iterrows():
            lines.append(f"- **{row['instrumento_A']} vs {row['instrumento_B']}**: "
                         f"r = {row['r_pearson']:.4f}, n = {int(row['n_semanas'])}, "
                         f"RMSE = {row['rmse_pp']:.3f} pp")

    lines += [
        "",
        "## Pares con correlación baja (r < 0.50)",
        "",
    ]
    if baja.empty:
        lines.append("_Todos los pares tienen r ≥ 0.50._")
    else:
        for _, row in baja.iterrows():
            lines.append(f"- **{row['instrumento_A']} vs {row['instrumento_B']}**: "
                         f"r = {row['r_pearson']:.4f}, n = {int(row['n_semanas'])}")

    lines += [
        "",
        "---",
        "## Interpretación",
        "",
        "Una correlación alta entre dos instrumentos indica que rastrean la **misma",
        "tendencia temporal del soiling**, aunque puedan tener niveles absolutos distintos",
        "(sesgo). Una correlación baja indica que los instrumentos responden a fenómenos",
        "diferentes o que uno de ellos introduce ruido sistemático.",
        "",
        f"> **Nota:** La correlación se calcula sobre el SR semanal Q25 ({modo_txt}).",
        "> Los instrumentos con períodos de medición cortos (IV600: 30 semanas) tienen",
        "> menos semanas en común con el resto, lo que puede afectar la estimación de r.",
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Reporte: %s", out_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(norm_csv, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    df = cargar_norm(norm_csv)
    base_name = os.path.basename(norm_csv).lower()
    sin_normalizar = ("sr_semanal_q25" in base_name) and ("norm" not in base_name)
    modo_txt = "SIN normalizar" if sin_normalizar else "t₀=100% excepto IV600 Pmax/Isc en valor absoluto"
    logger.info("Instrumentos: %s", df.columns.tolist())
    logger.info("Semanas totales: %d", len(df))

    mat_r, mat_p, mat_n = matriz_correlacion(df)
    df_pares = calcular_pares(df)

    # CSVs
    mat_r.to_csv(os.path.join(out_dir, "correlacion_matrix.csv"))
    mat_p.to_csv(os.path.join(out_dir, "correlacion_pvalues.csv"))
    df_pares.to_csv(os.path.join(out_dir, "correlacion_pares.csv"), index=False)
    logger.info("CSVs guardados en %s", out_dir)

    # Log resumen
    for _, row in df_pares.iterrows():
        logger.info("  %-20s vs %-20s  r=%+.4f  p=%.4f  n=%d",
                    row["instrumento_A"], row["instrumento_B"],
                    row["r_pearson"], row["p_valor"], int(row["n_semanas"]))

    # Gráficos
    if MATPLOTLIB_AVAILABLE:
        heatmap_correlacion(mat_r, mat_n,
                            os.path.join(out_dir, "correlacion_heatmap_r.png"))
        heatmap_pvalores(mat_p,
                         os.path.join(out_dir, "correlacion_heatmap_p.png"))
        scatter_matrix(df, os.path.join(out_dir, "correlacion_scatter_matrix.png"))

    generar_reporte(df_pares, mat_r, os.path.join(out_dir, "correlacion_report.md"), modo_txt)
    return True


def main():
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    norm_csv = os.path.join(project_root, "analysis", "stats", "sr_semanal_norm.csv")
    out_dir  = os.path.join(project_root, "analysis", "correlacion")
    if len(sys.argv) > 1:
        norm_csv = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    logger.info("Input: %s | Salida: %s", norm_csv, out_dir)
    ok = run(norm_csv, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
