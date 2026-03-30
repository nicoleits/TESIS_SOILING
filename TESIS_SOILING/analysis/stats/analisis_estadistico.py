"""
Análisis estadístico de los datos filtrados/alineados.

- Módulos con frecuencia 1 min (fotoceldas, dustiq, temperatura, refcells): dentro de la ventana
  de 5 min hay hasta 5 valores por día; se calcula dispersión (desv. estándar, rango, CV) por día
  y por variable, y luego se resume entre días (media de std, percentiles, etc.).
- Módulos 5 min o irregulares (pvstand, iv600, soilingkit): solo un valor por día en la ventana;
  se hace análisis entre días (media, std, percentiles por variable).

Uso (desde TESIS_SOILING):
  python -m analysis.stats.analisis_estadistico
  python -m analysis.stats.analisis_estadistico [data_dir]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Reutilizar sesiones y filtro de estabilidad del módulo de alineación
from analysis.align.align_to_soiling_kit import (
    cargar_sesiones_soiling_kit,
    dias_estables_irradiancia,
    MODULOS_ALINEAR,
    SOILINGKIT_SOLAR_NOON,
    SOLYS2_REF,
    COLUMNA_G_ESTABILIDAD,
    _get_time_col,
    _ensure_utc,
)


def _numeric_columns(df, exclude_time=True):
    time_keys = ["time", "fecha", "timestamp", "date"]
    cols = []
    for c in df.columns:
        if exclude_time and any(t in c.lower() for t in time_keys):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols


def _df_to_markdown(df):
    """Convierte DataFrame a tabla Markdown sin depender de tabulate."""
    if df is None or df.empty:
        return ""
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |", "| " + " | ".join("---" for _ in df.columns) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in df.columns) + " |")
    return "\n".join(lines)


def stats_dentro_ventana(csv_path, sesiones, time_col, tz_local=None):
    """
    Para cada día y cada columna numérica, toma los valores en la ventana de 5 min
    y calcula: n, mean, std, min, max, range, CV (%).
    Devuelve DataFrame largo: fecha, variable, n, mean, std, min, max, range, cv_pct.
    """
    df = pd.read_csv(csv_path)
    tc = time_col or _get_time_col(df)
    if not tc:
        return None
    df[tc] = pd.to_datetime(df[tc])
    df[tc] = _ensure_utc(df[tc], tz_local=tz_local)
    cols_num = _numeric_columns(df)
    if not cols_num:
        return None
    filas = []
    for _, row in sesiones.iterrows():
        start, end = row["_bin_start"], row["_bin_end"]
        mask = (df[tc] >= start) & (df[tc] < end)
        sub = df.loc[mask, cols_num]
        if sub.empty:
            continue
        for col in cols_num:
            vals = sub[col].dropna()
            n = len(vals)
            if n == 0:
                continue
            mean_v = vals.mean()
            std_v = vals.std()
            if pd.isna(std_v) or n < 2:
                std_v = 0.0
            min_v, max_v = vals.min(), vals.max()
            rng = max_v - min_v if n else 0
            cv = (100.0 * std_v / mean_v) if mean_v and np.isfinite(mean_v) else np.nan
            filas.append({
                "fecha": row["_date"],
                "variable": col,
                "n": n,
                "mean": mean_v,
                "std": std_v,
                "min": min_v,
                "max": max_v,
                "range": rng,
                "cv_pct": cv,
            })
    if not filas:
        return None
    return pd.DataFrame(filas)


def resumir_dentro_ventana(df_ventana):
    """Resumen entre días: por variable, media(std), mediana(std), p95(std), media(CV), etc."""
    if df_ventana is None or df_ventana.empty:
        return None
    res = df_ventana.groupby("variable").agg(
        dias_con_datos=("std", "count"),
        mean_std=("std", "mean"),
        median_std=("std", "median"),
        p95_std=("std", lambda x: x.quantile(0.95)),
        mean_cv_pct=("cv_pct", "mean"),
        median_cv_pct=("cv_pct", "median"),
        mean_range=("range", "mean"),
        mean_n=("n", "mean"),
    ).round(6)
    return res.reset_index()


def stats_entre_dias(csv_path, time_col=None):
    """
    Un valor por día (o por día+módulo): estadísticos entre días por columna numérica.
    Devuelve DataFrame: variable, count, mean, std, min, p05, p25, p50, p75, p95, max.
    """
    df = pd.read_csv(csv_path)
    tc = time_col or _get_time_col(df)
    cols_num = _numeric_columns(df)
    if not cols_num:
        return None
    res_list = []
    for col in cols_num:
        vals = df[col].dropna()
        if len(vals) == 0:
            continue
        res_list.append({
            "variable": col,
            "count": len(vals),
            "mean": vals.mean(),
            "std": vals.std(),
            "min": vals.min(),
            "p05": vals.quantile(0.05),
            "p25": vals.quantile(0.25),
            "p50": vals.quantile(0.50),
            "p75": vals.quantile(0.75),
            "p95": vals.quantile(0.95),
            "max": vals.max(),
        })
    if not res_list:
        return None
    return pd.DataFrame(res_list)


def run_analisis(data_dir, usar_solo_dias_estables=True, salida_md="analisis_estadistico_report.md", salida_csv="analisis_estadistico_resumen.csv"):
    """
    Ejecuta el análisis estadístico y escribe reporte Markdown + CSV de resúmenes.
    """
    data_dir = os.path.abspath(data_dir)
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "analysis", "stats")
    os.makedirs(out_dir, exist_ok=True)

    soiling_path = os.path.join(data_dir, "soilingkit", SOILINGKIT_SOLAR_NOON)
    if not os.path.isfile(soiling_path):
        logger.error("No existe %s. Ejecuta antes la alineación.", soiling_path)
        return False

    sesiones = cargar_sesiones_soiling_kit(soiling_path)
    if usar_solo_dias_estables:
        solys2_path = os.path.join(data_dir, "solys2", SOLYS2_REF)
        fechas_estables = dias_estables_irradiancia(solys2_path, sesiones)
        sesiones = sesiones[sesiones["_date"].isin(fechas_estables)].copy()
    logger.info("Sesiones (días) para análisis: %d", len(sesiones))

    # Config: (section, filename_filtered, freq, time_col, tz_local)
    modulos_1min = [(m[0], m[1], m[3], m[4] if len(m) > 4 else None) for m in MODULOS_ALINEAR if m[2] == "1min"]
    modulos_5min_irreg = [(m[0], m[2]) for m in MODULOS_ALINEAR if m[2] in ("5min", "irregular")]

    resultados_ventana = {}
    resultados_entre_dias = {}

    # --- Módulos 1 min: estadísticos dentro de ventana + resumen entre días
    for section, filename, time_col, tz_local in modulos_1min:
        csv_path = os.path.join(data_dir, section, filename)
        if not os.path.isfile(csv_path):
            logger.info("Omite %s: no existe %s", section, csv_path)
            continue
        df_ventana = stats_dentro_ventana(csv_path, sesiones, time_col, tz_local)
        if df_ventana is not None:
            resultados_ventana[section] = {
                "por_dia": df_ventana,
                "resumen": resumir_dentro_ventana(df_ventana),
            }
        # Entre días del valor medio por día (usar aligned si existe)
        aligned_path = os.path.join(data_dir, section, f"{section}_aligned_solar_noon.csv")
        if os.path.isfile(aligned_path):
            ed = stats_entre_dias(aligned_path)
            if ed is not None:
                resultados_entre_dias[section] = ed

    # --- Módulos 5 min e irregulares: solo entre días (aligned)
    for section, freq in modulos_5min_irreg:
        aligned_path = os.path.join(data_dir, section, f"{section}_aligned_solar_noon.csv")
        if not os.path.isfile(aligned_path):
            logger.info("Omite %s: no existe %s", section, aligned_path)
            continue
        ed = stats_entre_dias(aligned_path)
        if ed is not None:
            resultados_entre_dias[section] = ed

    # --- Soiling Kit: entre días (aligned)
    sk_path = os.path.join(data_dir, "soilingkit", "soilingkit_aligned_solar_noon.csv")
    if os.path.isfile(sk_path):
        ed = stats_entre_dias(sk_path)
        if ed is not None:
            resultados_entre_dias["soilingkit"] = ed

    # --- Escribir reporte Markdown
    md_path = os.path.join(out_dir, salida_md)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Análisis estadístico de datos filtrados/alineados\n\n")
        f.write(f"Días analizados: **{len(sesiones)}** (sesiones Soiling Kit")
        if usar_solo_dias_estables:
            f.write(", solo días con estabilidad de irradiancia (G) < 10%")
        f.write(").\n\n")

        # Módulos 1 min: dispersión dentro de la ventana de 5 min
        f.write("## 1. Módulos con datos cada 1 minuto (ventana 5 min)\n\n")
        f.write("En cada día se toman los valores en la misma ventana de 5 min que el Soiling Kit; ")
        f.write("hay hasta 5 puntos por día. Se calcula **dentro de la ventana** por día: media, desviación estándar (std), ")
        f.write("mínimo, máximo, rango y coeficiente de variación (CV = 100·std/mean). ")
        f.write("Luego se resume **entre días** (media de std, mediana de std, p95 de std, media de CV, etc.).\n\n")
        for section in resultados_ventana:
            r = resultados_ventana[section]["resumen"]
            if r is None or r.empty:
                continue
            f.write(f"### {section}\n\n")
            f.write(_df_to_markdown(r))
            f.write("\n\n")
            # Breve interpretación
            if "mean_cv_pct" in r.columns:
                cv_medio = r["mean_cv_pct"].mean()
                f.write(f"- CV medio entre días (por variable): ~{cv_medio:.2f}%. ")
                f.write("Menor CV indica menor dispersión dentro de la ventana de 5 min.\n\n")

        # Módulos 5 min e irregulares
        f.write("## 2. Módulos con datos cada 5 min o irregulares\n\n")
        f.write("Solo hay **un valor por día** (o por día y submódulo) en la ventana; no se puede calcular dispersión dentro de la ventana. ")
        f.write("Se reportan estadísticos **entre días**: count, mean, std, min, percentiles (p05, p25, p50, p75, p95), max.\n\n")
        for section in ["pvstand", "iv600"]:
            if section not in resultados_entre_dias:
                continue
            ed = resultados_entre_dias[section]
            f.write(f"### {section}\n\n")
            f.write(_df_to_markdown(ed))
            f.write("\n\n")

        # Soiling Kit
        if "soilingkit" in resultados_entre_dias:
            f.write("### soilingkit (alineado)\n\n")
            f.write(_df_to_markdown(resultados_entre_dias["soilingkit"]))
            f.write("\n\n")

        # Fotoceldas / otros 1 min: entre días (valor medio por día)
        f.write("## 3. Valores medios por día (módulos 1 min)\n\n")
        f.write("Estadísticos **entre días** del valor medio diario (una fila por día ya promediada en la ventana):\n\n")
        for section in resultados_ventana:
            if section not in resultados_entre_dias:
                continue
            ed = resultados_entre_dias[section]
            f.write(f"### {section}\n\n")
            f.write(_df_to_markdown(ed))
            f.write("\n\n")

    logger.info("Reporte escrito: %s", md_path)

    # --- CSV resumen (tablas concatenadas con columna 'modulo')
    csv_path = os.path.join(out_dir, salida_csv)
    listas = []
    for section, res in resultados_ventana.items():
        r = res.get("resumen")
        if r is not None and not r.empty:
            r = r.copy()
            r.insert(0, "modulo", section)
            r.insert(1, "tipo", "dentro_ventana")
            listas.append(r)
    for section, ed in resultados_entre_dias.items():
        if ed is None or ed.empty:
            continue
        ed = ed.copy()
        ed.insert(0, "modulo", section)
        ed.insert(1, "tipo", "entre_dias")
        listas.append(ed)
    if listas:
        pd.concat(listas, ignore_index=True).to_csv(csv_path, index=False)
        logger.info("Resumen CSV: %s", csv_path)
    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data")
    if len(sys.argv) > 1:
        data_dir = os.path.abspath(sys.argv[1])
    logger.info("Directorio de datos: %s", data_dir)
    ok = run_analisis(data_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
