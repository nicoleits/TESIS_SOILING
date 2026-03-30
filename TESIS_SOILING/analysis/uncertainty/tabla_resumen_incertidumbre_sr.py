"""
Tabla resumen comparativa: incertidumbre combinada y expandida de SR por metodología.

Columnas: Metodología, Salida usada para SR, n válido, u_c(SR) mediana [pp],
P25–P75 u_c(SR) [pp], U(SR) mediana [pp], máximo U(SR) [pp], fuente dominante.
Todas las incertidumbres en puntos porcentuales (pp) para comparar con variabilidad en pp.
"""

import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)


def _fila_resumen(metodologia, salida, res):
    """Construye una fila de tabla con datos reales del dict resumen."""
    n = res["n_valido"]
    if n == 0:
        return {
            "Metodología": metodologia,
            "Salida usada para SR": salida,
            "n válido": "—",
            "u_c(SR) mediana [pp]": "—",
            "P25–P75 de u_c(SR) [pp]": "—",
            "U(SR) mediana [pp]": "—",
            "máximo de U(SR) [pp]": "—",
            "fuente dominante del presupuesto": res["fuente_dominante"],
        }
    return {
        "Metodología": metodologia,
        "Salida usada para SR": salida,
        "n válido": n,
        "u_c(SR) mediana [pp]": res["u_c_mediana_pp"],
        "P25–P75 de u_c(SR) [pp]": f"{res['u_c_P25_pp']:.3f}–{res['u_c_P75_pp']:.3f}",
        "U(SR) mediana [pp]": res["U_mediana_pp"],
        "máximo de U(SR) [pp]": res["U_max_pp"],
        "fuente dominante del presupuesto": res["fuente_dominante"],
    }


def _fila_pendiente(metodologia, salida):
    """Fila con "—" y Pendiente cuando no hay datos."""
    return {
        "Metodología": metodologia,
        "Salida usada para SR": salida,
        "n válido": "—",
        "u_c(SR) mediana [pp]": "—",
        "P25–P75 de u_c(SR) [pp]": "—",
        "U(SR) mediana [pp]": "—",
        "máximo de U(SR) [pp]": "—",
        "fuente dominante del presupuesto": "Pendiente",
    }


def _ruta_pv_glasses_por_periodo(base_dir):
    """Ruta típica al CSV de PV Glasses por período."""
    return os.path.join(base_dir, "analysis", "pv_glasses", "pv_glasses_por_periodo.csv")


def _ruta_sr(base_dir, nombre):
    """Ruta al CSV de SR en analysis/sr (ej. refcells_sr.csv)."""
    return os.path.join(base_dir, "analysis", "sr", nombre)


def build_tabla_resumen_incertidumbre_sr(
    base_dir=None,
    out_dir=None,
    *,
    out_stem="resumen_incertidumbre_sr_por_metodologia",
    md_title=None,
    md_note=None,
):
    """
    Construye la tabla resumen por metodología. Por ahora solo PV Glasses tiene datos;
    el resto se rellena con "—" o "Pendiente".

    Parámetros
    ----------
    base_dir : str, opcional
        Raíz del proyecto (TESIS_SOILING). Si None, se usa el directorio del script.
    out_dir : str, opcional
        Carpeta de salida (p. ej. uncertainty/results). Si None, se usa results/ junto al módulo.
    out_stem : str
        Nombre base (sin extensión) para `out_stem.csv` y `out_stem.md`.
    md_title : str, opcional
        Título H1 del Markdown. Por defecto: resumen genérico.
    md_note : str, opcional
        Párrafo aclaratorio debajo del título (p. ej. contexto sin normalizar).

    Returns
    -------
    pandas.DataFrame
        Tabla con las columnas indicadas.
    """
    from .sr_pv_glasses import resumen_incertidumbre_sr_pv_glasses, COL_SR_PCT
    from . import sr_metodologias

    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(__file__), "results")

    filas = []

    # --- PV Glasses ---
    path_pg = _ruta_pv_glasses_por_periodo(base_dir)
    if os.path.isfile(path_pg):
        df_pg = pd.read_csv(path_pg)
        res = resumen_incertidumbre_sr_pv_glasses(df_pg, col_sr=COL_SR_PCT)
        filas.append(_fila_resumen("PV Glasses", "pv_glasses_por_periodo.csv (sr_q25)", res))
    else:
        filas.append(_fila_pendiente("PV Glasses", "pv_glasses_por_periodo.csv"))
        filas[-1]["fuente dominante del presupuesto"] = "escala (fotoceldas 2,5 % k=2)"

    # --- RefCells ---
    path_refcells = _ruta_sr(base_dir, "refcells_sr.csv")
    if os.path.isfile(path_refcells):
        df_rc = pd.read_csv(path_refcells)
        res = sr_metodologias.resumen_incertidumbre_sr_refcells(df_rc, col_sr="SR")
        filas.append(_fila_resumen("RefCells", "refcells_sr.csv (SR)", res))
    else:
        filas.append(_fila_pendiente("RefCells", "SR desde celdas de referencia"))

    # --- DustIQ ---
    path_dustiq = _ruta_sr(base_dir, "dustiq_sr.csv")
    if os.path.isfile(path_dustiq):
        df_dq = pd.read_csv(path_dustiq)
        res = sr_metodologias.resumen_incertidumbre_sr_dustiq(df_dq, col_sr="SR")
        filas.append(_fila_resumen("DustIQ", "dustiq_sr.csv (SR)", res))
    else:
        filas.append(_fila_pendiente("DustIQ", "SR directo del sensor"))

    # --- Soiling Kit ---
    path_sk = _ruta_sr(base_dir, "soilingkit_sr.csv")
    if os.path.isfile(path_sk):
        df_sk = pd.read_csv(path_sk)
        res = sr_metodologias.resumen_incertidumbre_sr_soilingkit(df_sk, col_sr="SR")
        filas.append(_fila_resumen("Soiling Kit", "soilingkit_sr.csv (SR)", res))
    else:
        filas.append(_fila_pendiente("Soiling Kit", "SR = 100×Isc(p)/Isc(e)"))

    # --- PVStand (SR con corrección T; incertidumbre incluye escala + PT100) ---
    path_pvs = _ruta_sr(base_dir, "pvstand_sr_corr.csv")
    if os.path.isfile(path_pvs):
        df_pvs = pd.read_csv(path_pvs)
        res_pmax = sr_metodologias.resumen_incertidumbre_sr_pvstand(df_pvs, col_sr="SR_Pmax_corr")
        filas.append(_fila_resumen("PVStand", "pvstand_sr_corr.csv (SR_Pmax_corr)", res_pmax))
        res_isc = sr_metodologias.resumen_incertidumbre_sr_pvstand_isc(df_pvs, col_sr="SR_Isc_corr")
        filas.append(_fila_resumen("PVStand Isc", "pvstand_sr_corr.csv (SR_Isc_corr)", res_isc))
    else:
        filas.append(_fila_pendiente("PVStand", "SR_Pmax / SR_Isc con corrección T"))

    # --- IV600 (SR con corrección T; Pmax e Isc por separado) ---
    path_iv = _ruta_sr(base_dir, "iv600_sr_corr.csv")
    if os.path.isfile(path_iv):
        df_iv = pd.read_csv(path_iv)
        res_pmax = sr_metodologias.resumen_incertidumbre_sr_iv600_pmax(df_iv, col_sr="SR_Pmax_corr_434")
        filas.append(_fila_resumen("IV600 Pmax", "iv600_sr_corr.csv (SR_Pmax_corr_434)", res_pmax))
        res_isc = sr_metodologias.resumen_incertidumbre_sr_iv600(df_iv, col_sr="SR_Isc_corr_434")
        filas.append(_fila_resumen("IV600 Isc", "iv600_sr_corr.csv (SR_Isc_corr_434)", res_isc))
    else:
        filas.append(_fila_pendiente("IV600 Pmax", "iv600_sr_corr.csv (SR_Pmax_corr_434)"))
        filas.append(_fila_pendiente("IV600 Isc", "iv600_sr_corr.csv (SR_Isc_corr_434)"))

    tabla = pd.DataFrame(filas)
    os.makedirs(out_dir, exist_ok=True)
    if md_title is None:
        md_title = "Resumen comparativo: incertidumbre de SR por metodología"

    csv_path = os.path.join(out_dir, f"{out_stem}.csv")
    tabla.to_csv(csv_path, index=False)
    logger.info("Tabla resumen incertidumbre SR: %s", csv_path)

    # Markdown
    md_path = os.path.join(out_dir, f"{out_stem}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {md_title}\n\n")
        if md_note:
            f.write(md_note.strip() + "\n\n")
        f.write("Incertidumbre combinada u_c(SR) e expandida U(SR) en **puntos porcentuales (pp)** ")
        f.write("para comparar con métricas de variabilidad en pp.\n\n")
        f.write("| Metodología | Salida usada para SR | n válido | u_c(SR) mediana [pp] | ")
        f.write("P25–P75 de u_c(SR) [pp] | U(SR) mediana [pp] | máximo de U(SR) [pp] | fuente dominante del presupuesto |\n")
        f.write("|-------------|----------------------|----------|----------------------|-------------------------------|-------------------|------------------------|------------------------------------|\n")
        for _, r in tabla.iterrows():
            f.write(f"| {r['Metodología']} | {r['Salida usada para SR']} | {r['n válido']} | ")
            f.write(f"{r['u_c(SR) mediana [pp]']} | {r['P25–P75 de u_c(SR) [pp]']} | ")
            f.write(f"{r['U(SR) mediana [pp]']} | {r['máximo de U(SR) [pp]']} | {r['fuente dominante del presupuesto']} |\n")
        f.write("\n")
    logger.info("Markdown: %s", md_path)

    return tabla


def build_tabla_resumen_incertidumbre_sr_sin_normalizar(base_dir=None, out_dir=None):
    """
    Misma tabla que `build_tabla_resumen_incertidumbre_sr`: la propagación ya usa SR en % absoluto
    desde `analysis/sr/*.csv` (y PV Glasses por período). Escribe archivos con sufijo
    `_sin_normalizar` y un párrafo explícito para memoria / carpeta TESIS_NO_NORM.

    Nota: no confundir con el eje **normalizado** de los gráficos semanales (t₀=100 %);
    aquí no se aplica ese reescalado a los valores de entrada del presupuesto.
    """
    note = (
        "**Contexto sin normalizar (eje temporal de SR):** los SR de entrada son **porcentaje "
        "absoluto** según cada metodología (CSV en `analysis/sr/` y `sr_q25` por período en "
        "PV Glasses). **No** se reescalan las series al 100 % de la primera semana. Las "
        "incertidumbres u_c y U se obtienen propagando sobre esos valores (GUM, k=2 para U)."
    )
    return build_tabla_resumen_incertidumbre_sr(
        base_dir=base_dir,
        out_dir=out_dir,
        out_stem="resumen_incertidumbre_sr_por_metodologia_sin_normalizar",
        md_title="Resumen comparativo: incertidumbre de SR por metodología (sin normalizar)",
        md_note=note,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Directorio del script: .../TESIS_SOILING/analysis/uncertainty → subir 2 niveles = TESIS_SOILING
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(script_dir, "..", "..")
    base = os.path.normpath(os.path.abspath(base))
    if os.path.basename(base) != "TESIS_SOILING" and os.path.isdir(os.path.join(base, "TESIS_SOILING")):
        base = os.path.join(base, "TESIS_SOILING")
    out_dir = os.path.join(script_dir, "results")
    build_tabla_resumen_incertidumbre_sr(base_dir=base, out_dir=out_dir)
    build_tabla_resumen_incertidumbre_sr_sin_normalizar(base_dir=base, out_dir=out_dir)
    logger.info("También: resumen_incertidumbre_sr_por_metodologia_sin_normalizar.csv/.md")
