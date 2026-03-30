import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_module(python_exe: str, module: str, args: list[str], env: dict):
    cmd = [python_exe, "-m", module] + args
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def safe_rmtree(path: Path):
    if path.exists():
        shutil.rmtree(path)


def prune_sr_norm_outputs(stats_dir: Path):
    """
    En modo SIN normalizar queremos conservar solo archivos 'crudos' (sr_semanal_q25*)
    y eliminar los que son explícitamente normalizados (sr_semanal_norm*).
    """
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
    parser = argparse.ArgumentParser(description="Genera resultados de tesis en modo normalizado / sin normalizar.")
    parser.add_argument("--modo", choices=["sin_normalizar", "normalizado", "both"], default="sin_normalizar")
    parser.add_argument("--force", action="store_true", help="Borra carpetas de salida antes de regenerar.")
    parser.add_argument("--copiar-pv-glasses", action="store_true", default=True, help="Copia analysis/pv_glasses completo.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    tesis_soiling_root = repo_root / "TESIS_SOILING"
    out_no_norm_root = repo_root / "TESIS_NO_NORM"
    out_norm_root = repo_root / "TESIS_NORMALIZADO"

    out_roots = []
    if args.modo in ("sin_normalizar", "both"):
        out_roots.append(("sin_normalizar", out_no_norm_root))
    if args.modo in ("normalizado", "both"):
        out_roots.append(("normalizado", out_norm_root))

    # Preferir el python del venv del proyecto (incluye dependencias como pandas).
    venv_python = repo_root / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tesis_soiling_root)

    # Ruta fuente SR y pv_glasses (siempre desde TESIS_SOILING)
    sr_dir = str(tesis_soiling_root / "analysis" / "sr")
    src_pv_glasses_dir = tesis_soiling_root / "analysis" / "pv_glasses"

    for mode, out_base in out_roots:
        print(f"\n===== Modo: {mode} → salida: {out_base} =====")
        if args.force:
            safe_rmtree(out_base)
        (out_base / "analysis").mkdir(parents=True, exist_ok=True)

        out_stats_dir = out_base / "analysis" / "stats"
        out_tend_dir = out_base / "analysis" / "tendencias"
        out_corr_dir = out_base / "analysis" / "correlacion"
        out_cc_dir = out_base / "analysis" / "concordancia"
        out_anova_dir = out_base / "analysis" / "anova"
        out_bias_dir = out_base / "analysis" / "sesgo"

        out_intercomparacion_dir = out_base / "analysis"
        out_inter_data_dir = out_base / "analysis" / f"intercomparacion_data_{mode}"

        # 1) Agregación semanal: en sin_normalizar solo escribe Q25/sombra/incert. Q25 (sin sr_semanal_norm*)
        agg_args = [sr_dir, str(out_stats_dir)]
        if mode == "sin_normalizar":
            agg_args.append("--solo-sin-normalizar")
        run_module(
            python_exe,
            "analysis.stats.agregacion_semanal",
            agg_args,
            env=env,
        )

        if mode == "sin_normalizar":
            # Por si quedaran restos antiguos (p. ej. ejecución manual sin el flag)
            prune_sr_norm_outputs(out_stats_dir)
            readme_sombra = tesis_soiling_root / "analysis" / "stats" / "README_grafico_q25_sombra.md"
            if readme_sombra.is_file():
                shutil.copy2(readme_sombra, out_stats_dir / "README_grafico_q25_sombra.md")
                print("[COPY]", out_stats_dir / "README_grafico_q25_sombra.md")

        # 1b) Dispersión diaria por método (mismos CSV en sr/; independiente de normalización semanal)
        run_module(
            python_exe,
            "analysis.stats.dispersion_diaria",
            [sr_dir, str(out_stats_dir)],
            env=env,
        )

        # 2) Entrada y selección de CSV según modo
        if mode == "sin_normalizar":
            wide_csv = out_stats_dir / "sr_semanal_q25.csv"
            long_csv = out_stats_dir / "sr_semanal_q25_largo.csv"
        else:
            wide_csv = out_stats_dir / "sr_semanal_norm.csv"
            long_csv = out_stats_dir / "sr_semanal_norm_largo.csv"

        # 3) Tendencias (con SR diario para Q25 mensual si modo sin normalizar)
        tend_args = [str(wide_csv), str(out_tend_dir)]
        if mode == "sin_normalizar":
            tend_args.append(str(tesis_soiling_root / "analysis" / "sr"))
        run_module(
            python_exe,
            "analysis.tendencias.analisis_tendencias",
            tend_args,
            env=env,
        )

        # 4) Correlación cruzada
        run_module(
            python_exe,
            "analysis.correlacion.correlacion_cruzada",
            [str(wide_csv), str(out_corr_dir)],
            env=env,
        )

        # 5) Concordancia
        run_module(
            python_exe,
            "analysis.concordancia.concordancia_intermetodologica",
            [str(wide_csv), str(out_cc_dir)],
            env=env,
        )

        # 6) ANOVA
        run_module(
            python_exe,
            "analysis.anova.anova_sr",
            [str(long_csv), str(out_anova_dir)],
            env=env,
        )

        # 7) Sesgo
        run_module(
            python_exe,
            "analysis.sesgo.sesgo_referencia",
            [str(wide_csv), str(out_bias_dir)],
            env=env,
        )

        # 8) Intercomparación SR diario (+ CSVs usados)
        sys.path.insert(0, str(tesis_soiling_root))
        from analysis import grafico_sr_diario_intercomparacion as mod  # type: ignore

        normalize_series = (mode != "sin_normalizar")
        out_inter_png = out_intercomparacion_dir / (
            "intercomparacion_sr_diario.png" if normalize_series else "intercomparacion_sr_diario_sin_normalizar.png"
        )
        out_inter_png_corr = out_intercomparacion_dir / (
            "intercomparacion_sr_diario_corr.png"
            if normalize_series
            else "intercomparacion_sr_diario_sin_normalizar_corr.png"
        )
        mod.run(
            project_root=str(tesis_soiling_root),
            output_path=str(out_inter_png),
            use_corr_series=False,
            normalize_series=normalize_series,
            export_data_dir=str(out_inter_data_dir) if mode == "sin_normalizar" else None,
        )
        mod.run(
            project_root=str(tesis_soiling_root),
            output_path=str(out_inter_png_corr),
            use_corr_series=True,
            normalize_series=normalize_series,
            export_data_dir=str(out_inter_data_dir) if mode == "sin_normalizar" else None,
        )

        # 9) pv_glasses: copia plantilla (CSVs, verificación) y regenera gráficos con el código actual de SOILING
        if args.copiar_pv_glasses:
            dest = out_base / "analysis" / "pv_glasses"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src_pv_glasses_dir, dest)
            run_module(
                python_exe,
                "analysis.pv_glasses.pv_glasses_calendario",
                [str(dest)],
                env=env,
            )

        print(f"[OK] Modo {mode} generado en: {out_base}")

    print("\nListo.")


if __name__ == "__main__":
    main()

