"""
Exporta un CSV largo: SR diario (sin normalizar) + u_c(SR) y U(SR) en pp por instrumento.

Usa la misma configuración de rutas/columnas que agregacion_semanal y U_pp_por_metodologia.

Uso (desde la raíz TESIS_SOILING):
  python -m analysis.uncertainty.export_sr_diario_incertidumbre [SR_DIR] [OUT_CSV]

Por defecto: analysis/sr → analysis/stats/sr_diario_incertidumbre.csv
"""

from __future__ import annotations

import logging
import os
import sys

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from analysis.stats import agregacion_semanal as agg
except ImportError:
    agg = None  # type: ignore

try:
    from analysis.uncertainty.sr_metodologias import U_pp_por_metodologia
except ImportError:
    U_pp_por_metodologia = None  # type: ignore

from analysis.uncertainty import constants


def _rows_for_instrument(nombre: str, ruta: str, col_sr: str, fecha_max) -> pd.DataFrame | None:
    if U_pp_por_metodologia is None or agg is None:
        logger.error("No se pudieron importar agregacion_semanal o U_pp_por_metodologia.")
        return None
    serie = agg.cargar_sr_diario(
        ruta, col_sr, fecha_min=None, fecha_max=fecha_max
    )
    if serie is None or serie.empty:
        return None
    sr_vals = pd.to_numeric(serie.values, errors="coerce")
    U_pp = U_pp_por_metodologia(nombre, sr_vals)
    k = float(constants.K_COVERAGE)
    u_c_pp = np.where(np.isfinite(U_pp), U_pp / k, np.nan)
    fechas = pd.to_datetime(pd.Series(serie.index.astype(str))).dt.date.astype(str)
    return pd.DataFrame(
        {
            "fecha": fechas,
            "instrumento": nombre,
            "sr_pct": sr_vals,
            "u_c_SR_pp": u_c_pp,
            "U_SR_pp": U_pp,
        }
    )


def run(sr_dir: str | None = None, out_csv: str | None = None) -> str | None:
    """
    Genera CSV largo con una fila por (fecha, instrumento).

    Returns
    -------
    str | None
        Ruta del CSV escrito, o None si no hubo datos.
    """
    if agg is None or U_pp_por_metodologia is None:
        raise RuntimeError("Faltan dependencias (analysis.stats.agregacion_semanal, sr_metodologias).")

    if sr_dir is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sr_dir = os.path.join(base, "analysis", "sr")
    sr_dir = os.path.abspath(sr_dir)

    if out_csv is None:
        out_csv = os.path.join(os.path.dirname(sr_dir), "stats", "sr_diario_incertidumbre.csv")
    out_csv = os.path.abspath(out_csv)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    config = agg._build_config(sr_dir)
    # SR diario PV Glasses (misma propagación que en agregación semanal para esa metodología)
    config = config + [
        ("PV Glasses", os.path.join(sr_dir, "pv_glasses_sr.csv"), "SR", None),
    ]

    partes = []
    for nombre, ruta, col_sr, fecha_max in config:
        df_i = _rows_for_instrument(nombre, ruta, col_sr, fecha_max)
        if df_i is not None:
            partes.append(df_i)
            logger.info("%s: %d días", nombre, len(df_i))
        else:
            logger.warning("%s: sin datos (%s)", nombre, ruta)

    if not partes:
        logger.error("No se generó ninguna fila; revisa SR_DIR=%s", sr_dir)
        return None

    out = pd.concat(partes, ignore_index=True)
    out = out.sort_values(["instrumento", "fecha"])
    out.to_csv(out_csv, index=False)
    logger.info("Escrito: %s (%d filas)", out_csv, len(out))
    return out_csv


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    sr_dir = argv[0] if len(argv) > 0 else None
    out_csv = argv[1] if len(argv) > 1 else None
    path = run(sr_dir=sr_dir, out_csv=out_csv)
    return 0 if path else 1


if __name__ == "__main__":
    raise SystemExit(main())
