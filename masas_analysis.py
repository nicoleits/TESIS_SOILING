import pandas as pd
import numpy as np
import logging
import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.sr_uncertainty_mass import run_uncertainty_propagation_analysis
except ImportError:
    # Si falla el import, definir una función dummy
    def run_uncertainty_propagation_analysis(df, output_file=None):
        print("⚠️  No se pudo importar el módulo de propagación de errores")
        return False

logger = logging.getLogger(__name__)

def calcular_diferencia(masa_soiled, masa_clean):
    """
    Calcula la diferencia entre masa soiled y clean.
    Si algún valor es 0 o 0.0, retorna 0.
    Multiplica por 1000 para convertir de gramos a miligramos (mg).
    Si la diferencia es negativa (ruido/rotación), se reporta 0 (la acumulación no puede ser negativa).
    """
    if masa_soiled == 0.0 or masa_clean == 0.0 or masa_soiled == 0 or masa_clean == 0:
        return 0.0
    diferencia = masa_soiled - masa_clean
    diferencia_mg = diferencia * 1000  # 1 g = 1000 mg
    # Acumulación no negativa
    diferencia_mg = max(0.0, diferencia_mg)
    return round(diferencia_mg, 6)


def _cargar_desde_excel(excel_path, sheet_name="Hoja1"):
    """Carga el calendario desde el Excel y normaliza columnas para coincidir con el flujo CSV."""
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    # Normalizar nombres y tipos
    if "Estado" in df.columns:
        df["Estado"] = df["Estado"].astype(str).str.strip().str.lower()
    if "Estructura" in df.columns:
        df["Estructura"] = df["Estructura"].astype(str).str.strip()
    # Excel usa "Fecha medición" como día de medición = fin de exposición para esa fila
    if "Fecha medición" in df.columns and "Fin Exposicion" not in df.columns:
        df["Fin Exposicion"] = pd.to_datetime(df["Fecha medición"], errors="coerce")
    df["Inicio Exposición"] = pd.to_datetime(df["Inicio Exposición"], errors="coerce").dt.date
    df["Fin Exposicion"] = pd.to_datetime(df["Fin Exposicion"], errors="coerce").dt.date
    # Exposición en días (Excel puede tener columna "Exposición" numérica o "Tiempo" tipo "9 días")
    if "Exposición" in df.columns:
        df["Exposición"] = pd.to_numeric(df["Exposición"], errors="coerce").fillna(0).astype(int)
    elif "Tiempo" in df.columns:
        df["Exposición"] = pd.to_numeric(df["Tiempo"].astype(str).str.extract(r"(\d+)", expand=False), errors="coerce").fillna(0).astype(int)
    else:
        df["Exposición"] = 0
    for col in ["Masa A", "Masa B", "Masa C"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "Fila" in df.columns:
        df["Fila"] = pd.to_numeric(df["Fila"], errors="coerce")
    return df


def procesar_masas(csv_path=None, excel_path=None, output_path=None):
    """
    Procesa el CSV de masas emparejando por **ciclo de exposición** (mismo Inicio Exposición).

    Regla (según calendario de muestras):
    - **Fija a RC**, soiled: muestra que acaba de ser medida tras la exposición y se coloca sobre
      las FC; la masa es la "sucia" al final del periodo indicado (Inicio → Fin Exposicion).
    - **RC a Fija**, clean: masa del vidrio limpio que será (o fue) expuesto; es la referencia
      para ese ciclo (mismo Inicio Exposición).
    - Para cada fila soiled (Fija a RC), la **masa limpia** a restar es la de la fila
      **RC a Fija, Estado clean** con el **mismo Inicio Exposición**. Así se usa la masa limpia
      de la misma muestra expuesta a ese periodo, aunque la medición clean sea en otra fecha
      (ej. medida limpia el 06-08 para un periodo que terminó el 01-08: Δm = masa_sucia_01-08 - masa_limpia_06-08).
    """
    base = os.path.dirname(os.path.abspath(__file__))
    if excel_path is not None:
        input_path = excel_path
        df = _cargar_desde_excel(excel_path)
    else:
        if csv_path is None:
            csv_path = os.path.join(base, "TESIS_SOILING", "data", "calendario", "calendario_muestras_seleccionado.csv")
        input_path = csv_path
        df = pd.read_csv(csv_path)
        if "Estado" in df.columns:
            df["Estado"] = df["Estado"].astype(str).str.strip().str.lower()
        if "Estructura" in df.columns:
            df["Estructura"] = df["Estructura"].astype(str).str.strip()
        df["Masa A"] = pd.to_numeric(df["Masa A"], errors="coerce").fillna(0)
        df["Masa B"] = pd.to_numeric(df["Masa B"], errors="coerce").fillna(0)
        df["Masa C"] = pd.to_numeric(df["Masa C"], errors="coerce").fillna(0)
        df["Inicio Exposición"] = pd.to_datetime(df["Inicio Exposición"]).dt.date
        df["Fin Exposicion"] = pd.to_datetime(df["Fin Exposicion"]).dt.date
        if "Fila" not in df.columns:
            df["Fila"] = np.nan

    if output_path is None:
        output_path = os.path.join(base, "TESIS_SOILING", "analysis", "pv_glasses", "resultados_diferencias_masas.csv")

    # Usar (Inicio Exposición, Fila) para emparejar si Fila está presente y es válida
    usar_fila = "Fila" in df.columns and df["Fila"].notna().any()

    # Soiled: solo "Fija a RC", soiled (masa medida al llegar a FC tras la exposición)
    llegadas = df[(df["Estructura"] == "Fija a RC") & (df["Estado"] == "soiled")].copy()
    # Clean: "RC a Fija", clean = masa del vidrio limpio de ese ciclo (mismo Inicio y misma Fila si aplica)
    clean_rows = df[(df["Estructura"] == "RC a Fija") & (df["Estado"] == "clean")].copy()
    if usar_fila:
        clean_rows["Fila"] = clean_rows["Fila"].apply(lambda x: int(x) if pd.notna(x) and x == int(x) else x)
        clean_rows = clean_rows.drop_duplicates(subset=["Inicio Exposición", "Fila"], keep="first")
        clean_por_clave = clean_rows.set_index(["Inicio Exposición", "Fila"])
    else:
        clean_rows = clean_rows.drop_duplicates(subset=["Inicio Exposición"], keep="first")
        clean_por_clave = clean_rows.set_index("Inicio Exposición")

    resultados = []
    for idx_df_soiled, fila_soiled in llegadas.iterrows():
        inicio_exp = fila_soiled["Inicio Exposición"]
        fin_exp = fila_soiled["Fin Exposicion"]
        periodo = fila_soiled["Periodo"]
        fila_num = fila_soiled.get("Fila", np.nan) if usar_fila else None
        if usar_fila and pd.notna(fila_num):
            fila_num = int(fila_num) if fila_num == int(fila_num) else fila_num
        clave = (inicio_exp, fila_num) if usar_fila else inicio_exp
        if clave not in clean_por_clave.index:
            continue
        row_clean = clean_por_clave.loc[clave]
        if isinstance(row_clean, pd.DataFrame):
            row_clean = row_clean.iloc[0]
        fila_clean = row_clean
        # Número de fila en el archivo (1 = cabecera, 2 = primera fila de datos)
        idx_soiled = int(idx_df_soiled) + 2
        mask_clean = (df["Inicio Exposición"] == inicio_exp) & (df["Estructura"] == "RC a Fija") & (df["Estado"] == "clean")
        if usar_fila and pd.notna(fila_num):
            mask_clean = mask_clean & (df["Fila"] == fila_num)
        idx_clean = int(df.loc[mask_clean].index[0]) + 2

        masa_a_diff = calcular_diferencia(fila_soiled["Masa A"], fila_clean["Masa A"])
        masa_b_diff = calcular_diferencia(fila_soiled["Masa B"], fila_clean["Masa B"])
        masa_c_diff = calcular_diferencia(fila_soiled["Masa C"], fila_clean["Masa C"])
        r = {
            "Estructura": fila_soiled["Estructura"],
            "Inicio_Exposicion": inicio_exp,
            "Fin_Exposicion": fin_exp,
            "Periodo": periodo,
            "Exposicion_dias": fila_soiled["Exposición"],
            "Diferencia_Masa_A_mg": masa_a_diff,
            "Diferencia_Masa_B_mg": masa_b_diff,
            "Diferencia_Masa_C_mg": masa_c_diff,
            "Fila_Soiled": idx_soiled,
            "Fila_Clean": idx_clean,
            "Masa_A_Soiled_g": fila_soiled["Masa A"],
            "Masa_A_Clean_g": fila_clean["Masa A"],
            "Masa_B_Soiled_g": fila_soiled["Masa B"],
            "Masa_B_Clean_g": fila_clean["Masa B"],
            "Masa_C_Soiled_g": fila_soiled["Masa C"],
            "Masa_C_Clean_g": fila_clean["Masa C"],
        }
        if usar_fila and pd.notna(fila_num):
            r["Fila"] = int(fila_num) if fila_num == int(fila_num) else fila_num
        resultados.append(r)

    df_resultados = pd.DataFrame(resultados)
    if df_resultados.empty:
        print("No se encontraron pares soiled/clean. Revisa el CSV y la columna Estado.")
        return df_resultados
    
    # Mostrar resultados
    print("Resultados del procesamiento de masas:")
    print("=" * 60)
    for idx, row in df_resultados.iterrows():
        print(f"\nPar {idx + 1}:")
        print(f"  Estructura: {row['Estructura']} (de la muestra soiled)")
        print(f"  Período: {row['Periodo']} (de la muestra soiled)")
        print(f"  Exposición: {row['Exposicion_dias']} días")
        print(f"  Fechas: {row['Inicio_Exposicion']} a {row['Fin_Exposicion']}")
        print(f"  Filas procesadas: {row['Fila_Soiled']} (soiled) - {row['Fila_Clean']} (clean)")
        print(f"  Masas soiled (g): A={row['Masa_A_Soiled_g']:.4f}, B={row['Masa_B_Soiled_g']:.4f}, C={row['Masa_C_Soiled_g']:.4f}")
        print(f"  Masas clean (g):  A={row['Masa_A_Clean_g']:.4f}, B={row['Masa_B_Clean_g']:.4f}, C={row['Masa_C_Clean_g']:.4f}")
        print(f"  Diferencias de masa (mg):")
        
        # Mostrar si alguna diferencia es 0 por tener valores 0
        masa_a_zero = row['Masa_A_Soiled_g'] == 0.0 or row['Masa_A_Clean_g'] == 0.0
        masa_b_zero = row['Masa_B_Soiled_g'] == 0.0 or row['Masa_B_Clean_g'] == 0.0
        masa_c_zero = row['Masa_C_Soiled_g'] == 0.0 or row['Masa_C_Clean_g'] == 0.0
        
        print(f"    Masa A: {row['Diferencia_Masa_A_mg']:.6f} mg" + (" (=0 por valor 0)" if masa_a_zero else ""))
        print(f"    Masa B: {row['Diferencia_Masa_B_mg']:.6f} mg" + (" (=0 por valor 0)" if masa_b_zero else ""))
        print(f"    Masa C: {row['Diferencia_Masa_C_mg']:.6f} mg" + (" (=0 por valor 0)" if masa_c_zero else ""))
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    # Redondear columnas de diferencias a 6 decimales y masas a 4 decimales
    columnas_diferencias = ['Diferencia_Masa_A_mg', 'Diferencia_Masa_B_mg', 'Diferencia_Masa_C_mg']
    columnas_masas = ['Masa_A_Soiled_g', 'Masa_A_Clean_g', 'Masa_B_Soiled_g', 'Masa_B_Clean_g',
                     'Masa_C_Soiled_g', 'Masa_C_Clean_g']
    
    # Redondear diferencias a 6 decimales para mantener cifras significativas
    for col in columnas_diferencias:
        if col in df_resultados.columns:
            df_resultados[col] = df_resultados[col].round(6)
    
    # Redondear masas a 4 decimales (son valores más grandes)
    for col in columnas_masas:
        if col in df_resultados.columns:
            df_resultados[col] = df_resultados[col].round(4)
    
    df_resultados.to_csv(output_path, index=False)
    print(f"\nResultados guardados en: {output_path}")
    
    # Calcular propagación de errores
    print("\n" + "=" * 60)
    print("CALCULANDO PROPAGACIÓN DE ERRORES DE MASAS...")
    print("=" * 60)
    try:
        success = run_uncertainty_propagation_analysis(df_resultados)
        if success:
            print("✅ Propagación de errores calculada exitosamente")
        else:
            print("⚠️  Hubo problemas al calcular la propagación de errores")
    except Exception as e:
        print(f"⚠️  Error al calcular propagación de errores: {e}")
    
    # Mostrar resumen estadístico
    print(f"\nResumen:")
    print(f"Total de pares soiled/clean procesados: {len(df_resultados)}")
    print(f"Estructuras analizadas: {df_resultados['Estructura'].nunique()}")
    print(f"Períodos incluidos: {', '.join(df_resultados['Periodo'].unique())}")
    
    # Verificar que todos los períodos corresponden a las muestras soiled
    print(f"\nVerificación:")
    print("Todos los períodos mostrados corresponden a las muestras soiled consideradas en la sustracción.")
    
    return df_resultados

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Análisis de diferencias de masa (soiled - clean) por periodo.")
    parser.add_argument("--excel", "-e", type=str, default=None, help="Ruta al Excel del calendario (Hoja1). Si no se indica, se usa el CSV por defecto.")
    parser.add_argument("--csv", "-c", type=str, default=None, help="Ruta al CSV del calendario (alternativa al Excel).")
    parser.add_argument("--output", "-o", type=str, default=None, help="Ruta del CSV de salida.")
    args = parser.parse_args()

    print("Iniciando análisis de masas...")
    print("Recuerda activar el entorno virtual antes de ejecutar.")
    print("El Período mostrado corresponde SIEMPRE a la muestra soiled.")
    if args.excel:
        print(f"Origen: Excel {args.excel} (emparejamiento por Inicio Exposición + Fila)")
    else:
        print("Origen: CSV (emparejamiento por Inicio Exposición)")
    print("-" * 50)

    try:
        resultados = procesar_masas(csv_path=args.csv, excel_path=args.excel, output_path=args.output)
        print("\n¡Análisis completado exitosamente!")
    except FileNotFoundError as e:
        print("Error: No se pudo encontrar el archivo.")
        print(f"  {e}")
        raise SystemExit(1)
    except Exception as e:
        print(f"Error durante el procesamiento: {e}")
        raise SystemExit(1)