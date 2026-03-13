"""
Análisis del efecto del QA/QC sobre el conjunto de datos.

Genera:
1. Tabla tipo embudo: días iniciales → tras umbral irradiancia/cielo despejado
   → tras ventana mediodía solar → tras estabilidad intraventana → días finales comparables.
2. Figura: distribución de dist_solar_noon_min (criterio "cercano a mediodía solar").
3. Figura: distribución del indicador de estabilidad (G_max-G_min)/G_med y umbral.

Uso (desde TESIS_SOILING):
  python -m analysis.qaqc.analisis_efecto_qaqc
  python -m analysis.qaqc.analisis_efecto_qaqc [data_dir]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    from analysis.config import PERIODO_ANALISIS_INICIO, PERIODO_ANALISIS_FIN
except ImportError:
    PERIODO_ANALISIS_INICIO = "2024-08-03"
    PERIODO_ANALISIS_FIN = "2025-08-04"

# Umbrales (deben coincidir con download_data y align_to_soiling_kit)
UMBRAL_ESTABILIDAD_G = 0.10  # (G_max - G_min) / G_med < 10%
MAX_DIST_SOLAR_NOON_MIN = 50  # minutos
COLUMNA_G_ESTABILIDAD = "POA"


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def _ensure_utc(series, tz_local=None):
    if series.dt.tz is None:
        return series.dt.tz_localize("UTC")
    return series.dt.tz_convert("UTC")


def _dias_unicos(csv_path, time_col=None, fecha_min=None, fecha_max=None):
    """Devuelve número de días únicos en un CSV con columna de tiempo. Opcional: filtrar por fecha_min/fecha_max (str YYYY-MM-DD)."""
    if not os.path.isfile(csv_path):
        return None
    df = pd.read_csv(csv_path, nrows=100000)
    tc = time_col or _get_time_col(df)
    if not tc:
        return None
    df = pd.read_csv(csv_path)
    df[tc] = pd.to_datetime(df[tc])
    df["_date"] = df[tc].dt.date
    if fecha_min is not None:
        df = df[df["_date"] >= pd.to_datetime(fecha_min).date()]
    if fecha_max is not None:
        df = df[df["_date"] <= pd.to_datetime(fecha_max).date()]
    return df["_date"].nunique()


def _cargar_sesiones_solar_noon(csv_path, fecha_min=None, fecha_max=None):
    """Carga soilingkit_solar_noon.csv con ventana 5 min por día. Opcional: filtrar por fecha_min/fecha_max (str YYYY-MM-DD)."""
    df = pd.read_csv(csv_path)
    tc = _get_time_col(df)
    if not tc:
        raise ValueError(f"No se encontró columna de tiempo en {csv_path}")
    df[tc] = pd.to_datetime(df[tc])
    df[tc] = _ensure_utc(df[tc])
    df["_date"] = df[tc].dt.date
    if fecha_min is not None:
        df = df[df["_date"] >= pd.to_datetime(fecha_min).date()]
    if fecha_max is not None:
        df = df[df["_date"] <= pd.to_datetime(fecha_max).date()]
    df["_center"] = df[tc]
    df["_bin_start"] = df["_center"].dt.floor("5min")
    df["_bin_end"] = df["_bin_start"] + pd.Timedelta(minutes=5)
    return df


def _estabilidad_por_dia(solys2_csv_path, sesiones, col_g=COLUMNA_G_ESTABILIDAD):
    """
    Para cada día en sesiones, calcula (G_max - G_min)/G_med en la ventana de 5 min.
    Devuelve DataFrame con _date y indicador_estabilidad (ratio).
    """
    if not os.path.isfile(solys2_csv_path):
        return pd.DataFrame(columns=["_date", "indicador_estabilidad"])
    df_g = pd.read_csv(solys2_csv_path)
    tc = _get_time_col(df_g)
    if not tc or col_g not in df_g.columns:
        return pd.DataFrame(columns=["_date", "indicador_estabilidad"])
    df_g[tc] = pd.to_datetime(df_g[tc])
    df_g[tc] = _ensure_utc(df_g[tc])
    df_g = df_g.sort_values(tc)
    filas = []
    for _, row in sesiones.iterrows():
        start, end = row["_bin_start"], row["_bin_end"]
        mask = (df_g[tc] >= start) & (df_g[tc] < end)
        sub = df_g.loc[mask, col_g].dropna()
        if len(sub) < 2:
            continue
        g_med = sub.mean()
        if g_med <= 0:
            continue
        g_max, g_min = sub.max(), sub.min()
        ratio = (g_max - g_min) / g_med
        filas.append({"_date": row["_date"], "indicador_estabilidad": ratio})
    return pd.DataFrame(filas)


def run_analisis_qaqc(data_dir, output_dir=None):
    """
    Ejecuta el análisis de efecto QA/QC: tabla embudo y figuras.
    data_dir: directorio base de datos (ej. TESIS_SOILING/data).
    output_dir: donde guardar CSV y PNG; por defecto analysis/qaqc.
    """
    data_dir = os.path.abspath(data_dir)
    # Carpeta que contiene data/ (ej. TESIS_SOILING)
    project_root = os.path.dirname(data_dir)
    if output_dir is None:
        output_dir = os.path.join(project_root, "analysis", "qaqc")
    os.makedirs(output_dir, exist_ok=True)

    soiling_raw = os.path.join(data_dir, "soilingkit", "soilingkit_raw_data.csv")
    soiling_poa = os.path.join(data_dir, "soilingkit", "soilingkit_poa_500_clear_sky.csv")
    soiling_solar = os.path.join(data_dir, "soilingkit", "soilingkit_solar_noon.csv")
    soiling_aligned = os.path.join(data_dir, "soilingkit", "soilingkit_aligned_solar_noon.csv")
    solys2_ref = os.path.join(data_dir, "solys2", "solys2_poa_500_clear_sky.csv")

    # Periodo de análisis (mismo que el resto del proyecto)
    fecha_min = PERIODO_ANALISIS_INICIO
    fecha_max = PERIODO_ANALISIS_FIN
    logger.info("Periodo de análisis: %s — %s", fecha_min, fecha_max)

    # --- Embudo de días (solo dentro del periodo) ---
    n_iniciales = _dias_unicos(soiling_raw, fecha_min=fecha_min, fecha_max=fecha_max)
    if n_iniciales is None:
        n_iniciales = _dias_unicos(soiling_poa, fecha_min=fecha_min, fecha_max=fecha_max)
        etapa_inicial = "días con datos Soiling Kit (tras POA/clear-sky)*"
    else:
        etapa_inicial = "días con datos Soiling Kit (raw)"

    n_tras_irradiancia = _dias_unicos(soiling_poa, fecha_min=fecha_min, fecha_max=fecha_max)
    if n_tras_irradiancia is None:
        logger.warning("No se encuentra soilingkit_poa_500_clear_sky; no se puede calcular embudo.")
        return False

    df_solar = pd.read_csv(soiling_solar)
    tc = _get_time_col(df_solar)
    df_solar[tc] = pd.to_datetime(df_solar[tc])
    df_solar["_date"] = df_solar[tc].dt.date
    df_solar = df_solar[(df_solar["_date"] >= pd.to_datetime(fecha_min).date()) & (df_solar["_date"] <= pd.to_datetime(fecha_max).date())]
    n_tras_mediodia = df_solar["_date"].nunique() if "_date" in df_solar.columns else len(df_solar)

    df_aligned = pd.read_csv(soiling_aligned)
    tc_a = _get_time_col(df_aligned)
    if tc_a:
        df_aligned[tc_a] = pd.to_datetime(df_aligned[tc_a])
        df_aligned["_date"] = df_aligned[tc_a].dt.date
        df_aligned = df_aligned[(df_aligned["_date"] >= pd.to_datetime(fecha_min).date()) & (df_aligned["_date"] <= pd.to_datetime(fecha_max).date())]
    n_tras_estabilidad = df_aligned["_date"].nunique() if "_date" in df_aligned.columns else len(df_aligned)
    n_finales = n_tras_estabilidad

    # Si no teníamos raw, primera fila del embudo = días tras irradiancia
    if n_iniciales is None:
        n_iniciales = n_tras_irradiancia

    embudo = pd.DataFrame([
        {"etapa": "Días iniciales (con datos Soiling Kit)", "descripcion": etapa_inicial, "dias": n_iniciales},
        {"etapa": "Tras umbral irradiancia y cielo despejado", "descripcion": "POA ≥ 500 W/m², clear_sky_ratio ≥ 0,8", "dias": n_tras_irradiancia},
        {"etapa": "Tras ventana mediodía solar", "descripcion": f"Ventana 5 min más cercana al mediodía solar (≤ {MAX_DIST_SOLAR_NOON_MIN} min)", "dias": n_tras_mediodia},
        {"etapa": "Tras estabilidad intraventana", "descripcion": f"(G_max − G_min)/G_med < {UMBRAL_ESTABILIDAD_G*100:.0f}% en la ventana de 5 min", "dias": n_tras_estabilidad},
        {"etapa": "Días finales comparables", "descripcion": "Conjunto usado para comparaciones entre módulos", "dias": n_finales},
    ])
    # Días perdidos = etapa anterior − etapa actual
    anterior = embudo["dias"].shift(1)
    embudo["dias_perdidos"] = (anterior - embudo["dias"]).fillna(0).astype(int)

    path_embudo_csv = os.path.join(output_dir, "qaqc_embudo_dias.csv")
    embudo.to_csv(path_embudo_csv, index=False)
    logger.info("Tabla embudo guardada: %s", path_embudo_csv)

    # Markdown
    path_embudo_md = os.path.join(output_dir, "qaqc_embudo_dias.md")
    with open(path_embudo_md, "w", encoding="utf-8") as f:
        f.write("# Efecto del QA/QC: embudo de días\n\n")
        f.write(f"**Periodo de análisis:** {fecha_min} — {fecha_max} (mismo que en `analysis/config.py`).\n\n")
        f.write("| Etapa | Descripción | Días | Días perdidos respecto a la etapa anterior |\n")
        f.write("|-------|-------------|------|------------------------------------------|\n")
        for idx, r in embudo.iterrows():
            perd = r["dias_perdidos"]
            perd_str = "—" if (idx == 0 or idx == len(embudo) - 1) else str(int(perd))
            f.write(f"| {r['etapa']} | {r['descripcion']} | {r['dias']} | {perd_str} |\n")
        f.write("\nLos **días finales comparables** son los que se usan para alinear todos los módulos y calcular SR.\n")
    logger.info("Resumen embudo (Markdown): %s", path_embudo_md)

    # --- Figura: distribución dist_solar_noon_min ---
    if "dist_solar_noon_min" in df_solar.columns:
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
            fig, ax = plt.subplots(figsize=(7, 4))
            d = df_solar["dist_solar_noon_min"].dropna()
            ax.hist(d, bins=min(30, max(10, len(d) // 5)), color="steelblue", edgecolor="white", alpha=0.85, density=True, label="Días")
            ax.axvline(MAX_DIST_SOLAR_NOON_MIN, color="crimson", linestyle="--", linewidth=2, label=f"Umbral ({MAX_DIST_SOLAR_NOON_MIN} min)")
            ax.set_xlabel("Distancia ventana–mediodía solar (min)")
            ax.set_ylabel("Densidad")
            ax.set_title("Distribución de distancia al mediodía solar\n(criterio «cercano a mediodía solar» aplicado de forma consistente)")
            ax.legend()
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            path_dist = os.path.join(output_dir, "qaqc_dist_solar_noon_min.png")
            fig.savefig(path_dist, dpi=150, bbox_inches="tight")
            plt.close(fig)
            logger.info("Figura guardada: %s", path_dist)
        except Exception as e:
            logger.warning("No se pudo generar figura dist_solar_noon_min: %s", e)

    # --- Indicador de estabilidad por día (sesiones dentro del periodo) ---
    sesiones = _cargar_sesiones_solar_noon(soiling_solar, fecha_min=fecha_min, fecha_max=fecha_max)
    df_estab = _estabilidad_por_dia(solys2_ref, sesiones)
    if df_estab.empty:
        logger.warning("No se pudo calcular indicador de estabilidad por día.")
    else:
        n_estables = (df_estab["indicador_estabilidad"] < UMBRAL_ESTABILIDAD_G).sum()
        # Figura: distribución del indicador de estabilidad
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
            fig, ax = plt.subplots(figsize=(7, 4))
            x = df_estab["indicador_estabilidad"].dropna()
            ax.hist(x, bins=min(40, max(15, len(x) // 3)), color="teal", edgecolor="white", alpha=0.85, density=True, label="Días")
            ax.axvline(UMBRAL_ESTABILIDAD_G, color="crimson", linestyle="--", linewidth=2, label=f"Umbral ({UMBRAL_ESTABILIDAD_G*100:.0f}%)")
            ax.set_xlabel("Indicador de estabilidad: (G_max − G_min) / G_med")
            ax.set_ylabel("Densidad")
            ax.set_title("Distribución del indicador de estabilidad en la ventana de 5 min\n(solo días con sesión de mediodía solar)")
            ax.legend()
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            path_estab = os.path.join(output_dir, "qaqc_estabilidad_umbral.png")
            fig.savefig(path_estab, dpi=150, bbox_inches="tight")
            plt.close(fig)
            logger.info("Figura guardada: %s", path_estab)
        except Exception as e:
            logger.warning("No se pudo generar figura estabilidad: %s", e)

        # Guardar indicador por día para transparencia
        df_estab.to_csv(os.path.join(output_dir, "qaqc_indicador_estabilidad_por_dia.csv"), index=False)

    # --- Visualizaciones adicionales: embudo visual y figura resumen ---
    try:
        import locale
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        try:
            locale.setlocale(locale.LC_NUMERIC, "es_ES.UTF-8")
        except locale.Error:
            try:
                locale.setlocale(locale.LC_NUMERIC, "es_ES")
            except locale.Error:
                pass
        plt.rcParams["axes.formatter.use_locale"] = True

        # Etiquetas cortas para el gráfico
        etiquetas = [
            "Días iniciales\n(Soiling Kit raw)",
            "Tras irradiancia\ny cielo despejado",
            "Tras ventana\nmediodía solar",
            "Tras estabilidad\nintraventana",
            "Días finales\ncomparables",
        ]
        dias = embudo["dias"].tolist()
        perdidos = embudo["dias_perdidos"].tolist()

        # 1) Gráfico tipo embudo (barras horizontales que se estrechan)
        fig_funnel, ax_f = plt.subplots(figsize=(9, 5))
        y_pos = np.arange(len(etiquetas))[::-1]  # arriba = inicial
        colors = ["#2e7d32"] * 4 + ["#1565c0"]  # verde para proceso, azul para resultado final
        bars = ax_f.barh(y_pos, dias, height=0.6, color=colors, edgecolor="white", linewidth=1.2)
        ax_f.set_yticks(y_pos)
        ax_f.set_yticklabels(etiquetas, fontsize=10)
        ax_f.set_xlabel("Número de días", fontsize=11)
        ax_f.set_title("Proceso de limpieza de datos (QA/QC): embudo de días", fontsize=12, fontweight="bold")
        ax_f.set_xlim(0, max(dias) * 1.18)
        for i, (d, p) in enumerate(zip(dias, perdidos)):
            ax_f.text(d + 5, len(etiquetas) - 1 - i, f"{d}", va="center", fontsize=11, fontweight="bold")
            if p > 0 and i > 0:
                ax_f.annotate(f"−{p}", xy=(dias[i] + 2, len(etiquetas) - 1 - i), fontsize=10, color="#c62828", fontweight="bold")
        ax_f.grid(axis="x", alpha=0.3)
        fig_funnel.tight_layout()
        path_funnel = os.path.join(output_dir, "qaqc_embudo_visual.png")
        fig_funnel.savefig(path_funnel, dpi=150, bbox_inches="tight")
        plt.close(fig_funnel)
        logger.info("Figura guardada: %s", path_funnel)

        # 2) Waterfall: barras por etapa + anotaciones de pérdida
        fig_w, ax_w = plt.subplots(figsize=(10, 5))
        x_w = np.arange(5)
        ax_w.bar(x_w, dias, width=0.5, color="#1976d2", edgecolor="white", linewidth=1)
        ax_w.set_xticks(x_w)
        ax_w.set_xticklabels(["Inicial", "Irradiancia\ny cielo claro", "Ventana\nmediodía solar", "Estabilidad\nintraventana", "Final\ncomparables"])
        ax_w.set_ylabel("Días")
        ax_w.set_title("Waterfall: efecto de cada filtro en el número de días", fontsize=12, fontweight="bold")
        for i, d in enumerate(dias):
            ax_w.text(i, d + 4, str(d), ha="center", fontsize=10, fontweight="bold")
        for i in range(1, 4):
            if perdidos[i] > 0:
                ax_w.annotate(f"−{perdidos[i]}", xy=(i - 0.5, (dias[i - 1] + dias[i]) / 2),
                              fontsize=10, color="#c62828", fontweight="bold", ha="center")
        ax_w.set_ylim(0, max(dias) + 22)
        ax_w.grid(axis="y", alpha=0.3)
        fig_w.tight_layout()
        path_waterfall = os.path.join(output_dir, "qaqc_waterfall_filtros.png")
        fig_w.savefig(path_waterfall, dpi=150, bbox_inches="tight")
        plt.close(fig_w)
        logger.info("Figura guardada: %s", path_waterfall)

        # 3) Figura resumen: 1 fila x 3 columnas (embudo + dist_solar_noon + estabilidad)
        fig_resumen, axes = plt.subplots(1, 3, figsize=(14, 5))
        fig_resumen.suptitle("Proceso y resultado de la limpieza de datos (QA/QC)", fontsize=13, fontweight="bold", y=1.02)

        # Panel A: miniemudo (barras horizontales compactas)
        ax_a = axes[0]
        ax_a.barh(range(5)[::-1], dias, height=0.55, color=colors, edgecolor="white", linewidth=0.8)
        ax_a.set_yticks(range(5)[::-1])
        ax_a.set_yticklabels(["Inicial", "Tras irradiancia", "Tras mediodía", "Tras estabilidad", "Finales"], fontsize=9)
        ax_a.set_xlabel("Días")
        ax_a.set_title("A. Embudo de días")
        for i, d in enumerate(dias):
            ax_a.text(d + 3, 4 - i, str(d), va="center", fontsize=9)
        ax_a.set_xlim(0, max(dias) * 1.15)
        ax_a.grid(axis="x", alpha=0.3)

        # Panel B: dist_solar_noon_min
        ax_b = axes[1]
        if "dist_solar_noon_min" in df_solar.columns:
            d = df_solar["dist_solar_noon_min"].dropna()
            ax_b.hist(d, bins=min(25, max(8, len(d) // 5)), color="steelblue", edgecolor="white", alpha=0.85, density=True)
            ax_b.axvline(MAX_DIST_SOLAR_NOON_MIN, color="crimson", linestyle="--", linewidth=1.5, label=f"Umbral ({MAX_DIST_SOLAR_NOON_MIN} min)")
            ax_b.set_xlabel("Distancia al mediodía solar (min)")
            ax_b.set_ylabel("Densidad")
            ax_b.set_title("B. Cercanía al mediodía solar")
            ax_b.legend(fontsize=8)
        ax_b.grid(True, alpha=0.3)

        # Panel C: estabilidad
        ax_c = axes[2]
        if not df_estab.empty:
            x = df_estab["indicador_estabilidad"].dropna()
            ax_c.hist(x, bins=min(30, max(12, len(x) // 3)), color="teal", edgecolor="white", alpha=0.85, density=True)
            ax_c.axvline(UMBRAL_ESTABILIDAD_G, color="crimson", linestyle="--", linewidth=1.5, label=f"Umbral ({UMBRAL_ESTABILIDAD_G*100:.0f}%)")
            ax_c.set_xlabel("(G_max − G_min) / G_med")
            ax_c.set_ylabel("Densidad")
            ax_c.set_title("C. Estabilidad en ventana 5 min")
            ax_c.legend(fontsize=8)
        ax_c.grid(True, alpha=0.3)

        fig_resumen.tight_layout()
        path_resumen = os.path.join(output_dir, "qaqc_resumen_visual.png")
        fig_resumen.savefig(path_resumen, dpi=150, bbox_inches="tight")
        plt.close(fig_resumen)
        logger.info("Figura guardada: %s", path_resumen)
    except Exception as e:
        logger.warning("No se pudieron generar figuras visuales adicionales: %s", e)
    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data")
    if len(sys.argv) > 1:
        data_dir = os.path.abspath(sys.argv[1])
    logger.info("Directorio de datos: %s", data_dir)
    ok = run_analisis_qaqc(data_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
