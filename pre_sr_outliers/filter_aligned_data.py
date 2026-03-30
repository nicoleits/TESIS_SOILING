"""
Copia TESIS_SOILING/data → data_pre_sr_iqr y aplica IQR (Tukey) a columnas
usadas como entrada del cálculo de SR, antes de ejecutar calcular_sr_modulos.

No modifica el árbol data/ original.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from pre_sr_outliers.iqr_utils import mask_groupby_columns, mask_per_column, mask_union_nan

REPORT_NAME = "_pre_sr_iqr_report.json"


def mirror_data_dir(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _soilingkit(path: Path, rows: list) -> None:
    df = pd.read_csv(path)
    n = mask_union_nan(df, ["Isc(e)", "Isc(p)"])
    rows.append({"archivo": path.name, "estrategia": "union_Isc_e_Isc_p", "celdas_nan": n})
    df.to_csv(path, index=False)


def _dustiq(path: Path, rows: list) -> None:
    df = pd.read_csv(path)
    c = mask_per_column(df, ["SR_C11_Avg"])
    n = sum(c.values())
    rows.append({"archivo": path.name, "estrategia": "SR_C11_Avg_por_columna", "celdas_nan": n})
    df.to_csv(path, index=False)


def _refcells(path: Path, rows: list) -> None:
    df = pd.read_csv(path)
    cols = [c for c in df.columns if c.startswith("1RC411") or c.startswith("1RC412")]
    n = mask_union_nan(df, cols)
    rows.append({"archivo": path.name, "estrategia": "union_1RC411_1RC412", "celdas_nan": n})
    df.to_csv(path, index=False)


def _pv_glasses(path: Path, rows: list) -> None:
    df = pd.read_csv(path)
    cols = ["REF", "R_FC3_Avg", "R_FC4_Avg", "R_FC5_Avg"]
    c = mask_per_column(df, cols)
    rows.append(
        {
            "archivo": path.name,
            "estrategia": "IQR_independiente_REF_y_R_FC3_4_5",
            "detalle": c,
            "celdas_nan": sum(c.values()),
        }
    )
    df.to_csv(path, index=False)


def _pvstand(path: Path, rows: list) -> None:
    df = pd.read_csv(path)
    det = mask_groupby_columns(df, "module", ["pmax", "imax"])
    n = sum(vv for v in det.values() for vv in v.values())
    rows.append({"archivo": path.name, "estrategia": "por_module_pmax_imax", "detalle": det, "celdas_nan": n})
    df.to_csv(path, index=False)


def _iv600(path: Path, rows: list) -> None:
    df = pd.read_csv(path)
    det = mask_groupby_columns(df, "module", ["pmp", "isc"])
    n = sum(vv for v in det.values() for vv in v.values())
    rows.append({"archivo": path.name, "estrategia": "por_module_pmp_isc", "detalle": det, "celdas_nan": n})
    df.to_csv(path, index=False)


def apply_pre_sr_iqr(data_root: Path) -> list[dict]:
    """
    Aplica filtros in-place sobre CSVs ya copiados bajo data_root.
    data_root suele ser .../TESIS_SOILING/data_pre_sr_iqr
    """
    data_root = data_root.resolve()
    report: list[dict] = []

    jobs = [
        (data_root / "soilingkit" / "soilingkit_aligned_solar_noon.csv", _soilingkit),
        (data_root / "dustiq" / "dustiq_aligned_solar_noon.csv", _dustiq),
        (data_root / "refcells" / "refcells_aligned_solar_noon.csv", _refcells),
        (data_root / "pv_glasses" / "pv_glasses_aligned_solar_noon.csv", _pv_glasses),
        (data_root / "pvstand" / "pvstand_aligned_solar_noon.csv", _pvstand),
        (data_root / "iv600" / "iv600_aligned_solar_noon.csv", _iv600),
    ]

    for csv_path, fn in jobs:
        if not csv_path.is_file():
            report.append({"archivo": str(csv_path.relative_to(data_root)), "omitido": "no_existe"})
            continue
        fn(csv_path, report)

    rep_path = data_root / REPORT_NAME
    rep_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def build_filtered_data_tree(soiling_root: Path, dst_data: Path) -> list[dict]:
    src = soiling_root / "data"
    if not src.is_dir():
        raise FileNotFoundError(f"No existe carpeta data: {src}")
    mirror_data_dir(src, dst_data)
    return apply_pre_sr_iqr(dst_data)


def main():
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Copia data/ y aplica IQR pre-SR.")
    p.add_argument("soiling_root", type=Path, help="Raíz TESIS_SOILING")
    p.add_argument("dst_data", type=Path, help="Salida, ej. TESIS_SOILING/data_pre_sr_iqr")
    args = p.parse_args()
    r = build_filtered_data_tree(args.soiling_root.resolve(), args.dst_data.resolve())
    print(json.dumps(r, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
