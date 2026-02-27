"""
ANOVA de un factor sobre el SR semanal Q25 normalizado.

Pregunta: ¿Existe diferencia estadísticamente significativa en el SR normalizado
medio entre los distintos instrumentos de medición de soiling?

Flujo:
  1. Carga sr_semanal_norm_largo.csv  (semana, instrumento, sr_norm)
  2. Dos conjuntos de datos:
       - pool      : todas las semanas disponibles por instrumento (ANOVA no balanceado)
       - intersección: solo semanas donde TODOS los instrumentos tienen dato
  3. Para cada conjunto:
       a. Shapiro-Wilk por grupo (normalidad)
       b. Levene (homocedasticidad)
       c. ANOVA paramétrico (scipy f_oneway)  → post-hoc Tukey HSD (statsmodels)
       d. Kruskal-Wallis no paramétrico       → post-hoc Dunn (scikit-posthocs, Bonferroni)
  4. Gráficos: violin, heatmap p-valores Tukey, heatmap p-valores Dunn
  5. Reporte Markdown con interpretación automática

Salidas en analysis/anova/:
  anova_results.csv
  anova_posthoc_tukey_pool.csv / _interseccion.csv
  anova_posthoc_dunn_pool.csv  / _interseccion.csv
  anova_violin.png
  anova_heatmap_tukey_pool.png / _interseccion.png
  anova_heatmap_dunn_pool.png  / _interseccion.png
  anova_report.md

Uso (desde TESIS_SOILING):
  python -m analysis.anova.anova_sr
"""
import os
import sys
import logging
import textwrap
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import scikit_posthocs as sp

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

ALPHA = 0.05


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def cargar_datos(norm_largo_csv):
    df = pd.read_csv(norm_largo_csv, parse_dates=["semana"])
    df = df.dropna(subset=["sr_norm"])
    return df


def hacer_interseccion(df):
    """Devuelve solo las semanas donde TODOS los instrumentos tienen dato."""
    instrumentos = df["instrumento"].unique()
    conteo = df.groupby("semana")["instrumento"].nunique()
    semanas_completas = conteo[conteo == len(instrumentos)].index
    return df[df["semana"].isin(semanas_completas)].copy()


# ---------------------------------------------------------------------------
# Supuestos
# ---------------------------------------------------------------------------

def test_normalidad(df):
    rows = []
    for inst, grupo in df.groupby("instrumento"):
        vals = grupo["sr_norm"].dropna().values
        if len(vals) < 3:
            rows.append({"instrumento": inst, "n": len(vals),
                         "shapiro_W": np.nan, "shapiro_p": np.nan, "normal_alpha05": np.nan})
            continue
        W, p = stats.shapiro(vals)
        rows.append({"instrumento": inst, "n": len(vals),
                     "shapiro_W": round(W, 4), "shapiro_p": round(p, 4),
                     "normal_alpha05": p >= ALPHA})
    return pd.DataFrame(rows)


def test_levene(df):
    grupos = [g["sr_norm"].dropna().values
              for _, g in df.groupby("instrumento")]
    stat, p = stats.levene(*grupos)
    return {"levene_stat": round(stat, 4), "levene_p": round(p, 4),
            "homocedastico_alpha05": p >= ALPHA}


# ---------------------------------------------------------------------------
# ANOVA + post-hoc Tukey
# ---------------------------------------------------------------------------

def anova_parametrico(df):
    grupos = [g["sr_norm"].dropna().values for _, g in df.groupby("instrumento")]
    F, p = stats.f_oneway(*grupos)
    return {"F": round(F, 4), "p_anova": round(p, 6),
            "significativo_alpha05": p < ALPHA}


def posthoc_tukey(df):
    result = pairwise_tukeyhsd(endog=df["sr_norm"], groups=df["instrumento"], alpha=ALPHA)
    df_res = pd.DataFrame(data=result._results_table.data[1:],
                          columns=result._results_table.data[0])
    df_res.columns = ["grupo1", "grupo2", "meandiff", "p_adj", "lower", "upper", "reject"]
    return df_res


# ---------------------------------------------------------------------------
# Kruskal-Wallis + post-hoc Dunn
# ---------------------------------------------------------------------------

def kruskal(df):
    grupos = [g["sr_norm"].dropna().values for _, g in df.groupby("instrumento")]
    H, p = stats.kruskal(*grupos)
    return {"H": round(H, 4), "p_kruskal": round(p, 6),
            "significativo_alpha05": p < ALPHA}


def posthoc_dunn(df):
    result = sp.posthoc_dunn(df, val_col="sr_norm", group_col="instrumento", p_adjust="bonferroni")
    return result


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def grafico_violin(df_pool, df_inter, out_path):
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    titles = ["Pool completo (todas las semanas)", "Intersección (semanas comunes)"]
    for ax, data, title in zip(axes, [df_pool, df_inter], titles):
        instrumentos = sorted(data["instrumento"].unique())
        grupos = [data[data["instrumento"] == i]["sr_norm"].dropna().values for i in instrumentos]
        parts = ax.violinplot(grupos, positions=range(len(instrumentos)),
                              showmedians=True, showextrema=True)
        colors = plt.cm.tab10.colors
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(colors[i % len(colors)])
            pc.set_alpha(0.7)
        ax.set_xticks(range(len(instrumentos)))
        ax.set_xticklabels(instrumentos, rotation=20, ha="right", fontsize=8)
        ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_ylabel("SR normalizado (%)")
        ax.set_title(title, fontsize=10)
        ax.grid(True, axis="y", alpha=0.3)
    fig.suptitle("Distribución del SR semanal Q25 normalizado por instrumento",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico violin: %s", out_path)


def _heatmap_pvalores(matrix_df, title, out_path, instrumentos=None):
    """Heatmap de p-valores ajustados. matrix_df es un DataFrame cuadrado."""
    if instrumentos is not None:
        matrix_df = matrix_df.loc[instrumentos, instrumentos]
    n = len(matrix_df)
    fig, ax = plt.subplots(figsize=(max(7, n * 1.1), max(6, n * 1.0)))

    # Colormap: verde (p alto = no sig.) → rojo (p bajo = significativo)
    cmap = plt.cm.RdYlGn
    im = ax.imshow(matrix_df.values.astype(float), cmap=cmap, vmin=0, vmax=0.2, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(matrix_df.columns, rotation=35, ha="right", fontsize=9)
    ax.set_yticklabels(matrix_df.index, fontsize=9)

    for i in range(n):
        for j in range(n):
            val = matrix_df.values[i, j]
            if np.isnan(val):
                txt = "—"
                color = "gray"
            else:
                txt = f"{val:.3f}"
                color = "black" if val > 0.05 else "white"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7, color=color)

    plt.colorbar(im, ax=ax, label="p-valor ajustado")
    ax.set_title(title, fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Heatmap: %s", out_path)


def heatmap_tukey(df_tukey, instrumentos, title, out_path):
    """Convierte el resultado Tukey (lista de pares) en matriz cuadrada."""
    mat = pd.DataFrame(np.nan, index=instrumentos, columns=instrumentos)
    np.fill_diagonal(mat.values, 1.0)
    for _, row in df_tukey.iterrows():
        g1, g2, p = row["grupo1"], row["grupo2"], float(row["p_adj"])
        mat.loc[g1, g2] = p
        mat.loc[g2, g1] = p
    _heatmap_pvalores(mat, title, out_path, instrumentos)


def heatmap_dunn(df_dunn, title, out_path):
    _heatmap_pvalores(df_dunn, title, out_path)


# ---------------------------------------------------------------------------
# Reporte Markdown
# ---------------------------------------------------------------------------

def interpretar(p, test):
    if p < 0.001:
        return f"**p < 0.001** → diferencia altamente significativa ({test})"
    elif p < 0.01:
        return f"**p = {p:.4f}** → diferencia muy significativa ({test})"
    elif p < 0.05:
        return f"**p = {p:.4f}** → diferencia significativa ({test})"
    else:
        return f"**p = {p:.4f}** → sin diferencia significativa (p ≥ 0.05) ({test})"


def generar_reporte(conjuntos, out_path):
    lines = [
        "# Análisis ANOVA — SR Semanal Q25 Normalizado",
        "",
        "**Variable dependiente:** SR semanal Q25 normalizado a t₀ = 100%  ",
        f"**Nivel de significancia:** α = {ALPHA}  ",
        "**Factor:** instrumento (Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600, IV600 corr)",
        "",
    ]

    for etiqueta, res in conjuntos.items():
        lines += [
            f"---",
            f"## Conjunto: {etiqueta}",
            f"",
            f"**N total de observaciones:** {res['n_total']}  ",
            f"**Semanas por instrumento:**",
            "",
        ]
        for _, row in res["normalidad"].iterrows():
            lines.append(f"- {row['instrumento']}: n={int(row['n'])}")

        lines += [
            "",
            "### 1. Supuestos",
            "",
            "#### Normalidad (Shapiro-Wilk por grupo)",
            "",
        ]
        lines.append("| Instrumento | n | W | p | ¿Normal α=0.05? |")
        lines.append("|---|---|---|---|---|")
        for _, row in res["normalidad"].iterrows():
            ok = "✓" if row["normal_alpha05"] else "✗"
            lines.append(f"| {row['instrumento']} | {int(row['n'])} | {row['shapiro_W']:.4f} | {row['shapiro_p']:.4f} | {ok} |")

        lev = res["levene"]
        ok_lev = "✓ homocedástico" if lev["homocedastico_alpha05"] else "✗ heterocedástico"
        lines += [
            "",
            "#### Homocedasticidad (Levene)",
            "",
            f"- Estadístico: {lev['levene_stat']}  ",
            f"- p-valor: {lev['levene_p']}  ",
            f"- Resultado: {ok_lev}",
            "",
        ]

        an = res["anova"]
        kw = res["kruskal"]
        lines += [
            "### 2. ANOVA paramétrico (f_oneway)",
            "",
            f"- F = {an['F']},  {interpretar(an['p_anova'], 'ANOVA')}",
            "",
            "### 3. Kruskal-Wallis (no paramétrico)",
            "",
            f"- H = {kw['H']},  {interpretar(kw['p_kruskal'], 'Kruskal-Wallis')}",
            "",
        ]

        lines += [
            "### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)",
            "",
        ]
        sig_tukey = res["tukey"][res["tukey"]["reject"] == True]
        if sig_tukey.empty:
            lines.append("_Ningún par muestra diferencia significativa._")
        else:
            lines.append("| Par | Diferencia de medias | p_adj |")
            lines.append("|---|---|---|")
            for _, row in sig_tukey.iterrows():
                lines.append(f"| {row['grupo1']} vs {row['grupo2']} | {float(row['meandiff']):.3f} pp | {float(row['p_adj']):.4f} |")

        lines += [
            "",
            "### 5. Post-hoc Dunn + Bonferroni (pares significativos, p_adj < 0.05)",
            "",
        ]
        dunn = res["dunn"]
        sig_dunn = []
        for g1 in dunn.index:
            for g2 in dunn.columns:
                if g1 < g2 and dunn.loc[g1, g2] < ALPHA:
                    sig_dunn.append((g1, g2, dunn.loc[g1, g2]))
        if not sig_dunn:
            lines.append("_Ningún par muestra diferencia significativa._")
        else:
            lines.append("| Par | p_adj (Bonferroni) |")
            lines.append("|---|---|")
            for g1, g2, p in sig_dunn:
                lines.append(f"| {g1} vs {g2} | {p:.4f} |")
        lines.append("")

    lines += [
        "---",
        "## Conclusión general",
        "",
        "El análisis ANOVA sobre los datos normalizados evalúa si los instrumentos",
        "evolucionan de forma estadísticamente equivalente una vez eliminado el sesgo",
        "de nivel absoluto. Un resultado significativo indica que la **tasa de cambio**",
        "del SR difiere entre instrumentos, lo que implica que no son intercambiables",
        "para el seguimiento del soiling.",
        "",
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Reporte: %s", out_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(norm_largo_csv, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    df_all = cargar_datos(norm_largo_csv)
    df_inter = hacer_interseccion(df_all)

    logger.info("Pool: %d obs, %d instrumentos", len(df_all), df_all["instrumento"].nunique())
    logger.info("Intersección: %d obs, %d semanas comunes",
                len(df_inter), df_inter["semana"].nunique())

    conjuntos_data = {"Pool completo": df_all, "Intersección": df_inter}
    resultados = {}
    all_instrumentos = sorted(df_all["instrumento"].unique())

    for etiqueta, df in conjuntos_data.items():
        slug = etiqueta.lower().replace(" ", "_")
        logger.info("--- %s ---", etiqueta)

        norm = test_normalidad(df)
        lev  = test_levene(df)
        an   = anova_parametrico(df)
        kw   = kruskal(df)
        tuk  = posthoc_tukey(df)
        dun  = posthoc_dunn(df)

        logger.info("ANOVA  F=%.3f  p=%.6f  sig=%s", an["F"], an["p_anova"], an["significativo_alpha05"])
        logger.info("Kruskal H=%.3f  p=%.6f  sig=%s", kw["H"], kw["p_kruskal"], kw["significativo_alpha05"])

        tuk.to_csv(os.path.join(out_dir, f"anova_posthoc_tukey_{slug}.csv"), index=False)
        dun.to_csv(os.path.join(out_dir, f"anova_posthoc_dunn_{slug}.csv"))

        if MATPLOTLIB_AVAILABLE:
            instrumentos_set = sorted(df["instrumento"].unique())
            heatmap_tukey(tuk, instrumentos_set,
                          f"Tukey HSD p-valores — {etiqueta}",
                          os.path.join(out_dir, f"anova_heatmap_tukey_{slug}.png"))
            heatmap_dunn(dun,
                         f"Dunn + Bonferroni p-valores — {etiqueta}",
                         os.path.join(out_dir, f"anova_heatmap_dunn_{slug}.png"))

        resultados[etiqueta] = {
            "n_total": len(df),
            "normalidad": norm,
            "levene": lev,
            "anova": an,
            "kruskal": kw,
            "tukey": tuk,
            "dunn": dun,
        }

    # Resumen numérico global
    rows_res = []
    for etiqueta, res in resultados.items():
        rows_res.append({
            "conjunto": etiqueta,
            "n_total": res["n_total"],
            "levene_p": res["levene"]["levene_p"],
            "homocedastico": res["levene"]["homocedastico_alpha05"],
            "anova_F": res["anova"]["F"],
            "anova_p": res["anova"]["p_anova"],
            "anova_sig": res["anova"]["significativo_alpha05"],
            "kruskal_H": res["kruskal"]["H"],
            "kruskal_p": res["kruskal"]["p_kruskal"],
            "kruskal_sig": res["kruskal"]["significativo_alpha05"],
        })
    pd.DataFrame(rows_res).to_csv(os.path.join(out_dir, "anova_results.csv"), index=False)
    logger.info("Resultados: %s", os.path.join(out_dir, "anova_results.csv"))

    if MATPLOTLIB_AVAILABLE:
        grafico_violin(df_all, df_inter,
                       os.path.join(out_dir, "anova_violin.png"))

    generar_reporte(resultados, os.path.join(out_dir, "anova_report.md"))
    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    norm_csv = os.path.join(project_root, "analysis", "stats", "sr_semanal_norm_largo.csv")
    out_dir  = os.path.join(project_root, "analysis", "anova")
    if len(sys.argv) > 1:
        norm_csv = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    logger.info("Input: %s | Salida: %s", norm_csv, out_dir)
    ok = run(norm_csv, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
