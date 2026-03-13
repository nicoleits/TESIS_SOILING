"""
Genera el gráfico de promedio general de soiling por periodo (A+B+C)/3.
Lee resultados_diferencias_masas.csv y guarda pv_glasses_promedio_soiling_por_periodo.png
"""
import os
import pandas as pd
import numpy as np

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
except ImportError:
    plt = None

# Orden y etiquetas en inglés para el eje X (como en el gráfico de referencia)
PERIODO_ORDEN = [
    "semanal",
    "2 semanas",
    "Mensual",
    "Trimestral",
    "Cuatrimestral",
    "Semestral",
    "1 año",
]
PERIODO_LABEL = {
    "semanal": "Weekly",
    "2 semanas": "2 Weeks",
    "Mensual": "Monthly",
    "Trimestral": "Quarterly",
    "Cuatrimestral": "4-Monthly",
    "Semestral": "Semiannual",
    "1 año": "1 Year",
}


def grafico_promedio_soiling_por_periodo(
    csv_path=None,
    output_path=None,
):
    base = os.path.dirname(os.path.abspath(__file__))
    if csv_path is None:
        csv_path = os.path.join(base, "resultados_diferencias_masas.csv")
    if output_path is None:
        output_path = os.path.join(base, "pv_glasses_promedio_soiling_por_periodo.png")

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

    df = pd.read_csv(csv_path)
    for col in ["Diferencia_Masa_A_mg", "Diferencia_Masa_B_mg", "Diferencia_Masa_C_mg"]:
        if col not in df.columns:
            raise ValueError(f"Falta columna: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Promedio (A+B+C)/3 por fila
    df["promedio_mg"] = (
        df["Diferencia_Masa_A_mg"] + df["Diferencia_Masa_B_mg"] + df["Diferencia_Masa_C_mg"]
    ) / 3.0

    # Media por periodo
    por_periodo = df.groupby("Periodo", as_index=False)["promedio_mg"].mean()
    # Ordenar según PERIODO_ORDEN (solo periodos presentes)
    orden = [p for p in PERIODO_ORDEN if p in por_periodo["Periodo"].values]
    por_periodo = por_periodo.set_index("Periodo").reindex(orden).reset_index()
    por_periodo = por_periodo.dropna(subset=["promedio_mg"])

    if por_periodo.empty:
        raise ValueError("No hay datos por periodo para graficar.")

    labels = [PERIODO_LABEL.get(p, p) for p in por_periodo["Periodo"]]
    valores = por_periodo["promedio_mg"].values

    if plt is None:
        print("Matplotlib no disponible. No se generó el gráfico.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    color_fill = "#B8A9C9"   # light purple
    color_edge = "#5D4E6D"   # darker purple
    bars = ax.bar(labels, valores, color=color_fill, edgecolor=color_edge, linewidth=1.2)

    ax.set_ylabel("General Average Difference (mg)", fontsize=11)
    ax.set_xlabel("Exposure Period", fontsize=11)
    ax.set_title("General Average of Soiling by Period\n(A+B+C)/3", fontsize=12)
    ax.set_ylim(0, max(valores) * 1.15 if valores.size else 14)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(axis="y", color="gray", linestyle="-", linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    for bar, val in zip(bars, valores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.15,
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="normal",
        )

    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Gráfico guardado: {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gráfico promedio soiling (A+B+C)/3 por periodo.")
    parser.add_argument("--csv", type=str, default=None, help="CSV de diferencias de masa.")
    parser.add_argument("--output", "-o", type=str, default=None, help="Ruta del PNG de salida.")
    args = parser.parse_args()
    grafico_promedio_soiling_por_periodo(csv_path=args.csv, output_path=args.output)
