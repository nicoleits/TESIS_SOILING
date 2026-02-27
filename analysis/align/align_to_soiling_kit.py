"""
Alinea el resto de módulos con las sesiones del Soiling Kit (una ventana de 5 min por día)
y filtra por estabilidad de irradiancia: (G_max - G_min) / G_med < 10%.

Reglas de alineación:
- Frecuencia 1 min: se seleccionan los mismos 5 minutos diarios que el Soiling Kit (promedio).
- Frecuencia 5 min: se selecciona el dato más cercano al instante central del Soiling Kit.
- Horarios irregulares (ej. IV600): se selecciona el dato más cercano al Soiling Kit,
  que no esté a más de 1 hora de distancia.

Uso (desde TESIS_SOILING):
  python -m analysis.align.align_to_soiling_kit
  python -m analysis.align.align_to_soiling_kit [data_dir]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Umbral de estabilidad: (G_max - G_min) / G_med < este valor (10%)
UMBRAL_ESTABILIDAD_G = 0.10
# Máxima distancia en minutos para módulos irregulares (1 hora)
MAX_DISTANCIA_IRREGULAR_MIN = 60

# Configuración de módulos: (carpeta, archivo CSV, tipo_frecuencia, columna tiempo, tz_local opcional)
# tipo_frecuencia: '1min' | '5min' | 'irregular'
# tz_local: si el CSV guarda hora local (ej. IV600), indicar zona ej. 'America/Santiago'; None = ya UTC
MODULOS_ALINEAR = [
    ("pv_glasses", "pv_glasses_poa_500_clear_sky.csv", "1min", "_time", None),
    ("dustiq", "dustiq_poa_500_clear_sky.csv", "1min", "timestamp", None),
    ("temperatura", "temperatura_poa_500_clear_sky.csv", "1min", "TIMESTAMP", None),
    ("refcells", "refcells_poa_500_clear_sky.csv", "1min", "timestamp", None),
    ("pvstand", "pvstand_poa_500_clear_sky.csv", "5min", "timestamp", None),
    ("iv600", "iv600_poa_500_clear_sky.csv", "irregular", "timestamp", "America/Santiago"),
]
# Soiling Kit ya está en sesión mediodía solar; solo se filtra por estabilidad
SOILINGKIT_SOLAR_NOON = "soilingkit_solar_noon.csv"
# Solys2 para estabilidad (necesitamos 1 min con POA o GHI en la ventana de 5 min)
SOLYS2_REF = "solys2_poa_500_clear_sky.csv"
COLUMNA_G_ESTABILIDAD = "POA"  # o "GHI"


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def _ensure_utc(series, tz_local=None):
    """Convierte la columna de tiempo a UTC. Si tz_local (ej. 'America/Santiago') se indica, los valores se interpretan como hora local."""
    if tz_local:
        # Los valores están en hora local: quitar tz si viene con +00:00 y tratar como local
        if series.dt.tz is not None:
            series = series.dt.tz_localize(None)
        series = series.dt.tz_localize(tz_local, ambiguous="infer").dt.tz_convert("UTC")
        return series
    if series.dt.tz is None:
        return series.dt.tz_localize("UTC")
    return series.dt.tz_convert("UTC")


def cargar_sesiones_soiling_kit(csv_path):
    """Carga soilingkit_solar_noon.csv y devuelve DataFrame con timestamp (centro 5 min) por día."""
    df = pd.read_csv(csv_path)
    tc = _get_time_col(df)
    if not tc:
        raise ValueError(f"No se encontró columna de tiempo en {csv_path}")
    df[tc] = pd.to_datetime(df[tc])
    df[tc] = _ensure_utc(df[tc])
    df["_date"] = df[tc].dt.date
    df["_center"] = df[tc]
    # Ventana 5 min: inicio y fin
    df["_bin_start"] = df["_center"].dt.floor("5min")
    df["_bin_end"] = df["_bin_start"] + pd.Timedelta(minutes=5)
    return df[["_date", "_center", "_bin_start", "_bin_end"]].drop_duplicates("_date").sort_values("_date").reset_index(drop=True)


def dias_estables_irradiancia(solys2_csv_path, sesiones, col_g=COLUMNA_G_ESTABILIDAD):
    """
    Para cada día en sesiones, calcula (G_max - G_min)/G_med en la ventana de 5 min.
    Devuelve el set de fechas (date) que cumplen < UMBRAL_ESTABILIDAD_G.
    """
    if not os.path.isfile(solys2_csv_path):
        logger.warning("No existe %s; no se aplica filtro de estabilidad.", solys2_csv_path)
        return set(sesiones["_date"].tolist())
    df_g = pd.read_csv(solys2_csv_path)
    tc = _get_time_col(df_g)
    if not tc:
        logger.warning("No hay columna de tiempo en Solys2; no se aplica filtro de estabilidad.")
        return set(sesiones["_date"].tolist())
    if col_g not in df_g.columns:
        logger.warning("No hay columna %s en Solys2; no se aplica filtro de estabilidad.", col_g)
        return set(sesiones["_date"].tolist())
    df_g[tc] = pd.to_datetime(df_g[tc])
    df_g[tc] = _ensure_utc(df_g[tc])
    df_g = df_g.sort_values(tc)
    fechas_estables = []
    for _, row in sesiones.iterrows():
        d = row["_date"]
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
        if ratio < UMBRAL_ESTABILIDAD_G:
            fechas_estables.append(d)
    return set(fechas_estables)


def alinear_modulo_1min(csv_path, sesiones, time_col):
    """Selecciona los mismos 5 minutos que el Soiling Kit y promedia (una fila por día)."""
    df = pd.read_csv(csv_path)
    tc = time_col or _get_time_col(df)
    if not tc:
        return None
    df[tc] = pd.to_datetime(df[tc])
    df[tc] = _ensure_utc(df[tc])
    filas = []
    for _, row in sesiones.iterrows():
        start, end = row["_bin_start"], row["_bin_end"]
        mask = (df[tc] >= start) & (df[tc] < end)
        sub = df.loc[mask].copy()
        if sub.empty:
            continue
        sub = sub.drop(columns=[tc], errors="ignore")
        # Promedio de las columnas numéricas en la ventana
        agg = sub.mean(numeric_only=True).to_dict()
        agg["timestamp"] = row["_center"]
        agg["_date"] = row["_date"]
        filas.append(agg)
    if not filas:
        return None
    out = pd.DataFrame(filas)
    out = out.drop(columns=["_date"], errors="ignore")
    cols = ["timestamp"] + [c for c in out.columns if c != "timestamp"]
    return out[[c for c in cols if c in out.columns]]


def alinear_modulo_5min(csv_path, sesiones, time_col):
    """Selecciona el dato de 5 min más cercano al instante central del Soiling Kit (todas las filas de ese slot, ej. perc1 y perc2)."""
    df = pd.read_csv(csv_path)
    tc = time_col or _get_time_col(df)
    if not tc:
        return None
    df[tc] = pd.to_datetime(df[tc])
    df[tc] = _ensure_utc(df[tc])
    df["_bin_5"] = df[tc].dt.floor("5min")
    filas = []
    for _, row in sesiones.iterrows():
        center = row["_center"]
        bin_target = center.floor("5min")
        sub = df[df["_bin_5"] == bin_target].copy()
        if sub.empty:
            # Buscar el 5 min más cercano (puede haber varias filas, ej. dos módulos)
            dist = (df[tc] - center).abs()
            min_d = dist.min()
            if min_d > pd.Timedelta(minutes=7.5):
                continue
            sub = df.loc[dist == min_d].copy()
        sub = sub.drop(columns=["_bin_5"], errors="ignore")
        sub = sub.rename(columns={tc: "timestamp"})
        if "timestamp" not in sub.columns:
            sub["timestamp"] = center
        sub["_date"] = row["_date"]
        filas.append(sub)
    if not filas:
        return None
    out = pd.concat(filas, ignore_index=True)
    out = out.drop(columns=["_date"], errors="ignore")
    return out


def alinear_modulo_irregular(csv_path, sesiones, time_col, max_minutos=MAX_DISTANCIA_IRREGULAR_MIN, tz_local=None):
    """Selecciona el dato más cercano al Soiling Kit; si está a más de max_minutos, se descarta el día. Si tz_local (ej. America/Santiago), los timestamps del CSV se interpretan como hora local."""
    df = pd.read_csv(csv_path)
    tc = time_col or _get_time_col(df)
    if not tc:
        return None
    df[tc] = pd.to_datetime(df[tc])
    df[tc] = _ensure_utc(df[tc], tz_local=tz_local)
    max_delta = pd.Timedelta(minutes=max_minutos)
    filas = []
    for _, row in sesiones.iterrows():
        center = row["_center"]
        df["_dist"] = (df[tc] - center).abs()
        idx = df["_dist"].idxmin()
        if df.loc[idx, "_dist"] > max_delta:
            continue
        sub = df.loc[[idx]].copy().drop(columns=["_dist"], errors="ignore")
        sub = sub.rename(columns={tc: "timestamp"})
        if "timestamp" not in sub.columns:
            sub["timestamp"] = center
        sub["_date"] = row["_date"]
        filas.append(sub)
    if not filas:
        return None
    out = pd.concat(filas, ignore_index=True)
    out = out.drop(columns=["_date"], errors="ignore")
    return out


def run_align(data_dir, output_suffix="_aligned_solar_noon.csv", aplicar_estabilidad=True):
    """
    Ejecuta la alineación de todos los módulos y el filtro de estabilidad.
    data_dir: directorio base (TESIS_SOILING/data).
    """
    data_dir = os.path.abspath(data_dir)
    soiling_path = os.path.join(data_dir, "soilingkit", SOILINGKIT_SOLAR_NOON)
    if not os.path.isfile(soiling_path):
        logger.error("No existe %s. Ejecuta antes la opción 13 o 14 de download_data.py.", soiling_path)
        return False
    sesiones = cargar_sesiones_soiling_kit(soiling_path)
    logger.info("Sesiones Soiling Kit: %d días.", len(sesiones))

    # Fechas estables según irradiancia (Solys2)
    solys2_path = os.path.join(data_dir, "solys2", SOLYS2_REF)
    fechas_estables = dias_estables_irradiancia(solys2_path, sesiones)
    logger.info("Días con estabilidad (G) < %.0f%%: %d de %d.", UMBRAL_ESTABILIDAD_G * 100, len(fechas_estables), len(sesiones))
    if aplicar_estabilidad and fechas_estables:
        sesiones = sesiones[sesiones["_date"].isin(fechas_estables)].copy()
        logger.info("Sesiones tras filtro estabilidad: %d días.", len(sesiones))

    # Soiling Kit: solo filtrar por fechas estables (ya está en formato 1 fila/día)
    sk_df = pd.read_csv(soiling_path)
    tc_sk = _get_time_col(pd.read_csv(soiling_path))
    sk_df[tc_sk] = pd.to_datetime(sk_df[tc_sk])
    sk_df["_date"] = sk_df[tc_sk].dt.date
    if aplicar_estabilidad and fechas_estables:
        sk_df = sk_df[sk_df["_date"].isin(fechas_estables)].copy()
    sk_df = sk_df.drop(columns=["_date"], errors="ignore")
    sk_out = os.path.join(data_dir, "soilingkit", "soilingkit_aligned_solar_noon.csv")
    os.makedirs(os.path.dirname(sk_out), exist_ok=True)
    sk_df.to_csv(sk_out, index=False)
    logger.info("Soiling Kit (alineado/estable): %s", sk_out)

    # Resto de módulos
    for config in MODULOS_ALINEAR:
        section, filename, freq, time_col = config[0], config[1], config[2], config[3]
        tz_local = config[4] if len(config) > 4 else None
        csv_path = os.path.join(data_dir, section, filename)
        if not os.path.isfile(csv_path):
            logger.info("Omite %s: no existe %s", section, csv_path)
            continue
        if freq == "1min":
            out_df = alinear_modulo_1min(csv_path, sesiones, time_col)
        elif freq == "5min":
            out_df = alinear_modulo_5min(csv_path, sesiones, time_col)
        else:
            out_df = alinear_modulo_irregular(csv_path, sesiones, time_col, tz_local=tz_local)
        if out_df is None or out_df.empty:
            logger.warning("Sin datos alineados para %s.", section)
            continue
        if "_date" in out_df.columns:
            out_df = out_df.drop(columns=["_date"], errors="ignore")
        out_path = os.path.join(data_dir, section, section.replace("-", "_") + output_suffix)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        out_df.to_csv(out_path, index=False)
        logger.info("%s: %d filas -> %s", section, len(out_df), out_path)
    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data")
    if len(sys.argv) > 1:
        data_dir = os.path.abspath(sys.argv[1])
    logger.info("Directorio de datos: %s", data_dir)
    ok = run_align(data_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
