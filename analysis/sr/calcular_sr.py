"""
Sección Análisis: Cálculo de Soiling Ratio (SR).

Lee el CSV de sesión mediodía solar (salida de la sección Data),
calcula SR = 100 × Isc(p) / Isc(e), aplica filtro de corriente si aplica,
y guarda soilingkit_sr.csv y grafico_sr.png en esta sección.

Uso:
  - Desde menú download_data.py: opción "Calcular SR (sección análisis)".
  - Standalone: python -m analysis.sr.calcular_sr [solar_noon_csv] [output_dir]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Umbral de corriente (A): solo días con Isc(e) e Isc(p) >= este valor
UMBRAL_ISC_MIN = 1.0
# SR < este valor se considera outlier y se descarta
UMBRAL_SR_MIN = 80.0

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _get_time_index(df, time_terms=None):
    """Pone el DataFrame indexado por la columna de tiempo."""
    if time_terms is None:
        time_terms = ['time', 'fecha', 'timestamp', 'date']
    time_col = [c for c in df.columns if any(t in c.lower() for t in time_terms)]
    if not time_col:
        return df
    time_col = time_col[0]
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col)
    return df


def calcular_sr(solar_noon_csv_path, output_dir, umbral_isc=UMBRAL_ISC_MIN):
    """
    Calcula Soiling Ratio a partir del CSV de sesión mediodía solar.

    Args:
        solar_noon_csv_path: Ruta al soilingkit_solar_noon.csv (sección Data).
        output_dir: Directorio de salida (ej. analysis/sr/). Se crea si no existe.
        umbral_isc: Mínimo Isc(e) e Isc(p) en A para conservar la fila.

    Returns:
        str: Ruta a soilingkit_sr.csv, o None si error.
    """
    if not os.path.isfile(solar_noon_csv_path):
        logger.error(f"❌ No existe el archivo: {solar_noon_csv_path}")
        return None
    try:
        df = pd.read_csv(solar_noon_csv_path)
    except Exception as e:
        logger.error(f"❌ Error leyendo CSV: {e}")
        return None

    if 'Isc(e)' not in df.columns or 'Isc(p)' not in df.columns:
        logger.error("❌ El CSV debe contener columnas Isc(e) e Isc(p).")
        return None

    # Recalcular SR siempre: SR = 100 * Isc(p) / Isc(e)
    df['SR'] = np.where(
        df['Isc(e)'] > 1e-9,
        100.0 * df['Isc(p)'] / df['Isc(e)'],
        np.nan
    )

    # Filtro de corriente (por si el CSV de data no lo aplicó)
    n_antes = len(df)
    df = df[(df['Isc(e)'] >= umbral_isc) & (df['Isc(p)'] >= umbral_isc)].copy()
    if n_antes > len(df):
        logger.info(f"   Filtro corriente (Isc ≥ {umbral_isc} A): {n_antes} → {len(df)} días.")

    if len(df) == 0:
        logger.warning("⚠️  No quedaron registros tras el filtro de corriente.")
        return None

    # Filtro outliers: SR < UMBRAL_SR_MIN → NaN
    mask_outlier = df['SR'] < UMBRAL_SR_MIN
    if mask_outlier.any():
        df.loc[mask_outlier, 'SR'] = np.nan
        logger.info(f"   Filtro outliers SR < {UMBRAL_SR_MIN}%: {mask_outlier.sum()} filas descartadas.")

    # Orden de columnas: timestamp, dist_solar_noon_min, SR, resto
    base = ['timestamp', 'dist_solar_noon_min', 'SR']
    if 'timestamp' not in df.columns:
        time_col = [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower() or 'fecha' in c.lower()]
        if time_col:
            base = [time_col[0], 'dist_solar_noon_min', 'SR']
    base = [c for c in base if c in df.columns]
    rest = [c for c in df.columns if c not in base]
    df = df[base + rest]

    os.makedirs(output_dir, exist_ok=True)
    out_csv = os.path.join(output_dir, 'soilingkit_sr.csv')
    df.to_csv(out_csv, index=False)
    logger.info(f"✅ SR guardado: {out_csv} ({len(df)} días)")

    if MATPLOTLIB_AVAILABLE:
        _grafico_sr(df, output_dir)

    return out_csv


def _grafico_sr(df, output_dir):
    """Genera grafico_sr.png en output_dir."""
    try:
        time_col = [c for c in df.columns if any(t in c.lower() for t in ['time', 'date', 'fecha', 'timestamp'])]
        if not time_col or 'SR' not in df.columns:
            return
        df_plot = df.copy()
        df_plot[time_col[0]] = pd.to_datetime(df_plot[time_col[0]])
        df_plot = df_plot.set_index(time_col[0])

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df_plot.index, df_plot['SR'], color='#1f77b4', linewidth=0.9, alpha=0.9, marker='*', markersize=4, label='SR')
        ax.axhline(y=100.0, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='SR = 100')
        ax.set_xlabel('Fecha')
        ax.set_ylabel('SR (%) (Isc(p) / Isc(e))')
        ax.set_title('Soiling Ratio (SR) - Sesión mediodía solar')
        ax.legend(loc='best', fontsize=8)
        ax.set_ylim(bottom=0)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        path = os.path.join(output_dir, 'grafico_sr.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico SR guardado: {path}")
    except Exception as e:
        logger.error(f"❌ Error al generar gráfico SR: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')


def run_sr(solar_noon_csv_path=None, output_dir=None, project_root=None):
    """
    Punto de entrada: calcula SR y escribe en la sección análisis/sr.

    Si no se pasan rutas, usa por defecto:
      - solar_noon_csv_path: <project_root>/data/soilingkit/soilingkit_solar_noon.csv
      - output_dir: <project_root>/analysis/sr/

    Returns:
        str: Ruta a soilingkit_sr.csv, o None.
    """
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if solar_noon_csv_path is None:
        solar_noon_csv_path = os.path.join(project_root, 'data', 'soilingkit', 'soilingkit_solar_noon.csv')
    if output_dir is None:
        output_dir = os.path.join(project_root, 'analysis', 'sr')

    logger.info("📐 Sección Análisis SR: calculando Soiling Ratio...")
    return calcular_sr(solar_noon_csv_path, output_dir)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    result = run_sr(solar_noon_csv_path=csv_path, output_dir=out_dir)
    sys.exit(0 if result else 1)
