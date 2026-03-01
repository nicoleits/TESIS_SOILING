"""
Análisis integrado PV Glasses + Calendario de muestras.

Lógica de ventana de medición:
  Para cada fila 'Fija a RC, soiled' del calendario (llegada del vidrio):
    - La fila correspondiente 'RC a Fija, soiled' indica cuándo el vidrio sale.
    - Ventana de medición = [Fin_llegada, Fin_salida)
    - En esa ventana, cada canal mide el vidrio específico:
        FC5 → Vidrio A (Masa A)
        FC4 → Vidrio B (Masa B)
        FC3 → Vidrio C (Masa C)
    - Se calcula Q25 del SR de cada canal en esa ventana.

Uso (desde TESIS_SOILING/):
  python -m analysis.pv_glasses.pv_glasses_calendario

Salidas en analysis/pv_glasses/:
  pv_glasses_por_periodo.csv     SR Q25 por cada medición de cada vidrio
  pv_glasses_resumen.csv         Q25 medio por tipo de período
  pv_glasses_sr_vs_dias.png
  pv_glasses_sr_por_periodo.png
  pv_glasses_curva_acumulacion.png
  pv_glasses_report.md
"""
import os
import sys
import logging
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Mapeo vidrio → canal SR
CANAL_MUESTRA = {
    "A": "SR_R_FC5",
    "B": "SR_R_FC4",
    "C": "SR_R_FC3",
}

# Corrección por transmitancia óptica intrínseca del vidrio:
# FC1/FC2 son celdas desnudas; el vidrio limpio absorbe ~7.5% de luz.
# Se suma este offset para que SR=100% corresponda a vidrio sin suciedad.
CORRECCION_VIDRIO_PCT = 7.5

# Días de referencia por período para la curva de acumulación
DIAS_REFERENCIA = {
    "semanal": 7,
    "2 semanas": 14,
    "Mensual": 30,
    "2 Meses": 56,
    "Trimestral": 91,
    "Cuatrimestral": 120,
    "Semestral": 182,
    "1 año": 365,
}

ORDEN_PERIODO = [
    "semanal", "2 semanas", "Mensual", "2 Meses",
    "Trimestral", "Cuatrimestral", "Semestral", "1 año",
]

# Número de días post-llegada para la ventana de medición
DIAS_POST_LLEGADA = 5

# Ventana alrededor del mediodía solar (horas UTC).
# Solar noon en Atacama ≈ 16:00 UTC → ventana 14-17 UTC (±1.5 h aprox.)
# Se usa el archivo poa_500_clear_sky directamente para no depender del SK.
SOLAR_NOON_HORA_INI_UTC = 14
SOLAR_NOON_HORA_FIN_UTC = 17

# Umbral mínimo de irradiancia REF para calcular SR (W/m²)
MIN_REF_THRESHOLD = 200.0


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def cargar_calendario(csv_path):
    """
    Carga calendario_muestras_seleccionado.csv y devuelve el DataFrame completo.
    Convierte fechas a tipo date.
    """
    df = pd.read_csv(csv_path)
    df["Inicio Exposición"] = pd.to_datetime(df["Inicio Exposición"]).dt.date
    df["Fin Exposicion"]    = pd.to_datetime(df["Fin Exposicion"]).dt.date
    df["Estado"]     = df["Estado"].str.strip().str.lower()
    df["Estructura"] = df["Estructura"].str.strip()
    df["Periodo"]    = df["Periodo"].str.strip()
    logger.info("Calendario cargado: %d filas", len(df))
    return df


def cargar_datos_poa(poa_csv):
    """
    Lee pv_glasses_poa_500_clear_sky.csv (ya filtrado POA>500 y cielo despejado)
    y calcula SR por canal en cada minuto, sin depender de las sesiones del SK.

    Filtros aplicados:
    - Ventana horaria alrededor del mediodía solar (SOLAR_NOON_HORA_INI_UTC–FIN_UTC UTC)
    - REF >= MIN_REF_THRESHOLD
    - FC2 < 1 → SR marcado NaN

    Devuelve DataFrame con columnas: fecha, SR_R_FC3, SR_R_FC4, SR_R_FC5, R_FC2_Avg
    """
    df = pd.read_csv(poa_csv, parse_dates=["_time"])
    df["_time"] = pd.to_datetime(df["_time"], utc=True)

    # Filtrar por ventana horaria UTC
    hora_utc = df["_time"].dt.hour
    df = df[(hora_utc >= SOLAR_NOON_HORA_INI_UTC) & (hora_utc <= SOLAR_NOON_HORA_FIN_UTC)].copy()

    # Filtrar por irradiancia mínima de referencia
    df = df[df["REF"] >= MIN_REF_THRESHOLD].copy()

    # Calcular SR por canal (%)
    for fc in ["R_FC3_Avg", "R_FC4_Avg", "R_FC5_Avg"]:
        col_sr = "SR_" + fc
        df[col_sr] = 100.0 * df[fc] / df["REF"]

    # Marcar NaN cuando FC2 ≈ 0 (sensor apagado o falla)
    mask_fc2 = df["R_FC2_Avg"] < 1.0
    if mask_fc2.any():
        for col in ["SR_R_FC3_Avg", "SR_R_FC4_Avg", "SR_R_FC5_Avg"]:
            df.loc[mask_fc2, col] = np.nan
        logger.info("FC2≈0 en %d minutos → SR marcado NaN", mask_fc2.sum())

    df["fecha"] = df["_time"].dt.date

    n_dias = df["fecha"].nunique()
    logger.info("POA cargado: %d min válidos en %d días (ventana %02d-%02d UTC)",
                len(df), n_dias, SOLAR_NOON_HORA_INI_UTC, SOLAR_NOON_HORA_FIN_UTC)

    # Renombrar para compatibilidad con cruzar_ventanas_sr
    df = df.rename(columns={
        "SR_R_FC3_Avg": "SR_R_FC3",
        "SR_R_FC4_Avg": "SR_R_FC4",
        "SR_R_FC5_Avg": "SR_R_FC5",
    })

    return df[["fecha", "R_FC2_Avg", "SR_R_FC3", "SR_R_FC4", "SR_R_FC5"]]


# ---------------------------------------------------------------------------
# Acumulación de masa (Δm = masa final − masa inicial por exposición)
# ---------------------------------------------------------------------------

def calcular_acumulacion_masa(cal):
    """
    Acumulación de masa Δm = masa_final (soiled) − masa_inicial (clean) por exposición.

    Regla de emparejamiento (para consistencia):
    - La fila 'RC a Fija, clean' con Fin Exposicion = F indica que ese día F se pesaron
      los vidrios limpios (tras una exposición que terminó ese día).
    - Esos mismos vidrios suelen ir a la siguiente exposición **corta** (la que vuelve antes).
    - Por tanto asignamos esa masa inicial solo al evento 'Fija a RC, soiled' con Inicio = F
      que tiene el **menor Fin Exposicion** (vuelve antes). El resto de eventos con mismo
      Inicio = F (p. ej. Semestral) no usan esa masa inicial → Δm = NaN.
    Así evitamos emparejar la misma masa inicial con exposiciones largas que corresponden
    a otro set de vidrios.
    """
    llegadas = cal[
        (cal["Estructura"] == "Fija a RC") & (cal["Estado"] == "soiled")
    ].copy()
    clean_salidas = cal[
        (cal["Estructura"] == "RC a Fija") & (cal["Estado"] == "clean")
    ].copy()
    if clean_salidas.empty:
        logger.warning("No hay filas 'RC a Fija, clean' en el calendario; no se puede calcular Δm.")
        return pd.DataFrame()

    # Quitar duplicados por Fin (quedarse con la primera fila por Fin)
    clean_salidas = clean_salidas.drop_duplicates(subset=["Fin Exposicion"], keep="first")
    clean_por_fin = clean_salidas.set_index("Fin Exposicion")

    # Para cada Fin (fecha de pesada clean), decidir a qué evento (inicio, fin, periodo) asignarla:
    # solo al evento con Inicio = Fin que tiene el menor Fin Exposicion (vuelve antes).
    llegadas["_fin"] = llegadas["Fin Exposicion"]
    llegadas["_inicio"] = llegadas["Inicio Exposición"]
    # Eventos que SÍ reciben masa inicial: por cada inicio_exp, el que tiene fin_llegada mínimo
    asignar_clean = set()
    for inicio_exp, grupo in llegadas.groupby("Inicio Exposición"):
        if inicio_exp not in clean_por_fin.index:
            continue
        # De los que empezaron ese día, el que termina antes (menor Fin Exposicion)
        fin_primero = grupo["Fin Exposicion"].min()
        sub = grupo[grupo["Fin Exposicion"] == fin_primero]
        for _, r in sub.iterrows():
            asignar_clean.add((r["Inicio Exposición"], r["Fin Exposicion"], r["Periodo"]))

    rows = []
    for _, lle in llegadas.iterrows():
        inicio_exp = lle["Inicio Exposición"]
        fin_llegada = lle["Fin Exposicion"]
        periodo = lle["Periodo"]
        dias = int(lle["Exposición"]) if pd.notna(lle["Exposición"]) else np.nan
        mf_a, mf_b, mf_c = float(lle["Masa A"]), float(lle["Masa B"]), float(lle["Masa C"])
        usa_clean = (inicio_exp, fin_llegada, periodo) in asignar_clean

        if not usa_clean or inicio_exp not in clean_por_fin.index:
            for muestra, mf in [("A", mf_a), ("B", mf_b), ("C", mf_c)]:
                if mf >= 0.01:
                    rows.append({
                        "fecha_llegada": fin_llegada,
                        "inicio_exposicion": inicio_exp,
                        "periodo": periodo,
                        "dias_exposicion": dias,
                        "muestra": muestra,
                        "masa_inicial_g": np.nan,
                        "masa_final_g": mf,
                        "delta_m_g": np.nan,
                    })
            continue
        row_clean = clean_por_fin.loc[inicio_exp]
        if isinstance(row_clean, pd.DataFrame):
            row_clean = row_clean.iloc[0]
        mi_a = float(row_clean["Masa A"]) if row_clean["Masa A"] and float(row_clean["Masa A"]) >= 0.01 else np.nan
        mi_b = float(row_clean["Masa B"]) if row_clean["Masa B"] and float(row_clean["Masa B"]) >= 0.01 else np.nan
        mi_c = float(row_clean["Masa C"]) if row_clean["Masa C"] and float(row_clean["Masa C"]) >= 0.01 else np.nan
        for muestra, mf, mi in [("A", mf_a, mi_a), ("B", mf_b, mi_b), ("C", mf_c, mi_c)]:
            if mf < 0.01:
                continue
            if pd.isna(mi) or mi < 0.01:
                delta = np.nan
            else:
                # La acumulación no puede ser negativa (ruido/rotación → reportar 0)
                raw = mf - mi
                delta = round(max(0.0, raw), 6)
            rows.append({
                "fecha_llegada": fin_llegada,
                "inicio_exposicion": inicio_exp,
                "periodo": periodo,
                "dias_exposicion": dias,
                "muestra": muestra,
                "masa_inicial_g": mi if not pd.isna(mi) else np.nan,
                "masa_final_g": mf,
                "delta_m_g": delta,
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["periodo_ord"] = pd.Categorical(df["periodo"], categories=ORDEN_PERIODO, ordered=True)
        df = df.sort_values(["periodo_ord", "fecha_llegada", "muestra"]).reset_index(drop=True)
        n_con_delta = df["delta_m_g"].notna().sum()
        logger.info("Acumulación de masa: %d filas con Δm (de %d); emparejamiento solo al evento que vuelve primero por Inicio.", n_con_delta, len(df))
    return df


# ---------------------------------------------------------------------------
# Matching llegada ↔ salida
# ---------------------------------------------------------------------------

def _masas_similares(row, masa_a, masa_b, masa_c, tol=0.05):
    """Devuelve True si las masas del row coinciden con las de referencia."""
    def cerca(v1, v2):
        if v1 < 0.01 or v2 < 0.01:   # masa=0 → muestra ausente, ignorar
            return True
        return abs(v1 - v2) <= tol
    return (
        cerca(float(row["Masa A"]), masa_a) and
        cerca(float(row["Masa B"]), masa_b) and
        cerca(float(row["Masa C"]), masa_c)
    )


def encontrar_salida(llegada_row, salidas_df):
    """
    Dado un row 'Fija a RC, soiled', encuentra la fila 'RC a Fija, soiled'
    correspondiente: mismo Inicio Exposición, masas similares y fecha posterior.
    """
    inicio  = llegada_row["Inicio Exposición"]
    fin_lle = llegada_row["Fin Exposicion"]
    ma, mb, mc = (float(llegada_row["Masa A"]),
                  float(llegada_row["Masa B"]),
                  float(llegada_row["Masa C"]))

    candidatas = salidas_df[
        (salidas_df["Inicio Exposición"] == inicio) &
        (salidas_df["Fin Exposicion"] > fin_lle)
    ]
    candidatas = candidatas[
        candidatas.apply(lambda r: _masas_similares(r, ma, mb, mc), axis=1)
    ]
    if candidatas.empty:
        return None
    # La salida más próxima en el tiempo
    return candidatas.sort_values("Fin Exposicion").iloc[0]


# ---------------------------------------------------------------------------
# Cálculo principal
# ---------------------------------------------------------------------------

def cruzar_ventanas_sr(cal, sr_df):
    """
    Para cada evento 'Fija a RC, soiled' del calendario:
      1. La ventana de medición comienza el día SIGUIENTE al fin_llegada
         y dura DIAS_POST_LLEGADA días (el vidrio ya está estabilizado).
      2. Extrae SR de cada canal en esa ventana.
      3. Calcula Q25 del SR (absoluto) y aplica corrección +CORRECCION_VIDRIO_PCT
         para obtener el SR de soiling corregido por transmitancia del vidrio.
    Devuelve DataFrame con una fila por (medición, vidrio).
    """
    from datetime import timedelta

    llegadas = cal[
        (cal["Estructura"] == "Fija a RC") & (cal["Estado"] == "soiled")
    ].copy()

    rows = []

    for _, lle in llegadas.iterrows():
        fin_llegada = lle["Fin Exposicion"]
        periodo     = lle["Periodo"]
        dias        = lle["Exposición"]

        # Ventana: DIAS_POST_LLEGADA días después del día de llegada
        fecha_ini = fin_llegada + timedelta(days=1)
        fecha_fin = fin_llegada + timedelta(days=DIAS_POST_LLEGADA)

        ventana_sr = sr_df[
            (sr_df["fecha"] >= fecha_ini) &
            (sr_df["fecha"] <= fecha_fin)
        ]

        for muestra, col_sr in CANAL_MUESTRA.items():
            col_masa = f"Masa {muestra}"
            masa = float(lle[col_masa])
            if masa < 0.01:
                continue   # muestra ausente este período
            if col_sr not in ventana_sr.columns:
                continue

            vals = ventana_sr[col_sr].dropna()
            if vals.empty:
                continue

            sr_q25_abs = vals.quantile(0.25)
            sr_q25_cor = sr_q25_abs + CORRECCION_VIDRIO_PCT  # corrección transmitancia vidrio

            # Contar días únicos con dato (no minutos)
            n_dias_con_dato = ventana_sr.loc[vals.index, "fecha"].nunique()

            rows.append({
                "fecha_llegada":     fin_llegada,
                "ventana_ini":       fecha_ini,
                "ventana_fin":       fecha_fin,
                "inicio_exposicion": lle["Inicio Exposición"],
                "periodo":           periodo,
                "dias_exposicion":   dias,
                "muestra":           muestra,
                "canal":             col_sr,
                "n_dias":            n_dias_con_dato,
                "sr_q25_abs":        sr_q25_abs,       # SR absoluto (FCi/REF)
                "sr_q25":            sr_q25_cor,        # SR corregido (+ 7.5%)
                "sr_media_abs":      vals.mean(),
                "sr_media":          vals.mean() + CORRECCION_VIDRIO_PCT,
                "sr_std":            vals.std(),
                "masa_g":            masa,
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["periodo_ord"] = pd.Categorical(df["periodo"], categories=ORDEN_PERIODO, ordered=True)
    df = df.sort_values(["periodo_ord", "fecha_llegada", "muestra"]).reset_index(drop=True)
    return df


def resumir_por_periodo(df_res):
    """Estadísticos de SR Q25 agrupados por tipo de período."""
    rows = []
    for periodo, grupo in df_res.groupby("periodo", observed=True):
        vals = grupo["sr_q25"].dropna()
        if vals.empty:
            continue
        rows.append({
            "periodo":        periodo,
            "dias_ref":       DIAS_REFERENCIA.get(periodo, np.nan),
            "n_mediciones":   len(vals),
            "sr_q25":         vals.quantile(0.25),
            "sr_mediana":     vals.median(),
            "sr_media":       vals.mean(),
            "sr_std":         vals.std(),
            "perdida_pct":    100.0 - vals.quantile(0.25),
        })
    df = pd.DataFrame(rows)
    df["periodo_ord"] = pd.Categorical(df["periodo"], categories=ORDEN_PERIODO, ordered=True)
    return df.sort_values("periodo_ord").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def grafico_sr_vs_dias(df_res, out_path):
    fig, ax = plt.subplots(figsize=(12, 6))
    colors  = {"A": "#e6194b", "B": "#3cb44b", "C": "#4363d8"}
    markers = {"A": "o",       "B": "s",        "C": "^"}

    for muestra, grupo in df_res.groupby("muestra"):
        ax.scatter(grupo["dias_exposicion"], grupo["sr_q25"],
                   c=colors.get(muestra, "gray"),
                   marker=markers.get(muestra, "o"),
                   s=55, alpha=0.75, label=f"Vidrio {muestra} (FC{'5' if muestra=='A' else '4' if muestra=='B' else '3'})",
                   edgecolors="white", linewidths=0.4)

    df_ok = df_res.dropna(subset=["dias_exposicion", "sr_q25"])
    if len(df_ok) >= 4:
        z  = np.polyfit(df_ok["dias_exposicion"], df_ok["sr_q25"], 1)
        xr = np.linspace(df_ok["dias_exposicion"].min(), df_ok["dias_exposicion"].max(), 100)
        ax.plot(xr, np.polyval(z, xr), "k--", linewidth=1.2, alpha=0.6,
                label=f"Tendencia ({z[0]:.3f} pp/día)")

    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Días de exposición acumulados")
    ax.set_ylabel("SR Q25 en ventana de fotocelda (%)")
    ax.set_title("PV Glasses — SR Q25 vs Días de exposición")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico SR vs días: %s", out_path)


def grafico_sr_por_periodo(df_res, df_resumen, out_path):
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    n = len(periodos_presentes)
    if n == 0:
        return
    colors_m = {"A": "#e6194b", "B": "#3cb44b", "C": "#4363d8"}

    fig, ax = plt.subplots(figsize=(13, 6))
    posiciones = list(range(n))
    datos_box  = [df_res[df_res["periodo"] == p]["sr_q25"].dropna().values
                  for p in periodos_presentes]

    ax.boxplot(datos_box, positions=posiciones, patch_artist=True,
               medianprops=dict(color="black", linewidth=1.5),
               whiskerprops=dict(linewidth=0.8),
               boxprops=dict(facecolor="#d0e8ff", alpha=0.5),
               widths=0.4, showfliers=False)

    jitter = {"A": -0.15, "B": 0.0, "C": 0.15}
    for muestra, color in colors_m.items():
        for p_idx, periodo in enumerate(periodos_presentes):
            sub = df_res[(df_res["periodo"] == periodo) & (df_res["muestra"] == muestra)]
            if sub.empty:
                continue
            ax.scatter([p_idx + jitter[muestra]] * len(sub), sub["sr_q25"],
                       color=color, s=50, alpha=0.85, zorder=5,
                       label=f"Vidrio {muestra}" if p_idx == 0 else "",
                       edgecolors="white", linewidths=0.4)

    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xticks(posiciones)
    ax.set_xticklabels(periodos_presentes, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("SR Q25 en ventana de fotocelda (%)")
    ax.set_title("PV Glasses — SR Q25 por período de exposición")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[:3], labels[:3], fontsize=8, loc="lower left")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico SR por período: %s", out_path)


def grafico_sr_por_periodo_cajas_por_vidrio(df_res, out_path):
    """
    Boxplot por período con una caja por vidrio (A, B, C).
    En cada período hay 3 cajas adyacentes.
    """
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    n_periodos = len(periodos_presentes)
    if n_periodos == 0:
        return
    colors_m = {"A": "#e6194b", "B": "#3cb44b", "C": "#4363d8"}
    muestras = ["A", "B", "C"]
    ancho_caja = 0.22
    # Por cada período: 3 cajas centradas en pos_base - ancho, pos_base, pos_base + ancho
    offsets = {"A": -ancho_caja, "B": 0.0, "C": ancho_caja}

    fig, ax = plt.subplots(figsize=(14, 6))
    posiciones_xtick = []
    # Eje Y: incluir período anual (~80%); etiquetas "n=" van justo encima del borde inferior
    ymin = min(78, float(df_res["sr_q25"].min()) - 2) if df_res["sr_q25"].notna().any() else 78
    y_label_n = ymin + 0.8

    for p_idx, periodo in enumerate(periodos_presentes):
        pos_base = p_idx
        posiciones_xtick.append(pos_base)
        for m_idx, muestra in enumerate(muestras):
            sub = df_res[(df_res["periodo"] == periodo) & (df_res["muestra"] == muestra)]
            vals = sub["sr_q25"].dropna().values
            if len(vals) == 0:
                continue
            pos = pos_base + offsets[muestra]
            n_vals = len(vals)

            if n_vals == 1:
                # Un solo valor: dibujar punto grande en lugar de caja degenerada (para que se vean los 3 vidrios)
                ax.scatter([pos], [vals[0]], color=colors_m[muestra], s=80, alpha=0.85,
                           edgecolors="white", linewidths=0.8, zorder=5)
            else:
                bp = ax.boxplot(
                    [vals],
                    positions=[pos],
                    widths=ancho_caja * 1.6,
                    patch_artist=True,
                    medianprops=dict(color="black", linewidth=1.2),
                    whiskerprops=dict(linewidth=0.8),
                    boxprops=dict(facecolor=colors_m[muestra], alpha=0.6, edgecolor=colors_m[muestra]),
                    showfliers=True,
                    flierprops=dict(marker="o", markersize=4, alpha=0.7, markeredgecolor="none"),
                )
                for patch in bp["boxes"]:
                    patch.set_facecolor(colors_m[muestra])
                    patch.set_alpha(0.6)

            # Número de muestras justo encima del borde inferior del eje
            ax.text(pos, y_label_n, f"n={n_vals}", ha="center", va="bottom", fontsize=7,
                    color=colors_m[muestra], fontweight="normal")

    # Leyenda por vidrio
    from matplotlib.patches import Patch
    ax.legend(
        [Patch(facecolor=colors_m[m], alpha=0.7, label=f"Vidrio {m}") for m in muestras],
        [f"Vidrio {m}" for m in muestras],
        fontsize=9,
        loc="upper right",
    )
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xticks(posiciones_xtick)
    ax.set_xticklabels(periodos_presentes, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("SR Q25 en ventana de fotocelda (%)")
    ax.set_title("PV Glasses — SR Q25 por período de exposición (caja por vidrio)")
    ax.set_ylim(ymin, 105)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico SR por período (cajas por vidrio): %s", out_path)


def grafico_sr_por_vidrio(df_res, out_path):
    """
    Dos paneles: (1) barras Q25 por período y vidrio A/B/C; (2) dispersión de puntos por período.
    Incluye todos los períodos presentes en df_res (incl. 1 año).
    """
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    if not periodos_presentes:
        return
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    MARCADORES = {"A": "o", "B": "s", "C": "^"}
    ymin = min(78, float(df_res["sr_q25"].min()) - 2) if df_res["sr_q25"].notna().any() else 78

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: barras Q25 por período y vidrio
    ax = axes[0]
    resumen = df_res.groupby(["periodo", "muestra"])["sr_q25"].quantile(0.25).unstack("muestra")
    resumen = resumen.reindex(periodos_presentes)
    x = np.arange(len(resumen))
    width = 0.25
    for i, m in enumerate(["A", "B", "C"]):
        vals = resumen[m].values if m in resumen.columns else np.full(len(resumen), np.nan)
        ax.bar(x + (i - 1) * width, vals, width, color=colors_m[m], alpha=0.85, label=f"Vidrio {m}")
    ax.axhline(100, color="gray", ls="--", lw=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(periodos_presentes, rotation=25, ha="right", fontsize=9)
    ax.set_ylim(ymin, 104)
    ax.set_ylabel("SR Q25 (%)")
    ax.set_title("Q25 por período y vidrio")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)

    # Panel 2: dispersión por período
    ax = axes[1]
    for p_idx, periodo in enumerate(periodos_presentes):
        sub = df_res[df_res["periodo"] == periodo]
        for muestra, mk in MARCADORES.items():
            pts = sub[sub["muestra"] == muestra]
            if pts.empty:
                continue
            y_off = {"A": -0.18, "B": 0.0, "C": 0.18}[muestra]
            x_vals = pts["sr_q25"].values
            y_vals = np.full(len(pts), p_idx + y_off)
            ax.scatter(
                x_vals, y_vals,
                c=colors_m[muestra], marker=mk, s=55, alpha=0.8, edgecolors="white", linewidths=0.4,
            )
    ax.set_yticks(range(len(periodos_presentes)))
    ax.set_yticklabels(periodos_presentes, fontsize=9)
    ax.set_xlabel("SR Q25 (%)")
    ax.set_title("Distribución por período y vidrio")
    ax.set_xlim(ymin, 104)
    ax.axvline(100, color="gray", ls="--", lw=0.8, alpha=0.5)
    handles = [plt.Line2D([0], [0], marker=MARCADORES[m], color="w", markerfacecolor=colors_m[m], markersize=9)
               for m in ["A", "B", "C"]]
    ax.legend(handles, ["Vidrio A", "Vidrio B", "Vidrio C"], fontsize=9, loc="upper right")
    ax.grid(True, axis="x", alpha=0.3)

    fig.suptitle("PV Glasses — SR por vidrio (A=FC5, B=FC4, C=FC3)", fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico SR por vidrio: %s", out_path)


def grafico_curva_acumulacion(df_resumen, out_path):
    df = df_resumen.dropna(subset=["dias_ref", "sr_q25"])
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.errorbar(df["dias_ref"], df["sr_q25"],
                yerr=df["sr_std"].fillna(0),
                fmt="o-", color="#1f77b4", linewidth=1.5,
                markersize=7, capsize=4, capthick=1.5,
                label="SR Q25 ± std")
    for _, row in df.iterrows():
        ax.annotate(row["periodo"],
                    (row["dias_ref"], row["sr_q25"]),
                    textcoords="offset points", xytext=(5, 5), fontsize=7)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Días de exposición de referencia")
    ax.set_ylabel("SR Q25 (%)")
    ax.set_title("PV Glasses — Curva de acumulación de soiling por período")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico curva acumulación: %s", out_path)


def grafico_curva_acumulacion_por_vidrio(df_res, out_path):
    """
    Curva de acumulación (SR Q25 vs días de exposición) pero una por vidrio (A, B, C).
    Tres paneles en fila, mismo estilo que grafico_curva_acumulacion.
    """
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    if not periodos_presentes:
        return

    # Resumen por (periodo, muestra): dias_ref, sr_q25, sr_std
    rows = []
    for (periodo, muestra), grupo in df_res.groupby(["periodo", "muestra"], observed=True):
        dias_ref = DIAS_REFERENCIA.get(periodo, np.nan)
        if np.isnan(dias_ref):
            continue
        vals = grupo["sr_q25"].dropna()
        if vals.empty:
            continue
        rows.append({
            "periodo": periodo,
            "muestra": muestra,
            "dias_ref": dias_ref,
            "sr_q25": vals.quantile(0.25),
            "sr_std": vals.std() if len(vals) > 1 else 0,
        })
    if not rows:
        return
    res = pd.DataFrame(rows)

    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    titulos = {"A": "Vidrio A (FC5)", "B": "Vidrio B (FC4)", "C": "Vidrio C (FC3)"}

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    ymin = 78
    for col, muestra in enumerate(["A", "B", "C"]):
        ax = axes[col]
        sub = res[res["muestra"] == muestra].sort_values("dias_ref")
        if sub.empty:
            ax.set_title(titulos[muestra])
            ax.set_visible(True)
            continue
        ax.errorbar(
            sub["dias_ref"], sub["sr_q25"],
            yerr=sub["sr_std"].fillna(0),
            fmt="o-", color=colors_m[muestra], linewidth=1.5,
            markersize=7, capsize=4, capthick=1.5,
            label="SR Q25 ± std",
        )
        for _, row in sub.iterrows():
            ax.annotate(
                row["periodo"],
                (row["dias_ref"], row["sr_q25"]),
                textcoords="offset points", xytext=(5, 5), fontsize=7,
            )
        ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_xlabel("Días de exposición de referencia")
        if col == 0:
            ax.set_ylabel("SR Q25 (%)")
        ax.set_ylim(ymin, 105)
        ax.set_title(titulos[muestra])
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    fig.suptitle(
        "PV Glasses — Curva de acumulación de soiling por período (por vidrio)",
        fontsize=12, fontweight="bold", y=1.02,
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico curva acumulación por vidrio: %s", out_path)


def grafico_datos_detalle_por_vidrio(df_res, n_dias_poa, out_path):
    """
    Gráfico tipo 'datos detalle' pero separado por vidrio: 2 filas (SR vs Fecha, SR vs Días)
    y 3 columnas (Vidrio A, B, C). Cada celda muestra puntos por período de exposición.
    """
    import matplotlib.dates as mdates

    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    if not periodos_presentes:
        return

    # Colores por período (estilo del gráfico de detalle original)
    cmap_periodo = {
        "semanal":       "#1f77b4",
        "2 semanas":     "#2ca02c",
        "Mensual":       "#ff7f0e",
        "2 Meses":       "#d62728",
        "Trimestral":    "#9467bd",
        "Cuatrimestral": "#8c564b",
        "Semestral":     "#e377c2",
        "1 año":         "#7f7f7f",
    }
    colores = [cmap_periodo.get(p, "#333") for p in periodos_presentes]
    vidrios = ["A", "B", "C"]
    titulos_vidrio = {"A": "Vidrio A (FC5)", "B": "Vidrio B (FC4)", "C": "Vidrio C (FC3)"}

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    # Eje Y común
    ymin = min(78, float(df_res["sr_q25"].min()) - 2) if df_res["sr_q25"].notna().any() else 78

    for col, muestra in enumerate(vidrios):
        sub = df_res[df_res["muestra"] == muestra].copy()
        if sub.empty:
            axes[0, col].set_title(titulos_vidrio[muestra])
            axes[1, col].set_visible(True)
            continue

        sub["fecha_llegada_dt"] = pd.to_datetime(sub["fecha_llegada"])

        # Panel 1: SR vs Fecha de medición
        ax = axes[0, col]
        for p_idx, periodo in enumerate(periodos_presentes):
            mask = sub["periodo"] == periodo
            if not mask.any():
                continue
            s = sub.loc[mask]
            ax.scatter(
                s["fecha_llegada_dt"], s["sr_q25"],
                c=colores[p_idx], s=45, alpha=0.85, edgecolors="white", linewidths=0.4,
                label=periodo,
            )
            # Etiqueta días de exposición en algunos puntos (evitar saturación)
            for _, row in s.iterrows():
                ax.annotate(
                    str(int(row["dias_exposicion"])),
                    (row["fecha_llegada_dt"], row["sr_q25"]),
                    textcoords="offset points", xytext=(4, 4), fontsize=6, alpha=0.8,
                )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_ylabel("SR Q25 (%)")
        ax.set_ylim(ymin, 105)
        ax.set_title(titulos_vidrio[muestra])
        ax.grid(True, axis="y", alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=25, ha="right")
        if col == 0:
            ax.set_title(f"Panel 1 — SR vs Fecha (datos POA: {n_dias_poa} días)\n{titulos_vidrio[muestra]}")
        else:
            ax.set_title(titulos_vidrio[muestra])

        # Panel 2: SR vs Días de exposición
        ax = axes[1, col]
        for p_idx, periodo in enumerate(periodos_presentes):
            mask = sub["periodo"] == periodo
            if not mask.any():
                continue
            s = sub.loc[mask].sort_values("dias_exposicion")
            ax.scatter(
                s["dias_exposicion"], s["sr_q25"],
                c=colores[p_idx], s=45, alpha=0.85, edgecolors="white", linewidths=0.4,
                label=periodo,
            )
            if len(s) > 1:
                ax.plot(
                    s["dias_exposicion"], s["sr_q25"],
                    color=colores[p_idx], linewidth=1.2, alpha=0.6, zorder=0,
                )
            for _, row in s.iterrows():
                lbl = pd.to_datetime(row["fecha_llegada"]).strftime("%b %y")
                ax.annotate(
                    lbl,
                    (row["dias_exposicion"], row["sr_q25"]),
                    textcoords="offset points", xytext=(4, 4), fontsize=6, alpha=0.8,
                )
        ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_xlabel("Días de exposición")
        ax.set_ylabel("SR Q25 (%)")
        ax.set_ylim(ymin, 105)
        if col == 0:
            ax.set_title(f"Panel 2 — SR vs Días de exposición\n{titulos_vidrio[muestra]}")
        else:
            ax.set_title(titulos_vidrio[muestra])
        ax.grid(True, alpha=0.3)
        if col == 2:
            ax.legend(loc="upper right", fontsize=7, bbox_to_anchor=(1.22, 1.0))

    fig.suptitle(
        "PV Glasses — Detalle por vidrio (etiquetas: días de exposición en Panel 1; fecha en Panel 2)",
        fontsize=11, fontweight="bold", y=1.02,
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico datos detalle por vidrio: %s", out_path)


# ---------------------------------------------------------------------------
# Análisis de masas
# ---------------------------------------------------------------------------

def guardar_tabla_masas_por_periodo_por_vidrio(df_res, out_dir):
    """Tabla de masa (g) por período y vidrio: media, mediana, min, max, n."""
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    rows = []
    for periodo in periodos_presentes:
        sub = df_res[df_res["periodo"] == periodo]
        row = {"Período": periodo}
        for muestra in ["A", "B", "C"]:
            vals = sub[sub["muestra"] == muestra]["masa_g"].dropna()
            if vals.empty:
                row[f"Vidrio {muestra} (media g)"] = ""
                row[f"Vidrio {muestra} (mediana g)"] = ""
                row[f"Vidrio {muestra} (min–max)"] = ""
                row[f"Vidrio {muestra} (n)"] = ""
            else:
                row[f"Vidrio {muestra} (media g)"] = round(vals.mean(), 4)
                row[f"Vidrio {muestra} (mediana g)"] = round(vals.median(), 4)
                row[f"Vidrio {muestra} (min–max)"] = f"{vals.min():.2f}–{vals.max():.2f}"
                row[f"Vidrio {muestra} (n)"] = int(len(vals))
        rows.append(row)
    tabla = pd.DataFrame(rows)
    csv_path = os.path.join(out_dir, "pv_glasses_masas_por_periodo_por_vidrio.csv")
    tabla.to_csv(csv_path, index=False)
    logger.info("Tabla masas por período y vidrio: %s", csv_path)

    md_path = os.path.join(out_dir, "pv_glasses_masas_por_periodo_por_vidrio_tabla.md")
    lines = [
        "# PV Glasses — Masa (g) por período y vidrio",
        "",
        "Masa del vidrio al llegar a la fotocelda (calendario: Masa A/B/C). Media, mediana, rango y n.",
        "",
        "| Período | Vidrio A (media g) | Vidrio A (mediana g) | Vidrio A (min–max) | Vidrio A (n) | "
        "Vidrio B (media g) | Vidrio B (mediana g) | Vidrio B (min–max) | Vidrio B (n) | "
        "Vidrio C (media g) | Vidrio C (mediana g) | Vidrio C (min–max) | Vidrio C (n) |",
        "|---------|--------------------|----------------------|--------------------|--------------|"
        "--------------------|----------------------|--------------------|--------------|"
        "--------------------|----------------------|--------------------|--------------|",
    ]
    def _v(val):
        if val == "" or (isinstance(val, float) and np.isnan(val)):
            return "—"
        return f"{val:.4f}" if isinstance(val, (int, float)) else str(val)
    def _n(val):
        if val == "" or (isinstance(val, float) and np.isnan(val)):
            return "—"
        return str(int(val)) if isinstance(val, (int, float)) else str(val)
    for _, r in tabla.iterrows():
        lines.append(
            f"| {r['Período']} | {_v(r.get('Vidrio A (media g)'))} | {_v(r.get('Vidrio A (mediana g)'))} | {r.get('Vidrio A (min–max)', '—')} | {_n(r.get('Vidrio A (n)'))} | "
            f"{_v(r.get('Vidrio B (media g)'))} | {_v(r.get('Vidrio B (mediana g)'))} | {r.get('Vidrio B (min–max)', '—')} | {_n(r.get('Vidrio B (n)'))} | "
            f"{_v(r.get('Vidrio C (media g)'))} | {_v(r.get('Vidrio C (mediana g)'))} | {r.get('Vidrio C (min–max)', '—')} | {_n(r.get('Vidrio C (n)'))} |"
        )
    lines += ["", "- **Vidrio A** → FC5, **Vidrio B** → FC4, **Vidrio C** → FC3.", ""]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Tabla Markdown masas: %s", md_path)


def guardar_resumen_masas(df_res, out_dir):
    """Resumen de masa (g) por período (agregado, sin desglose por vidrio)."""
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    rows = []
    for periodo in periodos_presentes:
        vals = df_res[df_res["periodo"] == periodo]["masa_g"].dropna()
        if vals.empty:
            continue
        rows.append({
            "periodo": periodo,
            "dias_ref": DIAS_REFERENCIA.get(periodo, np.nan),
            "n": len(vals),
            "masa_media_g": round(vals.mean(), 4),
            "masa_mediana_g": round(vals.median(), 4),
            "masa_min_g": round(vals.min(), 4),
            "masa_max_g": round(vals.max(), 4),
            "masa_std_g": round(vals.std(), 4) if len(vals) > 1 else 0,
        })
    if not rows:
        return
    res = pd.DataFrame(rows)
    md_path = os.path.join(out_dir, "pv_glasses_masas_resumen.md")
    lines = [
        "# PV Glasses — Resumen de masa (g) por período",
        "",
        "| Período | Días ref. | n | Masa media (g) | Masa mediana (g) | Masa min–max (g) | Std (g) |",
        "|---------|-----------|---|----------------|------------------|------------------|--------|",
    ]
    for _, r in res.iterrows():
        dias = int(r["dias_ref"]) if pd.notna(r["dias_ref"]) else "—"
        lines.append(
            f"| {r['periodo']} | {dias} | {int(r['n'])} | "
            f"{r['masa_media_g']:.4f} | {r['masa_mediana_g']:.4f} | "
            f"{r['masa_min_g']:.2f}–{r['masa_max_g']:.2f} | {r['masa_std_g']:.4f} |"
        )
    lines += ["", "- Masa = peso del vidrio al llegar a la fotocelda (calendario).", ""]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    res.to_csv(os.path.join(out_dir, "pv_glasses_masas_resumen.csv"), index=False)
    logger.info("Resumen masas: %s", md_path)


def grafico_masa_por_periodo_por_vidrio(df_res, out_path):
    """Masa (g) por período de exposición, una serie por vidrio (barras o cajas)."""
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    if not periodos_presentes:
        return
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(periodos_presentes))
    w = 0.25
    for i, m in enumerate(["A", "B", "C"]):
        medias = []
        for p in periodos_presentes:
            vals = df_res[(df_res["periodo"] == p) & (df_res["muestra"] == m)]["masa_g"].dropna()
            medias.append(vals.mean() if not vals.empty else np.nan)
        ax.bar(x + (i - 1) * w, medias, w, color=colors_m[m], alpha=0.85, label=f"Vidrio {m}")
    ax.set_xticks(x)
    ax.set_xticklabels(periodos_presentes, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Masa (g)")
    ax.set_xlabel("Período de exposición")
    ax.set_title("PV Glasses — Masa media por período y vidrio")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico masa por período y vidrio: %s", out_path)


def grafico_masa_vs_dias(df_res, out_path):
    """Dispersión: masa (g) vs días de exposición, colores por vidrio."""
    df_ok = df_res.dropna(subset=["masa_g", "dias_exposicion"])
    if df_ok.empty:
        return
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    markers = {"A": "o", "B": "s", "C": "^"}
    fig, ax = plt.subplots(figsize=(10, 5))
    for muestra, grupo in df_ok.groupby("muestra"):
        ax.scatter(
            grupo["dias_exposicion"], grupo["masa_g"],
            c=colors_m.get(muestra, "gray"), marker=markers.get(muestra, "o"),
            s=50, alpha=0.8, label=f"Vidrio {muestra}", edgecolors="white", linewidths=0.4,
        )
    ax.set_xlabel("Días de exposición acumulados")
    ax.set_ylabel("Masa (g)")
    ax.set_title("PV Glasses — Masa del vidrio vs días de exposición")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico masa vs días: %s", out_path)


def grafico_masa_vs_sr(df_res, out_path):
    """Dispersión: masa (g) vs SR Q25 (%), colores por vidrio."""
    df_ok = df_res.dropna(subset=["masa_g", "sr_q25"])
    if df_ok.empty:
        return
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    markers = {"A": "o", "B": "s", "C": "^"}
    fig, ax = plt.subplots(figsize=(10, 5))
    for muestra, grupo in df_ok.groupby("muestra"):
        ax.scatter(
            grupo["masa_g"], grupo["sr_q25"],
            c=colors_m.get(muestra, "gray"), marker=markers.get(muestra, "o"),
            s=50, alpha=0.8, label=f"Vidrio {muestra}", edgecolors="white", linewidths=0.4,
        )
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Masa (g)")
    ax.set_ylabel("SR Q25 (%)")
    ax.set_title("PV Glasses — Masa del vidrio vs SR Q25")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico masa vs SR: %s", out_path)


# ---------------------------------------------------------------------------
# Análisis de acumulación de masa (Δm por período)
# ---------------------------------------------------------------------------

def guardar_tabla_acumulacion_masa_por_periodo_por_vidrio(df_res, out_dir):
    """Tabla de acumulación de masa Δm (g) por período y vidrio: media, mediana, min, max, n."""
    if "delta_m_g" not in df_res.columns:
        return
    df_ok = df_res.dropna(subset=["delta_m_g"])
    if df_ok.empty:
        logger.warning("No hay datos de Δm para tablas.")
        return
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_ok["periodo"].values]
    rows = []
    for periodo in periodos_presentes:
        sub = df_ok[df_ok["periodo"] == periodo]
        row = {"Período": periodo}
        for muestra in ["A", "B", "C"]:
            vals = sub[sub["muestra"] == muestra]["delta_m_g"]
            if vals.empty:
                row[f"Vidrio {muestra} (Δm media g)"] = ""
                row[f"Vidrio {muestra} (Δm mediana g)"] = ""
                row[f"Vidrio {muestra} (Δm min–max)"] = ""
                row[f"Vidrio {muestra} (n)"] = ""
            else:
                row[f"Vidrio {muestra} (Δm media g)"] = round(vals.mean(), 5)
                row[f"Vidrio {muestra} (Δm mediana g)"] = round(vals.median(), 5)
                row[f"Vidrio {muestra} (Δm min–max)"] = f"{vals.min():.4f}–{vals.max():.4f}"
                row[f"Vidrio {muestra} (n)"] = int(len(vals))
        rows.append(row)
    tabla = pd.DataFrame(rows)
    csv_path = os.path.join(out_dir, "pv_glasses_acumulacion_masa_por_periodo_por_vidrio.csv")
    tabla.to_csv(csv_path, index=False)
    logger.info("Tabla acumulación masa por período y vidrio: %s", csv_path)

    md_path = os.path.join(out_dir, "pv_glasses_acumulacion_masa_por_periodo_por_vidrio_tabla.md")
    def _v(val):
        if val == "" or (isinstance(val, float) and np.isnan(val)):
            return "—"
        return f"{val:.5f}" if isinstance(val, (int, float)) else str(val)
    def _n(val):
        if val == "" or (isinstance(val, float) and np.isnan(val)):
            return "—"
        return str(int(val)) if isinstance(val, (int, float)) else str(val)
    lines = [
        "# PV Glasses — Acumulación de masa (Δm, g) por período y vidrio",
        "",
        "Δm = masa al llegar (soiled) − masa inicial (clean al salir). Si Δm bruto &lt; 0 se reporta 0. Solo se usa masa inicial para el evento que vuelve primero por cada fecha de inicio.",
        "",
        "| Período | Vidrio A (Δm media g) | Vidrio A (Δm mediana g) | Vidrio A (Δm min–max) | Vidrio A (n) | "
        "Vidrio B (Δm media g) | Vidrio B (Δm mediana g) | Vidrio B (Δm min–max) | Vidrio B (n) | "
        "Vidrio C (Δm media g) | Vidrio C (Δm mediana g) | Vidrio C (Δm min–max) | Vidrio C (n) |",
        "|---------|------------------------|--------------------------|------------------------|--------------|"
        "------------------------|--------------------------|------------------------|--------------|"
        "------------------------|--------------------------|------------------------|--------------|",
    ]
    for _, r in tabla.iterrows():
        lines.append(
            f"| {r['Período']} | {_v(r.get('Vidrio A (Δm media g)'))} | {_v(r.get('Vidrio A (Δm mediana g)'))} | {r.get('Vidrio A (Δm min–max)', '—')} | {_n(r.get('Vidrio A (n)'))} | "
            f"{_v(r.get('Vidrio B (Δm media g)'))} | {_v(r.get('Vidrio B (Δm mediana g)'))} | {r.get('Vidrio B (Δm min–max)', '—')} | {_n(r.get('Vidrio B (n)'))} | "
            f"{_v(r.get('Vidrio C (Δm media g)'))} | {_v(r.get('Vidrio C (Δm mediana g)'))} | {r.get('Vidrio C (Δm min–max)', '—')} | {_n(r.get('Vidrio C (n)'))} |"
        )
    lines += ["", "- **Vidrio A** → FC5, **Vidrio B** → FC4, **Vidrio C** → FC3.", ""]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Tabla Markdown acumulación masa: %s", md_path)


def guardar_resumen_acumulacion_masa(df_res, out_dir):
    """Resumen de acumulación de masa Δm (g) por período (agregado)."""
    if "delta_m_g" not in df_res.columns:
        return
    df_ok = df_res.dropna(subset=["delta_m_g"])
    if df_ok.empty:
        return
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_ok["periodo"].values]
    rows = []
    for periodo in periodos_presentes:
        vals = df_ok[df_ok["periodo"] == periodo]["delta_m_g"]
        if vals.empty:
            continue
        rows.append({
            "periodo": periodo,
            "dias_ref": DIAS_REFERENCIA.get(periodo, np.nan),
            "n": len(vals),
            "delta_m_media_g": round(vals.mean(), 5),
            "delta_m_mediana_g": round(vals.median(), 5),
            "delta_m_min_g": round(vals.min(), 5),
            "delta_m_max_g": round(vals.max(), 5),
            "delta_m_std_g": round(vals.std(), 5) if len(vals) > 1 else 0,
        })
    if not rows:
        return
    res = pd.DataFrame(rows)
    md_path = os.path.join(out_dir, "pv_glasses_acumulacion_masa_resumen.md")
    lines = [
        "# PV Glasses — Resumen de acumulación de masa (Δm, g) por período",
        "",
        "Δm = masa final (soiled) − masa inicial (clean). Si da negativo (ruido/rotación) se reporta 0.",
        "Solo se asigna masa inicial al evento que **vuelve antes** por cada fecha de inicio (mismo set de vidrios).",
        "",
        "| Período | Días ref. | n | Δm media (g) | Δm mediana (g) | Δm min–max (g) | Std (g) |",
        "|---------|-----------|---|--------------|----------------|----------------|--------|",
    ]
    for _, r in res.iterrows():
        dias = int(r["dias_ref"]) if pd.notna(r["dias_ref"]) else "—"
        lines.append(
            f"| {r['periodo']} | {dias} | {int(r['n'])} | "
            f"{r['delta_m_media_g']:.5f} | {r['delta_m_mediana_g']:.5f} | "
            f"{r['delta_m_min_g']:.4f}–{r['delta_m_max_g']:.4f} | {r['delta_m_std_g']:.5f} |"
        )
    lines += ["", ""]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    res.to_csv(os.path.join(out_dir, "pv_glasses_acumulacion_masa_resumen.csv"), index=False)
    logger.info("Resumen acumulación masa: %s", md_path)


def grafico_acumulacion_masa_por_periodo_por_vidrio(df_res, out_path):
    """Acumulación de masa Δm (g) por período, una serie por vidrio (barras)."""
    if "delta_m_g" not in df_res.columns:
        return
    df_ok = df_res.dropna(subset=["delta_m_g"])
    if df_ok.empty:
        return
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_ok["periodo"].values]
    if not periodos_presentes:
        return
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(periodos_presentes))
    w = 0.25
    for i, m in enumerate(["A", "B", "C"]):
        medias = []
        for p in periodos_presentes:
            vals = df_ok[(df_ok["periodo"] == p) & (df_ok["muestra"] == m)]["delta_m_g"]
            medias.append(vals.mean() if not vals.empty else np.nan)
        ax.bar(x + (i - 1) * w, medias, w, color=colors_m[m], alpha=0.85, label=f"Vidrio {m}")
    ax.set_xticks(x)
    ax.set_xticklabels(periodos_presentes, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Acumulación de masa Δm (g)")
    ax.set_xlabel("Período de exposición")
    ax.set_title("PV Glasses — Acumulación de masa por período y vidrio (Δm = masa final − inicial)")
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico acumulación masa por período y vidrio: %s", out_path)


def grafico_acumulacion_masa_vs_dias(df_res, out_path):
    """Dispersión: Δm (g) vs días de exposición, colores por vidrio."""
    if "delta_m_g" not in df_res.columns:
        return
    df_ok = df_res.dropna(subset=["delta_m_g", "dias_exposicion"])
    if df_ok.empty:
        return
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    markers = {"A": "o", "B": "s", "C": "^"}
    fig, ax = plt.subplots(figsize=(10, 5))
    for muestra, grupo in df_ok.groupby("muestra"):
        ax.scatter(
            grupo["dias_exposicion"], grupo["delta_m_g"],
            c=colors_m.get(muestra, "gray"), marker=markers.get(muestra, "o"),
            s=50, alpha=0.8, label=f"Vidrio {muestra}", edgecolors="white", linewidths=0.4,
        )
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Días de exposición acumulados")
    ax.set_ylabel("Acumulación de masa Δm (g)")
    ax.set_title("PV Glasses — Acumulación de masa vs días de exposición")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico acumulación masa vs días: %s", out_path)


def grafico_acumulacion_masa_vs_sr(df_res, out_path):
    """Dispersión: Δm (g) vs SR Q25 (%), colores por vidrio."""
    if "delta_m_g" not in df_res.columns:
        return
    df_ok = df_res.dropna(subset=["delta_m_g", "sr_q25"])
    if df_ok.empty:
        return
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    markers = {"A": "o", "B": "s", "C": "^"}
    fig, ax = plt.subplots(figsize=(10, 5))
    for muestra, grupo in df_ok.groupby("muestra"):
        ax.scatter(
            grupo["delta_m_g"], grupo["sr_q25"],
            c=colors_m.get(muestra, "gray"), marker=markers.get(muestra, "o"),
            s=50, alpha=0.8, label=f"Vidrio {muestra}", edgecolors="white", linewidths=0.4,
        )
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Acumulación de masa Δm (g)")
    ax.set_ylabel("SR Q25 (%)")
    ax.set_title("PV Glasses — Acumulación de masa vs SR Q25")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico acumulación masa vs SR: %s", out_path)


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def generar_reporte(df_res, df_resumen, out_path):
    lines = [
        "# PV Glasses — Análisis integrado con Calendario de Muestras",
        "",
        "**Método:** Q25 del SR calculado durante la ventana [Fija→RC, RC→Fija),",
        "es decir, los días en que el vidrio sucio está efectivamente sobre la fotocelda.  ",
        "**Mapeo:** FC5=Vidrio A · FC4=Vidrio B · FC3=Vidrio C  ",
        f"**Total de mediciones procesadas:** {len(df_res)}  ",
        "",
        "---",
        "## 1. SR Q25 por tipo de período de exposición",
        "",
        "| Período | Días ref. | N mediciones | SR Q25 (%) | Pérdida (pp) | Std (pp) |",
        "|---|---|---|---|---|---|",
    ]
    for _, row in df_resumen.iterrows():
        dias = int(row["dias_ref"]) if pd.notna(row["dias_ref"]) else "—"
        lines.append(
            f"| {row['periodo']} | {dias} "
            f"| {int(row['n_mediciones'])} "
            f"| {row['sr_q25']:.2f} "
            f"| {row['perdida_pct']:.2f} "
            f"| {row['sr_std']:.2f} |"
        )

    lines += ["", "---", "## 2. Observaciones clave", ""]

    df_ok = df_res.dropna(subset=["dias_exposicion", "sr_q25"])
    if len(df_ok) >= 4:
        z = np.polyfit(df_ok["dias_exposicion"], df_ok["sr_q25"], 1)
        lines.append(
            f"- **Tasa de acumulación lineal:** {z[0]:.4f} pp/día "
            f"({abs(z[0]) * 365:.2f} pp/año estimados)"
        )

    if not df_resumen.empty:
        fila_max = df_resumen.loc[df_resumen["perdida_pct"].idxmax()]
        lines.append(
            f"- **Período con mayor pérdida (Q25):** {fila_max['periodo']} "
            f"({fila_max['perdida_pct']:.2f} pp)"
        )
        fila_min = df_resumen.loc[df_resumen["perdida_pct"].idxmin()]
        lines.append(
            f"- **Período con menor pérdida (Q25):** {fila_min['periodo']} "
            f"({fila_min['perdida_pct']:.2f} pp)"
        )

    lines += [
        "", "---", "## 3. Limitaciones", "",
        "- Los días en que FC2 ≈ 0 el SR fue marcado NaN y excluido.",
        "- Masa = 0 en algunos períodos indica muestra ausente (excluida).",
        "- La ventana de medición excluye el día de salida (fin_salida).",
        "",
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Reporte: %s", out_path)


def grafico_q25_y_mediana(df_res, df_resumen, out_path):
    """
    Gráficos de los resultados Q25 y mediana: (1) Resumen por período (barras Q25 vs Mediana);
    (2) Por período y vidrio: dos paneles (Q25 por vidrio, Mediana por vidrio).
    """
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    if not periodos_presentes or df_resumen.empty or "sr_mediana" not in df_resumen.columns:
        return
    df_resumen = df_resumen[df_resumen["periodo"].isin(periodos_presentes)]
    colors_m = {"A": "#E53935", "B": "#1E88E5", "C": "#43A047"}
    ymin = min(78, float(df_res["sr_q25"].min()) - 2) if df_res["sr_q25"].notna().any() else 78

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel (0,0): Resumen por período — Q25 y Mediana (barras agrupadas)
    ax = axes[0, 0]
    x = np.arange(len(periodos_presentes))
    width = 0.35
    q25_vals = df_resumen.set_index("periodo").reindex(periodos_presentes)["sr_q25"].values
    med_vals = df_resumen.set_index("periodo").reindex(periodos_presentes)["sr_mediana"].values
    ax.bar(x - width / 2, q25_vals, width, label="SR Q25 (%)", color="#1f77b4", alpha=0.85)
    ax.bar(x + width / 2, med_vals, width, label="SR mediana (%)", color="#ff7f0e", alpha=0.85)
    ax.axhline(100, color="gray", ls="--", lw=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(periodos_presentes, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("SR (%)")
    ax.set_ylim(ymin, 104)
    ax.set_title("Resumen por período (Q25 y mediana)")
    ax.legend(fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)

    # Panel (0,1): Q25 por período y vidrio (barras)
    ax = axes[0, 1]
    resumen_q25 = df_res.groupby(["periodo", "muestra"])["sr_q25"].quantile(0.25).unstack("muestra")
    resumen_q25 = resumen_q25.reindex(periodos_presentes)
    x = np.arange(len(periodos_presentes))
    w = 0.25
    for i, m in enumerate(["A", "B", "C"]):
        vals = resumen_q25[m].values if m in resumen_q25.columns else np.full(len(periodos_presentes), np.nan)
        ax.bar(x + (i - 1) * w, vals, w, color=colors_m[m], alpha=0.85, label=f"Vidrio {m}")
    ax.axhline(100, color="gray", ls="--", lw=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(periodos_presentes, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("SR Q25 (%)")
    ax.set_ylim(ymin, 104)
    ax.set_title("Q25 por período y vidrio")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)

    # Panel (1,0): Mediana por período y vidrio (barras)
    ax = axes[1, 0]
    resumen_med = df_res.groupby(["periodo", "muestra"])["sr_q25"].median().unstack("muestra")
    resumen_med = resumen_med.reindex(periodos_presentes)
    for i, m in enumerate(["A", "B", "C"]):
        vals = resumen_med[m].values if m in resumen_med.columns else np.full(len(periodos_presentes), np.nan)
        ax.bar(x + (i - 1) * w, vals, w, color=colors_m[m], alpha=0.85, label=f"Vidrio {m}")
    ax.axhline(100, color="gray", ls="--", lw=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(periodos_presentes, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("SR mediana (%)")
    ax.set_ylim(ymin, 104)
    ax.set_title("Mediana por período y vidrio")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)

    # Panel (1,1): Resumen por período — pérdida (pp) desde Q25
    ax = axes[1, 1]
    perdida = (100 - df_resumen.set_index("periodo").reindex(periodos_presentes)["sr_q25"]).values
    ax.bar(x, perdida, width=0.5, color="#2ca02c", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(periodos_presentes, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Pérdida (pp, desde Q25)")
    ax.set_title("Pérdida de SR por período")
    ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle(
        "PV Glasses — Resultados Q25 y mediana (mismo contenido que tablas .md/.csv)",
        fontsize=12, fontweight="bold", y=1.02,
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico Q25 y mediana: %s", out_path)


def guardar_tabla_sr_por_periodo_por_vidrio(df_res, out_dir):
    """
    Tablas SR por período y vidrio con **Q25** y **mediana**.
    Genera CSV y MD con ambas métricas para cada vidrio.
    """
    periodos_presentes = [p for p in ORDEN_PERIODO if p in df_res["periodo"].values]
    rows = []
    for periodo in periodos_presentes:
        sub = df_res[df_res["periodo"] == periodo]
        row = {"Período": periodo}
        for muestra in ["A", "B", "C"]:
            vals = sub[sub["muestra"] == muestra]["sr_q25"].dropna()
            if vals.empty:
                row[f"Vidrio {muestra} (Q25 %)"] = ""
                row[f"Vidrio {muestra} (mediana %)"] = ""
                row[f"Vidrio {muestra} (n)"] = ""
            else:
                row[f"Vidrio {muestra} (Q25 %)"] = round(vals.quantile(0.25), 2)
                row[f"Vidrio {muestra} (mediana %)"] = round(vals.median(), 2)
                row[f"Vidrio {muestra} (n)"] = int(len(vals))
        rows.append(row)
    tabla = pd.DataFrame(rows)

    csv_path = os.path.join(out_dir, "pv_glasses_sr_por_periodo_por_vidrio.csv")
    tabla.to_csv(csv_path, index=False)
    logger.info("Tabla SR por vidrio (Q25 + mediana): %s", csv_path)

    def _sr(v):
        return f"{v:.2f}" if pd.notna(v) and v != "" else "—"
    def _n(v):
        return v if v != "" else "—"

    md_path = os.path.join(out_dir, "pv_glasses_sr_por_periodo_por_vidrio_tabla.md")
    md_lines = [
        "# PV Glasses — SR por período y vidrio (Q25 y mediana)",
        "",
        "Dos métricas sobre los valores de SR en ventana por (período, vidrio):",
        "- **Q25**: percentil 25 (conservador, coherente con el resto del pipeline).",
        "- **Mediana**: valor central (más estable con pocos datos). *n* = número de mediciones.",
        "",
        "| Período | Vidrio A (Q25 %) | Vidrio A (mediana %) | Vidrio A (n) | "
        "Vidrio B (Q25 %) | Vidrio B (mediana %) | Vidrio B (n) | "
        "Vidrio C (Q25 %) | Vidrio C (mediana %) | Vidrio C (n) |",
        "|---------|------------------|----------------------|--------------|"
        "------------------|----------------------|--------------|"
        "------------------|----------------------|--------------|",
    ]
    for _, r in tabla.iterrows():
        md_lines.append(
            f"| {r['Período']} | {_sr(r['Vidrio A (Q25 %)'])} | {_sr(r['Vidrio A (mediana %)'])} | {_n(r['Vidrio A (n)'])} | "
            f"{_sr(r['Vidrio B (Q25 %)'])} | {_sr(r['Vidrio B (mediana %)'])} | {_n(r['Vidrio B (n)'])} | "
            f"{_sr(r['Vidrio C (Q25 %)'])} | {_sr(r['Vidrio C (mediana %)'])} | {_n(r['Vidrio C (n)'])} |"
        )
    md_lines += [
        "",
        "- **Vidrio A** → FC5, **Vidrio B** → FC4, **Vidrio C** → FC3. SR corregido (+7.5%).",
        "",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    logger.info("Tabla Markdown: %s", md_path)


def guardar_resumen_q25_y_mediana(df_resumen, out_dir):
    """Resumen por período con Q25 y mediana (sin desglose por vidrio)."""
    if df_resumen.empty or "sr_mediana" not in df_resumen.columns:
        return
    md_path = os.path.join(out_dir, "pv_glasses_resumen_q25_y_mediana.md")
    lines = [
        "# PV Glasses — Resumen por período (Q25 y mediana)",
        "",
        "| Período | Días ref. | n | SR Q25 (%) | SR mediana (%) | Pérdida (pp, Q25) |",
        "|---------|-----------|---|------------|----------------|-------------------|",
    ]
    for _, r in df_resumen.iterrows():
        dias = int(r["dias_ref"]) if pd.notna(r["dias_ref"]) else "—"
        lines.append(
            f"| {r['periodo']} | {dias} | {int(r['n_mediciones'])} | "
            f"{r['sr_q25']:.2f} | {r['sr_mediana']:.2f} | {r['perdida_pct']:.2f} |"
        )
    lines += ["", "- **SR Q25**: percentil 25 (conservador). **SR mediana**: valor central.", ""]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Resumen Q25 y mediana: %s", md_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(cal_csv, poa_csv, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    cal    = cargar_calendario(cal_csv)
    sr_df  = cargar_datos_poa(poa_csv)
    n_dias_poa = int(sr_df["fecha"].nunique())

    df_res = cruzar_ventanas_sr(cal, sr_df)
    logger.info("Mediciones procesadas: %d", len(df_res))

    # Acumulación de masa (Δm = masa_final - masa_inicial por exposición)
    df_acum = calcular_acumulacion_masa(cal)
    if not df_acum.empty:
        merge_cols = ["fecha_llegada", "periodo", "muestra"]
        df_res = df_res.merge(
            df_acum[merge_cols + ["masa_inicial_g", "delta_m_g"]],
            on=merge_cols, how="left", suffixes=("", "_acum")
        )

    if df_res.empty:
        logger.error("No se obtuvieron resultados.")
        return False

    df_resumen = resumir_por_periodo(df_res)

    print("\n=== SR Q25 por período de exposición ===")
    for _, row in df_resumen.iterrows():
        dias = int(row["dias_ref"]) if pd.notna(row["dias_ref"]) else "—"
        print(f"  {row['periodo']:<15}  días={dias:<4}  "
              f"n={int(row['n_mediciones']):<3}  "
              f"SR_Q25={row['sr_q25']:.2f}%  "
              f"pérdida={row['perdida_pct']:.2f} pp")

    # Guardar CSVs
    df_res.drop(columns=["periodo_ord"], errors="ignore").to_csv(
        os.path.join(out_dir, "pv_glasses_por_periodo.csv"), index=False)
    df_resumen.drop(columns=["periodo_ord"], errors="ignore").to_csv(
        os.path.join(out_dir, "pv_glasses_resumen.csv"), index=False)

    # Gráficos
    if MATPLOTLIB_AVAILABLE:
        grafico_sr_vs_dias(
            df_res, os.path.join(out_dir, "pv_glasses_sr_vs_dias.png"))
        grafico_sr_por_periodo(
            df_res, df_resumen,
            os.path.join(out_dir, "pv_glasses_sr_por_periodo.png"))
        grafico_sr_por_periodo_cajas_por_vidrio(
            df_res,
            os.path.join(out_dir, "pv_glasses_sr_por_periodo_por_vidrio.png"))
        grafico_sr_por_vidrio(
            df_res,
            os.path.join(out_dir, "pv_glasses_sr_por_vidrio.png"))
        grafico_curva_acumulacion(
            df_resumen, os.path.join(out_dir, "pv_glasses_curva_acumulacion.png"))
        grafico_curva_acumulacion_por_vidrio(
            df_res, os.path.join(out_dir, "pv_glasses_curva_acumulacion_por_vidrio.png"))
        grafico_datos_detalle_por_vidrio(
            df_res, n_dias_poa,
            os.path.join(out_dir, "pv_glasses_datos_detalle_por_vidrio.png"))
        grafico_q25_y_mediana(
            df_res, df_resumen,
            os.path.join(out_dir, "pv_glasses_q25_y_mediana.png"))
        grafico_masa_por_periodo_por_vidrio(
            df_res, os.path.join(out_dir, "pv_glasses_masa_por_periodo_por_vidrio.png"))
        grafico_masa_vs_dias(
            df_res, os.path.join(out_dir, "pv_glasses_masa_vs_dias.png"))
        grafico_masa_vs_sr(
            df_res, os.path.join(out_dir, "pv_glasses_masa_vs_sr.png"))
        if "delta_m_g" in df_res.columns and df_res["delta_m_g"].notna().any():
            grafico_acumulacion_masa_por_periodo_por_vidrio(
                df_res, os.path.join(out_dir, "pv_glasses_acumulacion_masa_por_periodo_por_vidrio.png"))
            grafico_acumulacion_masa_vs_dias(
                df_res, os.path.join(out_dir, "pv_glasses_acumulacion_masa_vs_dias.png"))
            grafico_acumulacion_masa_vs_sr(
                df_res, os.path.join(out_dir, "pv_glasses_acumulacion_masa_vs_sr.png"))

    generar_reporte(df_res, df_resumen,
                    os.path.join(out_dir, "pv_glasses_report.md"))

    # Tablas con Q25 y mediana por vidrio y resumen por período
    guardar_tabla_sr_por_periodo_por_vidrio(df_res, out_dir)
    guardar_resumen_q25_y_mediana(df_resumen, out_dir)
    # Análisis de masas (masa al llegar y acumulación Δm)
    guardar_tabla_masas_por_periodo_por_vidrio(df_res, out_dir)
    guardar_resumen_masas(df_res, out_dir)
    if "delta_m_g" in df_res.columns and df_res["delta_m_g"].notna().any():
        guardar_tabla_acumulacion_masa_por_periodo_por_vidrio(df_res, out_dir)
        guardar_resumen_acumulacion_masa(df_res, out_dir)
    return True


def main():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cal_csv = os.path.join(root, "data", "calendario",
                           "calendario_muestras_seleccionado.csv")
    poa_csv = os.path.join(root, "data", "pv_glasses",
                           "pv_glasses_poa_500_clear_sky.csv")
    out_dir = os.path.join(root, "analysis", "pv_glasses")
    ok = run(cal_csv, poa_csv, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
