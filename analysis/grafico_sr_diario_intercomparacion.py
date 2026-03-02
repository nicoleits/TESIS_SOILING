"""
Gráfico de intercomparación: SR diario de todos los módulos + PV Glasses (puntos por evento).

- Todas las series van normalizadas (primer valor = 100%).
- Datos dibujados con puntos o estrellas (markers).
- Líneas + markers: SR diario de Soiling Kit, DustIQ, RefCells, PVStand (Pmax e Isc), IV600 (Pmax e Isc).
- Puntos: PV Glasses = mismos datos que pv_glasses_curva_acumulacion_por_vidrio: por (periodo, muestra) Q25(sr_q25), posicionados en fecha = ref_start + dias_ref (dias_ref como en DIAS_REFERENCIA); sin normalizar.

Salida: analysis/intercomparacion_sr_diario.png

Uso (desde TESIS_SOILING):
  python -m analysis.grafico_sr_diario_intercomparacion
"""
import os
import sys
from datetime import timedelta

import pandas as pd
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Configuración: (etiqueta, ruta relativa a project_root, columna(s) SR).
# Solo una versión por módulo (no incluir _corr para evitar doble normalización, p. ej. IV600).
SERIES_SR = [
    ("RefCells", "analysis/sr/refcells_sr.csv", ["SR"]),
    ("DustIQ", "analysis/sr/dustiq_sr.csv", ["SR"]),
    ("Soiling Kit", "analysis/sr/soilingkit_sr.csv", ["SR"]),
    ("PVStand Pmax", "analysis/sr/pvstand_sr.csv", ["SR_Pmax"]),
    ("PVStand Isc", "analysis/sr/pvstand_sr.csv", ["SR_Isc"]),
    ("SR Pmax IV600", "analysis/sr/iv600_sr.csv", ["SR_Pmax_434"]),
    ("SR Isc IV600", "analysis/sr/iv600_sr.csv", ["SR_Isc_434"]),
]

# PV Glasses: muestra -> (etiqueta, color). Colores vivos, puntos más pequeños.
PVGLASSES_FC = {
    "C": ("PV Glasses FC3 (Q25)", "#00C853"),
    "B": ("PV Glasses FC4 (Q25)", "#00E5FF"),
    "A": ("PV Glasses FC5 (Q25)", "#FFEA00"),
}

# Mismo mapeo periodo -> días de referencia que en pv_glasses_calendario (curva_acumulacion_por_vidrio)
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

# Markers para series diarias: todos los puntos llevan marcador (tamaño reducido)
MARKERS = ["o", "*", "s", "o", "*", "s", "o"]
MARKERSIZE = 1.5
MARKEVERY = 1  # figurita en cada punto


def _get_time_col(df):
    for c in df.columns:
        if "time" in c.lower() or "fecha" in c.lower() or "date" in c.lower():
            return c
    return None


def run(project_root=None, output_path=None):
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if output_path is None:
        output_path = os.path.join(project_root, "analysis", "intercomparacion_sr_diario.png")
    sr_dir = os.path.join(project_root, "analysis", "sr")
    pv_glasses_path = os.path.join(project_root, "analysis", "pv_glasses", "pv_glasses_por_periodo.csv")

    if not MATPLOTLIB_AVAILABLE:
        print("Matplotlib no disponible. No se generó el gráfico.")
        return False

    fig, ax = plt.subplots(figsize=(14, 7))

    # Colores vivos para líneas (rojo, naranja, verde, azul, violeta, magenta, cyan)
    colors_line = [
        "#D32F2F", "#FF6F00", "#388E3C", "#1976D2", "#7B1FA2",
        "#C2185B", "#0097A7",
    ]
    icolor = 0
    ref_start = None  # fecha de inicio para mapear dias_ref -> fecha (PV Glasses)

    # --- Líneas + puntos/estrellas: SR diario por módulo (normalizado: primer valor = 100%) ---
    for label, rel_path, columns in SERIES_SR:
        path = os.path.join(project_root, rel_path)
        if not os.path.isfile(path):
            continue
        df = pd.read_csv(path)
        tc = _get_time_col(df)
        if not tc:
            continue
        df[tc] = pd.to_datetime(df[tc], utc=True)
        if ref_start is None:
            ref_start = df[tc].min().to_pydatetime()
        for col in columns:
            if col not in df.columns:
                continue
            y = pd.to_numeric(df[col], errors="coerce")
            y = y[y >= 80]  # mismo umbral que el pipeline
            if y.empty or y.iloc[0] == 0:
                continue
            # IV600: borrar primer dato y normalizar por el siguiente
            if "IV600" in label:
                y = y.iloc[1:]
                if y.empty or y.iloc[0] == 0:
                    continue
            y_norm = 100.0 * y / y.iloc[0]  # normalizado por primer valor
            color = colors_line[icolor % len(colors_line)]
            marker = MARKERS[icolor % len(MARKERS)]
            icolor += 1
            lbl = label if len(columns) == 1 else f"{label} ({col})"
            ax.plot(
                df.loc[y.index, tc], y_norm, "-", color=color, linewidth=0.35, alpha=0.95,
                marker=marker, markersize=MARKERSIZE, markevery=MARKEVERY, label=lbl,
            )

    # --- Puntos: PV Glasses = mismos datos que pv_glasses_curva_acumulacion_por_vidrio ---
    # Resumen por (periodo, muestra): sr_q25 = Q25(sr_q25), dias_ref; posición en tiempo = ref_start + dias_ref
    if os.path.isfile(pv_glasses_path):
        df_pv = pd.read_csv(pv_glasses_path)
        need_cols = ["sr_q25", "muestra", "periodo"]
        if all(c in df_pv.columns for c in need_cols):
            if ref_start is None:
                if "ventana_fin" in df_pv.columns:
                    ref_start = pd.to_datetime(df_pv["ventana_fin"]).min().to_pydatetime()
                else:
                    ref_start = pd.Timestamp("2024-08-01").to_pydatetime()
            rows = []
            for (periodo, muestra), grupo in df_pv.groupby(["periodo", "muestra"], observed=True):
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
                })
            if rows:
                res = pd.DataFrame(rows)
                res["fecha_pos"] = res["dias_ref"].apply(lambda d: ref_start + timedelta(days=d))
                periodos_ok = [p for p in ORDEN_PERIODO if p in res["periodo"].values]
                res["periodo_ord"] = pd.Categorical(res["periodo"], categories=periodos_ok, ordered=True)
                res = res.sort_values("periodo_ord")
                for muestra, (etiqueta, color) in PVGLASSES_FC.items():
                    sub = res[res["muestra"] == muestra]
                    if sub.empty:
                        continue
                    ax.scatter(
                        sub["fecha_pos"], sub["sr_q25"],
                        c=color, s=14, alpha=0.9, edgecolors="white", linewidths=0.3,
                        label=etiqueta, zorder=5, marker="o",
                    )

    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Soiling Ratio [%]")
    ax.set_title("Intercomparación Soiling Ratio diario")
    ax.set_ylim(70, 110)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print("Gráfico guardado:", output_path)
    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) > 1:
        project_root = os.path.abspath(sys.argv[1])
    run(project_root=project_root)


if __name__ == "__main__":
    main()
