import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SR_COLUMNS_BY_FILE = {
    # Cada CSV tiene una o más columnas SR relevantes para filtrado.
    "soilingkit_sr.csv": ["SR"],
    "dustiq_sr.csv": ["SR"],
    "refcells_sr.csv": ["SR"],
    "pv_glasses_sr.csv": ["SR"],  # Nota: PV Glasses semanal en agregación usa pv_glasses_por_periodo.csv
    "pvstand_sr.csv": ["SR_Pmax", "SR_Isc"],
    "pvstand_sr_corr.csv": ["SR_Pmax_corr", "SR_Isc_corr"],
    "iv600_sr.csv": ["SR_Pmax_434", "SR_Isc_434"],
    "iv600_sr_corr.csv": ["SR_Pmax_corr_434", "SR_Isc_corr_434"],
}


def run_module(python_exe: str, module: str, args: list[str], env: dict):
    cmd = [python_exe, "-m", module] + args
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def safe_rmtree(path: Path):
    if path.exists():
        shutil.rmtree(path)


def _apply_iqr_filter(values: pd.Series):
    """
    Filtro de outliers por vallas de Tukey:
      [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
    Excluye (pone NaN) los valores fuera del rango.

    Devuelve:
      - filtered (misma forma que input)
      - Q1, Q3, IQR
      - n_outliers_excluidos
    """
    vals = pd.to_numeric(values, errors="coerce")
    valid = vals[np.isfinite(vals)]
    if valid.empty:
        return vals, np.nan, np.nan, np.nan, 0

    q1 = float(valid.quantile(0.25))
    q3 = float(valid.quantile(0.75))
    iqr = q3 - q1

    # Evitar degeneración cuando IQR=0: las vallas colapsan.
    if not np.isfinite(iqr) or abs(iqr) < 1e-12:
        return vals, q1, q3, iqr, 0

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    out = vals.copy()
    mask_out = (out < lower) | (out > upper)
    n_removed = int(mask_out.fillna(False).sum())
    out.loc[mask_out] = np.nan
    return out, q1, q3, iqr, n_removed


def build_sr_outliers_dataset(src_sr_dir: Path, dst_sr_dir: Path, out_stats_dir: Path):
    """
    Aplica filtro IQR por columna en cada CSV de SR y escribe en dst_sr_dir.
    Además genera un resumen CSV con Q1/Q3/IQR y número de puntos excluidos.
    """
    dst_sr_dir.mkdir(parents=True, exist_ok=True)
    out_stats_dir.mkdir(parents=True, exist_ok=True)
    report_rows = []

    for csv_name, cols in SR_COLUMNS_BY_FILE.items():
        src_path = src_sr_dir / csv_name
        if not src_path.is_file():
            print("[WARN] No existe:", src_path)
            continue
        df = pd.read_csv(src_path)

        for col in cols:
            if col not in df.columns:
                continue
            original = pd.to_numeric(df[col], errors="coerce")
            filtered, q1, q3, iqr, n_removed = _apply_iqr_filter(original)
            df[col] = filtered
            report_rows.append(
                {
                    "archivo": csv_name,
                    "columna": col,
                    "Q1": round(q1, 6) if np.isfinite(q1) else "",
                    "Q3": round(q3, 6) if np.isfinite(q3) else "",
                    "IQR": round(iqr, 6) if np.isfinite(iqr) else "",
                    "limite_inferior": round(q1 - 1.5 * iqr, 6) if np.isfinite(iqr) else "",
                    "limite_superior": round(q3 + 1.5 * iqr, 6) if np.isfinite(iqr) else "",
                    "n_outliers_excluidos": int(n_removed),
                    "n_datos_columna": int(original.notna().sum()),
                }
            )

        dst_path = dst_sr_dir / csv_name
        df.to_csv(dst_path, index=False)
        print("[WRITE]", dst_path)

    report = pd.DataFrame(report_rows)
    report_path = out_stats_dir / "outliers_iqr_resumen.csv"
    report.to_csv(report_path, index=False)
    print("[WRITE]", report_path)
    return report_path


def apply_iqr_filter_to_pv_glasses_por_periodo(pv_glasses_dir: Path, out_stats_dir: Path):
    """
    Aplica el mismo criterio IQR (Q1-1.5·IQR a Q3+1.5·IQR) a la columna `sr_q25`
    de `pv_glasses_por_periodo.csv`.
    """
    path = pv_glasses_dir / "pv_glasses_por_periodo.csv"
    if not path.is_file():
        print("[WARN] pv_glasses_por_periodo.csv no existe en:", path)
        return None
    df = pd.read_csv(path)
    if "sr_q25" not in df.columns:
        print("[WARN] Falta columna sr_q25 en:", path)
        return None

    filtered, q1, q3, iqr, n_removed = _apply_iqr_filter(df["sr_q25"])
    df["sr_q25"] = filtered

    out_path = path  # sobreescribe
    df.to_csv(out_path, index=False)
    print("[WRITE]", out_path)

    report = pd.DataFrame(
        [
            {
                "archivo": "pv_glasses_por_periodo.csv",
                "columna": "sr_q25",
                "Q1": round(q1, 6) if np.isfinite(q1) else "",
                "Q3": round(q3, 6) if np.isfinite(q3) else "",
                "IQR": round(iqr, 6) if np.isfinite(iqr) else "",
                "limite_inferior": round(q1 - 1.5 * iqr, 6) if np.isfinite(iqr) else "",
                "limite_superior": round(q3 + 1.5 * iqr, 6) if np.isfinite(iqr) else "",
                "n_outliers_excluidos": int(n_removed),
                "n_datos_columna": int(pd.to_numeric(df["sr_q25"], errors="coerce").notna().sum()),
            }
        ]
    )
    report_path = out_stats_dir / "outliers_iqr_resumen_pv_glasses_por_periodo.csv"
    report.to_csv(report_path, index=False)
    print("[WRITE]", report_path)
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Genera TESIS_OUTLIERS con filtro IQR en SR.")
    parser.add_argument("--force", action="store_true", help="Borra TESIS_OUTLIERS antes de regenerar.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    tesis_soiling_root = repo_root / "TESIS_SOILING"
    out_root = repo_root / "TESIS_OUTLIERS"

    out_sr_dir = out_root / "analysis" / "sr"
    out_stats_dir = out_root / "analysis" / "stats"
    out_tend_dir = out_root / "analysis" / "tendencias"
    out_corr_dir = out_root / "analysis" / "correlacion"
    out_cc_dir = out_root / "analysis" / "concordancia"
    out_anova_dir = out_root / "analysis" / "anova"
    out_bias_dir = out_root / "analysis" / "sesgo"
    out_inter_data_dir = out_root / "analysis" / "intercomparacion_data_outliers"

    src_sr_dir = tesis_soiling_root / "analysis" / "sr"
    src_pv_glasses_dir = tesis_soiling_root / "analysis" / "pv_glasses"

    if args.force:
        safe_rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "analysis").mkdir(parents=True, exist_ok=True)

    venv_python = repo_root / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tesis_soiling_root)

    # 1) Escribir SR filtrado (sin normalizar)
    build_sr_outliers_dataset(src_sr_dir, out_sr_dir, out_stats_dir)

    # 2) Copiar PV Glasses (para pv_glasses_por_periodo.csv y gráficos/CSVs base)
    out_pv_glasses_dir = out_root / "analysis" / "pv_glasses"
    if out_pv_glasses_dir.exists():
        shutil.rmtree(out_pv_glasses_dir)
    shutil.copytree(src_pv_glasses_dir, out_pv_glasses_dir)
    print("[COPY]", out_pv_glasses_dir)

    # 2b) Regenerar PV Glasses (opcional, pero útil para asegurar consistencia)
    try:
        run_module(
            python_exe,
            "analysis.pv_glasses.pv_glasses_calendario",
            [str(out_pv_glasses_dir)],
            env=env,
        )
    except subprocess.CalledProcessError as e:
        print("[WARN] pv_glasses_calendario falló; se conservan resultados copiados (y se filtrará sr_q25 igual):", e)

    # 2c) Aplicar IQR a sr_q25 de PV Glasses para que agregación/todos los análisis usen el mismo outlier-filter
    apply_iqr_filter_to_pv_glasses_por_periodo(out_pv_glasses_dir, out_stats_dir)

    # 3) Misma secuencia que TESIS_NO_NORM (agregación + dispersión + análisis)
    run_module(
        python_exe,
        "analysis.stats.agregacion_semanal",
        [str(out_sr_dir), str(out_stats_dir), "--solo-sin-normalizar"],
        env=env,
    )
    run_module(
        python_exe,
        "analysis.stats.dispersion_diaria",
        [str(out_sr_dir), str(out_stats_dir)],
        env=env,
    )

    wide_csv = out_stats_dir / "sr_semanal_q25.csv"
    long_csv = out_stats_dir / "sr_semanal_q25_largo.csv"

    run_module(
        python_exe,
        "analysis.tendencias.analisis_tendencias",
        [str(wide_csv), str(out_tend_dir), str(out_sr_dir)],
        env=env,
    )
    run_module(
        python_exe,
        "analysis.correlacion.correlacion_cruzada",
        [str(wide_csv), str(out_corr_dir)],
        env=env,
    )
    run_module(
        python_exe,
        "analysis.concordancia.concordancia_intermetodologica",
        [str(wide_csv), str(out_cc_dir)],
        env=env,
    )
    run_module(
        python_exe,
        "analysis.anova.anova_sr",
        [str(long_csv), str(out_anova_dir)],
        env=env,
    )
    run_module(
        python_exe,
        "analysis.sesgo.sesgo_referencia",
        [str(wide_csv), str(out_bias_dir)],
        env=env,
    )

    # 4) Intercomparación SR diario (sin normalizar)
    sys.path.insert(0, str(tesis_soiling_root))
    from analysis import grafico_sr_diario_intercomparacion as mod  # type: ignore

    mod.run(
        project_root=str(out_root),
        output_path=str(out_root / "analysis" / "intercomparacion_sr_diario_sin_normalizar.png"),
        use_corr_series=False,
        normalize_series=False,
        export_data_dir=str(out_inter_data_dir),
    )
    mod.run(
        project_root=str(out_root),
        output_path=str(out_root / "analysis" / "intercomparacion_sr_diario_sin_normalizar_corr.png"),
        use_corr_series=True,
        normalize_series=False,
        export_data_dir=str(out_inter_data_dir),
    )

    print("\n[OK] TESIS_OUTLIERS generado en:", out_root)


if __name__ == "__main__":
    main()

