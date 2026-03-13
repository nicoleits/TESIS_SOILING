"""
Gráficos del cálculo de POA (Plane of Array) y de temperatura de módulos.

- POA: lee solys2_poa_500_clear_sky.csv y representa GHI, DHI, DNI y POA
  (POA calculado con pvlib a partir de GHI/DHI/DNI y geometría del panel).
- Temperatura: lee data/temperatura/data_temp.csv y representa las series
  de temperatura de los módulos (referencia y sucio).
- POA + Temperatura: combina POA diario con la temperatura diaria de los módulos
  en un mismo gráfico (eje izquierdo: POA; eje derecho: temperatura).

Salida: analysis/grafico_poa.png, analysis/grafico_temperatura_modulos.png,
        analysis/grafico_poa_con_temperatura.png

Uso (desde si_test con PYTHONPATH=TESIS_SOILING):
  python -m analysis.grafico_poa_temperatura
"""
import os
import sys

import pandas as pd
import numpy as np

try:
    from analysis.config import PERIODO_ANALISIS_INICIO, PERIODO_ANALISIS_FIN
except ImportError:
    PERIODO_ANALISIS_INICIO = "2024-08-03"
    PERIODO_ANALISIS_FIN = "2025-08-04"

try:
    import locale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
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

# Meses en español para el eje X
SPANISH_MONTHS = ["ene", "feb", "mar", "abr", "may", "jun",
                  "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt_month_es(x, pos=None):
    dt = mdates.num2date(x)
    mes_idx = dt.month - 1
    mes = SPANISH_MONTHS[mes_idx] if 0 <= mes_idx < len(SPANISH_MONTHS) else dt.strftime("%b")
    return f"{mes} {dt.year}"


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def grafico_poa(project_root, output_path=None):
    """Gráfico de irradiancia: GHI, DHI, DNI y POA (Plane of Array)."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    csv_path = os.path.join(project_root, "data", "solys2", "solys2_poa_500_clear_sky.csv")
    if not os.path.isfile(csv_path):
        print("No encontrado:", csv_path)
        return None
    df = pd.read_csv(csv_path)
    tc = _get_time_col(df)
    if not tc:
        return None
    df[tc] = pd.to_datetime(df[tc], utc=True)
    df = df.set_index(tc).sort_index()

    columnas = [c for c in ["GHI", "DHI", "DNI", "POA"] if c in df.columns]
    if not columnas:
        return None

    # Resamplear a máximo diario para que el gráfico sea legible
    daily = df[columnas].resample("1D").max()

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = {"GHI": "#D32F2F", "DHI": "#1976D2", "DNI": "#388E3C", "POA": "#7B1FA2"}
    for col in columnas:
        ax.plot(daily.index, daily[col], label=col, color=colors.get(col, "#333"),
                linewidth=1.0, alpha=0.9)
    ax.set_xlabel("Fecha", fontsize=12)
    ax.set_ylabel("Irradiancia (W/m²)", fontsize=12)
    ax.set_title("Cálculo de POA (Plane of Array)\nGHI, DHI, DNI (Solys2) y POA en el plano del panel (pvlib)", fontsize=13, pad=10)
    ax.legend(loc="upper right", fontsize=11)
    ax.tick_params(axis="both", labelsize=11)
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")
    plt.tight_layout()

    if output_path is None:
        output_path = os.path.join(project_root, "analysis", "grafico_poa.png")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print("Gráfico guardado:", output_path)
    return output_path


def grafico_temperatura(project_root, output_path=None):
    """Gráfico de temperatura de módulos (referencia y sucio)."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    csv_path = os.path.join(project_root, "data", "temperatura", "data_temp.csv")
    if not os.path.isfile(csv_path):
        print("No encontrado:", csv_path)
        return None
    df = pd.read_csv(csv_path)
    tc = _get_time_col(df)
    if not tc:
        return None
    df[tc] = pd.to_datetime(df[tc], utc=True)
    df = df.set_index(tc).sort_index()

    # Columnas numéricas de temperatura (excluir índice o no-numéricas)
    temp_cols = [c for c in df.columns if df[c].dtype in (np.float64, np.int64, float, int)]
    if not temp_cols:
        return None

    # Resamplear a media horaria para gráfico legible
    hourly = df[temp_cols].resample("1h").mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = ["#D32F2F", "#1976D2", "#388E3C", "#7B1FA2", "#FF6F00"]
    for i, col in enumerate(temp_cols):
        ax.plot(hourly.index, hourly[col], label=col, color=colors[i % len(colors)],
                linewidth=0.8, alpha=0.9)
    ax.set_xlabel("Fecha", fontsize=12)
    ax.set_ylabel("Temperatura (°C)", fontsize=12)
    ax.set_title("Temperatura de módulos fotovoltaicos\n(1TE416: módulo sucio, 1TE418: módulo referencia)", fontsize=13, pad=10)
    ax.legend(loc="upper right", fontsize=11)
    ax.tick_params(axis="both", labelsize=11)
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")
    plt.tight_layout()

    if output_path is None:
        output_path = os.path.join(project_root, "analysis", "grafico_temperatura_modulos.png")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print("Gráfico guardado:", output_path)
    return output_path


def grafico_poa_con_temperatura(project_root, output_path=None):
    """Gráfico combinado: POA diario y temperatura diaria de módulos."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    poa_csv = os.path.join(project_root, "data", "solys2", "solys2_poa_500_clear_sky.csv")
    temp_csv = os.path.join(project_root, "data", "temperatura", "data_temp.csv")
    if not os.path.isfile(poa_csv) or not os.path.isfile(temp_csv):
        print("No se encontraron archivos de POA o temperatura:")
        if not os.path.isfile(poa_csv):
            print("  - Falta:", poa_csv)
        if not os.path.isfile(temp_csv):
            print("  - Falta:", temp_csv)
        return None

    # POA diario (máximo por día)
    df_poa = pd.read_csv(poa_csv)
    tc_poa = _get_time_col(df_poa)
    if not tc_poa or "POA" not in df_poa.columns:
        return None
    df_poa[tc_poa] = pd.to_datetime(df_poa[tc_poa], utc=True)
    df_poa = df_poa.set_index(tc_poa).sort_index()
    poa_daily = df_poa["POA"].resample("1D").max()

    # Temperatura diaria (media por día)
    df_temp = pd.read_csv(temp_csv)
    tc_temp = _get_time_col(df_temp)
    if not tc_temp:
        return None
    df_temp[tc_temp] = pd.to_datetime(df_temp[tc_temp], utc=True)
    df_temp = df_temp.set_index(tc_temp).sort_index()
    temp_cols = [c for c in df_temp.columns if df_temp[c].dtype in (np.float64, np.int64, float, int)]
    if not temp_cols:
        return None
    temp_daily = df_temp[temp_cols].resample("1D").mean()

    combined = pd.concat([poa_daily.rename("POA"), temp_daily], axis=1).dropna(how="all")
    if combined.empty:
        return None

    # Limitar al mismo periodo de análisis que los gráficos de SR
    try:
        t_ini = pd.Timestamp(PERIODO_ANALISIS_INICIO, tz="UTC")
        t_fin = pd.Timestamp(PERIODO_ANALISIS_FIN, tz="UTC")
        combined = combined[(combined.index >= t_ini) & (combined.index <= t_fin)]
        if combined.empty:
            return None
    except Exception:
        # Si algo falla con las fechas, seguimos sin recorte explícito
        pass

    # Leyendas de temperatura: sucio (1TE416) -> Ts, limpio/referencia (1TE418) -> Tc
    temp_legend_names = {
        "1TE416(C)": "Ts",
        "1TE418(C)": "Tc",
    }

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax2 = ax1.twinx()

    # Eje izquierdo: POA (etiquetas en negro)
    ax1.plot(combined.index, combined["POA"], color="#7B1FA2", linewidth=1.2, alpha=0.9, label="POA (max diario)")
    ax1.set_ylabel("POA (W/m²)", color="k", fontsize=12)
    ax1.tick_params(axis="y", labelcolor="k")

    # Eje derecho: temperaturas (etiquetas en negro)
    colors = ["#D32F2F", "#1976D2", "#388E3C", "#FF6F00"]
    temp_cols_plot = [c for c in combined.columns if c != "POA"]
    for i, col in enumerate(temp_cols_plot):
        lbl = temp_legend_names.get(col, col)
        ax2.plot(combined.index, combined[col], color=colors[i % len(colors)],
                 linewidth=0.9, alpha=0.9, label=lbl)
    ax2.set_ylabel("Temperatura (°C)", color="k", fontsize=12)
    ax2.tick_params(axis="y", labelcolor="k")

    ax1.set_xlabel("Fecha", fontsize=12)
    ax1.set_title(
        "POA y temperatura de módulos (valores diarios)\n"
        "POA máximo diario (Solys2) y temperatura media diaria (1TE416, 1TE418)",
        fontsize=13,
        pad=10,
    )
    ax1.tick_params(axis="x", labelsize=11)
    ax2.tick_params(axis="x", labelsize=11)
    ax1.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax1.grid(True, alpha=0.3)
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=15, ha="right")

    # Leyenda combinada
    lineas_1, labels_1 = ax1.get_legend_handles_labels()
    lineas_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lineas_1 + lineas_2, labels_1 + labels_2, loc="lower left", fontsize=10)

    plt.tight_layout()
    if output_path is None:
        output_path = os.path.join(project_root, "analysis", "grafico_poa_con_temperatura.png")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print("Gráfico guardado:", output_path)
    return output_path


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) > 1:
        project_root = os.path.abspath(sys.argv[1])
    grafico_poa(project_root)
    grafico_temperatura(project_root)
    grafico_poa_con_temperatura(project_root)


if __name__ == "__main__":
    main()
