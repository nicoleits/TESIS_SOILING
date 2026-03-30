"""
Pipeline: outliers IQR sobre datos alineados (pre cálculo de SR) sin modificar
los módulos existentes en TESIS_SOILING.

1) Copia TESIS_SOILING/data → TESIS_SOILING/data_pre_sr_iqr
2) Aplica IQR a columnas crudas (Isc, irradiancias, pmax/imax por módulo, etc.)
3) Ejecuta los mismos scripts SR que ya tienes, con rutas alternativas:
   - salida: TESIS_SOILING/analysis/sr_pre_sr_iqr/
4) Opcional (--full): genera TESIS_PRE_SR_IQR/ con agregación, dispersión,
   tendencias, correlación, concordancia, ANOVA, sesgo, intercomparación
   y resumen de incertidumbre SR (analysis/uncertainty/results/, misma base
   de SR y pv_glasses que el resto de la carpeta).

Uso (desde si_test, con venv activo o .venv/bin/python):

  .venv/bin/python run_tesis_pre_sr_iqr.py --solo-sr
  .venv/bin/python run_tesis_pre_sr_iqr.py --full --force
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_module(python_exe: str, module: str, args: list[str], env: dict, cwd: Path | None = None):
    cmd = [python_exe, "-m", module] + args
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env, cwd=str(cwd) if cwd else None)


def safe_rmtree(path: Path):
    if path.exists():
        shutil.rmtree(path)


def prune_sr_norm_outputs(stats_dir: Path):
    patterns = [
        str(stats_dir / "sr_semanal_norm*.csv"),
        str(stats_dir / "sr_semanal_norm*.png"),
    ]
    for pat in patterns:
        for f in glob.glob(pat):
            try:
                os.remove(f)
                print("[PRUNE]", f)
            except FileNotFoundError:
                pass


def main():
    parser = argparse.ArgumentParser(description="SR con IQR pre-cálculo sobre datos alineados.")
    parser.add_argument("--force", action="store_true", help="Borra data_pre_sr_iqr, sr_pre_sr_iqr y TESIS_PRE_SR_IQR.")
    parser.add_argument("--solo-sr", action="store_true", help="Solo copia+filtro datos y regenera CSV SR (sin carpeta tesis).")
    parser.add_argument("--full", action="store_true", help="Además genera TESIS_PRE_SR_IQR (como tesis sin normalizar).")
    parser.add_argument(
        "--copiar-pv-glasses",
        action="store_true",
        default=True,
        help="En --full, copia analysis/pv_glasses y ejecuta calendario.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(repo_root))
    from pre_sr_outliers.filter_aligned_data import build_filtered_data_tree

    tesis_soiling = repo_root / "TESIS_SOILING"
    data_pre = tesis_soiling / "data_pre_sr_iqr"
    sr_pre = tesis_soiling / "analysis" / "sr_pre_sr_iqr"
    out_tesis = repo_root / "TESIS_PRE_SR_IQR"

    venv_python = repo_root / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tesis_soiling)

    if args.force:
        safe_rmtree(data_pre)
        safe_rmtree(sr_pre)
        safe_rmtree(out_tesis)

    print("[1/3] Copia data/ y filtro IQR pre-SR →", data_pre)
    build_filtered_data_tree(tesis_soiling, data_pre)

    sr_pre.mkdir(parents=True, exist_ok=True)
    print("[2/3] Cálculo SR (módulos existentes) →", sr_pre)
    run_module(
        python_exe,
        "analysis.sr.calcular_sr_modulos",
        [str(data_pre), str(sr_pre)],
        env=env,
        cwd=tesis_soiling,
    )
    run_module(
        python_exe,
        "analysis.sr.calcular_sr_pvstand_corr",
        [str(data_pre), str(sr_pre)],
        env=env,
        cwd=tesis_soiling,
    )
    run_module(
        python_exe,
        "analysis.sr.calcular_sr_iv600_corr",
        [str(data_pre), str(sr_pre)],
        env=env,
        cwd=tesis_soiling,
    )

    if args.solo_sr and not args.full:
        print("\n[OK] Solo SR en:", sr_pre)
        print("Informe filtro:", data_pre / "_pre_sr_iqr_report.json")
        return

    if not args.full:
        print("\n[OK] SR en:", sr_pre)
        print("Para análisis completos: python run_tesis_pre_sr_iqr.py --full")
        print("Informe filtro:", data_pre / "_pre_sr_iqr_report.json")
        return

    # --- Tesis completa (sin normalizar), leyendo sr_pre_sr_iqr ---
    print("[3/3] Carpeta tesis →", out_tesis)
    out_tesis.mkdir(parents=True, exist_ok=True)
    (out_tesis / "analysis").mkdir(parents=True, exist_ok=True)

    out_stats = out_tesis / "analysis" / "stats"
    out_tend = out_tesis / "analysis" / "tendencias"
    out_corr = out_tesis / "analysis" / "correlacion"
    out_cc = out_tesis / "analysis" / "concordancia"
    out_anova = out_tesis / "analysis" / "anova"
    out_bias = out_tesis / "analysis" / "sesgo"
    out_sr_pub = out_tesis / "analysis" / "sr"
    src_pv = tesis_soiling / "analysis" / "pv_glasses"

    run_module(
        python_exe,
        "analysis.stats.agregacion_semanal",
        [str(sr_pre), str(out_stats), "--solo-sin-normalizar"],
        env=env,
        cwd=tesis_soiling,
    )
    prune_sr_norm_outputs(out_stats)
    # dispersion_semanal_completo.png: mismo boxplot que el principal (sin PV Glasses).
    png_disp = out_stats / "dispersion_semanal.png"
    png_disp_completo = out_stats / "dispersion_semanal_completo.png"
    if png_disp.is_file():
        shutil.copy2(png_disp, png_disp_completo)
        print("[COPY]", png_disp_completo, "← sin PV Glasses (igual que dispersion_semanal.png)")
    readme_sombra = tesis_soiling / "analysis" / "stats" / "README_grafico_q25_sombra.md"
    if readme_sombra.is_file():
        shutil.copy2(readme_sombra, out_stats / "README_grafico_q25_sombra.md")
        print("[COPY]", out_stats / "README_grafico_q25_sombra.md")

    run_module(
        python_exe,
        "analysis.stats.dispersion_diaria",
        [str(sr_pre), str(out_stats)],
        env=env,
        cwd=tesis_soiling,
    )

    wide_csv = out_stats / "sr_semanal_q25.csv"
    long_csv = out_stats / "sr_semanal_q25_largo.csv"

    run_module(
        python_exe,
        "analysis.tendencias.analisis_tendencias",
        [str(wide_csv), str(out_tend), str(sr_pre)],
        env=env,
        cwd=tesis_soiling,
    )
    run_module(
        python_exe,
        "analysis.correlacion.correlacion_cruzada",
        [str(wide_csv), str(out_corr)],
        env=env,
        cwd=tesis_soiling,
    )
    run_module(
        python_exe,
        "analysis.concordancia.concordancia_intermetodologica",
        [str(wide_csv), str(out_cc)],
        env=env,
        cwd=tesis_soiling,
    )
    run_module(
        python_exe,
        "analysis.anova.anova_sr",
        [str(long_csv), str(out_anova)],
        env=env,
        cwd=tesis_soiling,
    )
    run_module(
        python_exe,
        "analysis.sesgo.sesgo_referencia",
        [str(wide_csv), str(out_bias)],
        env=env,
        cwd=tesis_soiling,
    )

    safe_rmtree(out_sr_pub)
    out_sr_pub.mkdir(parents=True, exist_ok=True)
    for f in sr_pre.glob("*.csv"):
        shutil.copy2(f, out_sr_pub / f.name)
    print("[COPY] SR →", out_sr_pub)

    if str(tesis_soiling) not in sys.path:
        sys.path.insert(0, str(tesis_soiling))

    from analysis import grafico_sr_diario_intercomparacion as mod  # type: ignore

    out_inter = out_tesis / "analysis"
    inter_data = out_inter / "intercomparacion_data_pre_sr_iqr"
    mod.run(
        project_root=str(out_tesis),
        output_path=str(out_inter / "intercomparacion_sr_diario_sin_normalizar.png"),
        use_corr_series=False,
        normalize_series=False,
        export_data_dir=str(inter_data),
        include_pv_glasses=False,
    )
    mod.run(
        project_root=str(out_tesis),
        output_path=str(out_inter / "intercomparacion_sr_diario_sin_normalizar_corr.png"),
        use_corr_series=True,
        normalize_series=False,
        export_data_dir=str(inter_data),
        include_pv_glasses=False,
    )

    if args.copiar_pv_glasses:
        dest = out_tesis / "analysis" / "pv_glasses"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src_pv, dest)
        run_module(
            python_exe,
            "analysis.pv_glasses.pv_glasses_calendario",
            [str(dest)],
            env=env,
            cwd=tesis_soiling,
        )

    out_unc = out_tesis / "analysis" / "uncertainty" / "results"
    out_unc.mkdir(parents=True, exist_ok=True)
    try:
        from analysis.uncertainty.tabla_resumen_incertidumbre_sr import (  # type: ignore
            build_tabla_resumen_incertidumbre_sr_sin_normalizar,
        )

        build_tabla_resumen_incertidumbre_sr_sin_normalizar(
            base_dir=str(out_tesis),
            out_dir=str(out_unc),
        )
        print(
            "[OK] Incertidumbre SR:",
            out_unc / "resumen_incertidumbre_sr_por_metodologia_sin_normalizar.csv",
        )
    except Exception as exc:
        print("[WARN] Resumen incertidumbre SR no generado:", exc)

    print("\n[OK] TESIS_PRE_SR_IQR generado en:", out_tesis)
    print("Datos filtrados (pre-SR):", data_pre)
    print("SR desde datos filtrados:", sr_pre)
    print("Informe JSON filtro:", data_pre / "_pre_sr_iqr_report.json")


if __name__ == "__main__":
    main()
