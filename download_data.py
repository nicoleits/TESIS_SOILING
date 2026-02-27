"""
Script para descargar datos de sistemas fotovoltaicos desde ClickHouse e InfluxDB

DESCRIPCIÓN:
------------
Este script proporciona una interfaz interactiva para descargar y procesar datos de 
diferentes sensores y sistemas de monitoreo fotovoltaico desde bases de datos ClickHouse 
e InfluxDB. Permite configurar rangos de fechas, horarios y seleccionar qué tipos de 
datos descargar.

FUNCIONALIDADES PRINCIPALES:
----------------------------
1. IV600: Descarga de curvas IV del trazador manual con cálculo de parámetros eléctricos
   (PMP, ISC, VOC, IMP, VMP) o descarga de curvas completas para gráficos I-V y P-V

2. PV Glasses: Descarga de datos de fotoceldas (RFC1-RFC5) con selección de tipo de 
   estadística (Avg, Max, Min, Std) y filtrado por horario (12:00-21:00)

3. DustIQ: Descarga de datos del sensor de polvo (SR_C11_Avg)

4. Soiling Kit: Descarga de datos del kit de ensuciamiento con corrientes de cortocircuito
   y temperaturas de celdas limpias y sucias

5. PVStand: Descarga de datos de módulos PVStand (perc1fixed y perc2fixed) con parámetros
   de potencia, corriente y voltaje máximos

6. Solys2: Descarga de datos de radiación solar (GHI, DHI, DNI) desde PSDA.meteo6857

CARACTERÍSTICAS:
----------------
- Interfaz interactiva con menú de opciones
- Configuración flexible de rangos de fechas y horarios
- Selección dinámica de fotoceldas disponibles en la base de datos
- Manejo automático de timezones (UTC)
- Logging detallado de operaciones
- Validación de datos y manejo de errores
- Organización automática de archivos en subdirectorios

USO:
----
Ejecutar el script desde la línea de comandos:
    python download_data.py

El script guiará al usuario a través de:
1. Configuración de fechas de inicio y fin
2. Selección del tipo de datos a descargar
3. Configuración adicional según el tipo seleccionado (fotoceldas, horarios, etc.)

Los datos descargados se guardan en CSV en el directorio configurado:
TESIS_SOILING/data/ (dentro de esta carpeta; los .csv/.png están en .gitignore y no se suben a git)

NOTAS:
------
- Convertido desde download_notebook.ipynb
- Requiere conexión a los servidores ClickHouse e InfluxDB configurados
- Las fechas por defecto son: 01/07/2024 - 31/12/2025
"""

# ============================================================================
# SECCIÓN 1: IMPORTACIONES Y CONFIGURACIÓN INICIAL
# ============================================================================

# Importar librerías necesarias - Config. InfluxDB y Clickhouse
import pandas as pd
import numpy as np
import os
import sys
import logging
import re
from datetime import datetime
import clickhouse_connect
import gc

# Importar matplotlib para gráficos (opcional)
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend sin GUI
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Importar pvlib para POA y modelo clear-sky Ineichen (opcional)
try:
    import pvlib
    from pvlib.location import Location
    from pvlib.irradiance import get_total_irradiance
    PVLIB_AVAILABLE = True
except ImportError:
    PVLIB_AVAILABLE = False

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuración de Clickhouse
CLICKHOUSE_CONFIG = {
    'host': "146.83.153.212",  # "172.24.61.95"
    'port': "30091",
    'user': "default",
    'password': "Psda2020"
}
# Configuración de fechas por defecto
DEFAULT_START_DATE = pd.to_datetime('01/08/2024', dayfirst=True).tz_localize('UTC')
DEFAULT_END_DATE = pd.to_datetime('01/08/2025', dayfirst=True).tz_localize('UTC')

# Directorio de salida - datos dentro de TESIS_SOILING (no se suben a git: .gitignore con *.csv, *.png, etc.)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR  # TESIS_SOILING (carpeta donde está este script)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuración del sitio (irradiancia, POA, clear-sky)
SITE_CONFIG = {
    'latitude': -24.08992287800815,
    'longitude': -69.92873664034512,
    'altitude': 500,   # m
    'surface_tilt': 20,   # inclinación panel [°]
    'surface_azimuth': 0,  # azimut panel [°]
    'tz': 'UTC',
}
UMBRAL_POA = 500          # W/m² - mínimo POA para considerar condición de referencia
UMBRAL_CLEAR_SKY = 0.8    # ratio mínimo GHI_medido / GHI_clear_sky (Ineichen)
MAX_DIST_SOLAR_NOON_MIN = 50  # máx. distancia (min) ventana → mediodía solar para aceptar el día
UMBRAL_ISC_MIN = 1.0  # mínimo Isc(e) e Isc(p) en A para conservar la fila (filtro de corriente)

# ============================================================================
# FUNCIÓN PARA CONFIGURAR HORARIO Y FECHAS DE FORMA INTERACTIVA
# ============================================================================

def configurar_rango_horario():

    """
    Permite configurar un rango horario de forma interactiva.
    Si se presiona Enter, se usa el rango completo del día (00:00-23:59).
    
    Returns:
        tuple: (hora_inicio, hora_fin) como strings en formato HH:MM
    """
    print("\n" + "="*60)
    print("CONFIGURACIÓN DE RANGO HORARIO")
    print("="*60)
    
    hora_inicio_default = "00:00"
    hora_fin_default = "23:59"
    
    print(f"\n🕐 Rango horario por defecto:")
    print(f"   Inicio: {hora_inicio_default}")
    print(f"   Fin:    {hora_fin_default}")
    print(f"\n💡 Presiona Enter para usar el rango completo del día")
    print(f"   O ingresa horas en formato HH:MM (ej: 09:00, 18:00)")
    print("-"*60)
    
    # Solicitar hora de inicio
    while True:
        hora_inicio_input = input(f"\n📌 Hora de inicio [{hora_inicio_default}]: ").strip()
        
        if hora_inicio_input == "":
            hora_inicio = hora_inicio_default
            print(f"✅ Usando hora por defecto: {hora_inicio}")
            break
        else:
            # Validar formato HH:MM
            try:
                hora, minuto = map(int, hora_inicio_input.split(':'))
                if 0 <= hora <= 23 and 0 <= minuto <= 59:
                    hora_inicio = hora_inicio_input
                    print(f"✅ Hora de inicio configurada: {hora_inicio}")
                    break
                else:
                    print("❌ Error: Hora inválida. Usa formato HH:MM con horas 0-23 y minutos 0-59")
            except ValueError:
                print("❌ Error: Formato inválido. Usa HH:MM (ej: 09:00)")
    
    # Solicitar hora de fin
    while True:
        hora_fin_input = input(f"\n📌 Hora de fin [{hora_fin_default}]: ").strip()
        
        if hora_fin_input == "":
            hora_fin = hora_fin_default
            print(f"✅ Usando hora por defecto: {hora_fin}")
            break
        else:
            # Validar formato HH:MM
            try:
                hora, minuto = map(int, hora_fin_input.split(':'))
                if 0 <= hora <= 23 and 0 <= minuto <= 59:
                    hora_fin = hora_fin_input
                    print(f"✅ Hora de fin configurada: {hora_fin}")
                    break
                else:
                    print("❌ Error: Hora inválida. Usa formato HH:MM con horas 0-23 y minutos 0-59")
            except ValueError:
                print("❌ Error: Formato inválido. Usa HH:MM (ej: 18:00)")
    
    # Validar que la hora de inicio sea anterior a la de fin
    hora_inicio_minutos = int(hora_inicio.split(':')[0]) * 60 + int(hora_inicio.split(':')[1])
    hora_fin_minutos = int(hora_fin.split(':')[0]) * 60 + int(hora_fin.split(':')[1])
    
    if hora_inicio_minutos >= hora_fin_minutos:
        print("\n⚠️  ADVERTENCIA: La hora de inicio es posterior o igual a la hora de fin.")
        print("   Se intercambiarán automáticamente.")
        hora_inicio, hora_fin = hora_fin, hora_inicio
    
    print("\n" + "="*60)
    print(f"✅ Rango horario configurado:")
    print(f"   Desde: {hora_inicio}")
    print(f"   Hasta: {hora_fin}")
    print("="*60 + "\n")
    
    return hora_inicio, hora_fin

def configurar_fechas():
    """
    Permite configurar las fechas de inicio y fin de forma interactiva.
    Si se presiona Enter, se usan las fechas por defecto.
    
    Returns:
        tuple: (start_date, end_date) como objetos datetime con timezone UTC
    """
    print("\n" + "="*60)
    print("CONFIGURACIÓN DE FECHAS")
    print("="*60)
    
    # Fechas por defecto
    default_start_str = DEFAULT_START_DATE.strftime('%d/%m/%Y')
    default_end_str = DEFAULT_END_DATE.strftime('%d/%m/%Y')
    
    print(f"\n📅 Fechas por defecto:")
    print(f"   Inicio: {default_start_str}")
    print(f"   Fin:    {default_end_str}")
    print(f"\n💡 Presiona Enter para usar las fechas por defecto")
    print(f"   O ingresa nuevas fechas en formato DD/MM/YYYY")
    print("-"*60)
    
    # Solicitar fecha de inicio
    while True:
        start_input = input(f"\n📌 Fecha de inicio [{default_start_str}]: ").strip()
        
        if start_input == "":
            # Usar fecha por defecto
            start_date = DEFAULT_START_DATE
            print(f"✅ Usando fecha por defecto: {default_start_str}")
            break
        else:
            # Intentar parsear la fecha ingresada
            try:
                start_date = pd.to_datetime(start_input, dayfirst=True)
                # Asegurar que tenga timezone UTC
                if start_date.tz is None:
                    start_date = start_date.tz_localize('UTC')
                else:
                    start_date = start_date.tz_convert('UTC')
                print(f"✅ Fecha de inicio configurada: {start_date.strftime('%d/%m/%Y %H:%M:%S UTC')}")
                break
            except ValueError:
                print("❌ Error: Formato de fecha inválido. Usa DD/MM/YYYY (ej: 01/07/2024)")
    
    # Solicitar fecha de fin
    while True:
        end_input = input(f"\n📌 Fecha de fin [{default_end_str}]: ").strip()
        
        if end_input == "":
            # Usar fecha por defecto
            end_date = DEFAULT_END_DATE
            print(f"✅ Usando fecha por defecto: {default_end_str}")
            break
        else:
            # Intentar parsear la fecha ingresada
            try:
                end_date = pd.to_datetime(end_input, dayfirst=True)
                # Asegurar que tenga timezone UTC
                if end_date.tz is None:
                    end_date = end_date.tz_localize('UTC')
                else:
                    end_date = end_date.tz_convert('UTC')
                print(f"✅ Fecha de fin configurada: {end_date.strftime('%d/%m/%Y %H:%M:%S UTC')}")
                break
            except ValueError:
                print("❌ Error: Formato de fecha inválido. Usa DD/MM/YYYY (ej: 31/12/2025)")
    
    # Validar que la fecha de inicio sea anterior a la de fin
    if start_date > end_date:
        print("\n⚠️  ADVERTENCIA: La fecha de inicio es posterior a la fecha de fin.")
        print("   Se intercambiarán automáticamente.")
        start_date, end_date = end_date, start_date
    
    print("\n" + "="*60)
    print(f"✅ Rango de fechas configurado:")
    print(f"   Desde: {start_date.strftime('%d/%m/%Y %H:%M:%S UTC')}")
    print(f"   Hasta: {end_date.strftime('%d/%m/%Y %H:%M:%S UTC')}")
    print("="*60 + "\n")
    
    return start_date, end_date

# ============================================================================
# SECCIÓN 3: FUNCIONES DE DESCARGA DESDE CLICKHOUSE
# ============================================================================

# Fotoceldas por defecto
DEFAULT_PHOTODIODES = ["R_FC1_Avg", "R_FC2_Avg", "R_FC3_Avg", "R_FC4_Avg", "R_FC5_Avg"]

# Tipos de estadística disponibles
STAT_TYPES = ["Avg", "Max", "Min", "Std"]

# Mapeo de atributos a columnas de ClickHouse
# Formato: "R_FC{N}_{StatType}" -> "RFC{N}{StatType}"
ATTRIBUTE_TO_COLUMN = {
    "R_FC1_Avg": "RFC1Avg",    "R_FC2_Avg": "RFC2Avg",    "R_FC3_Avg": "RFC3Avg",    "R_FC4_Avg": "RFC4Avg",    "R_FC5_Avg": "RFC5Avg",
    "R_FC1_Max": "RFC1Max",    "R_FC2_Max": "RFC2Max",   "R_FC3_Max": "RFC3Max",    "R_FC4_Max": "RFC4Max",    "R_FC5_Max": "RFC5Max",
    "R_FC1_Min": "RFC1Min",    "R_FC2_Min": "RFC2Min",   "R_FC3_Min": "RFC3Min",    "R_FC4_Min": "RFC4Min",    "R_FC5_Min": "RFC5Min",
    "R_FC1_Std": "RFC1Std",    "R_FC2_Std": "RFC2Std",   "R_FC3_Std": "RFC3Std",    "R_FC4_Std": "RFC4Std",    "R_FC5_Std": "RFC5Std",
}

def obtener_fotoceldas_disponibles():
    """
    Obtiene las columnas disponibles (fotoceldas) de la tabla ClickHouse.
    Organiza las fotoceldas por número (RFC1, RFC2, etc.) y tipo de estadística.
    
    Returns:
        dict: Diccionario con estructura {numero_fotocelda: {stat_type: columna_clickhouse}}
              o None si hay error
    """
    client = None
    try:
        logger.info("Conectando a ClickHouse para obtener fotoceldas disponibles...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        
        # Consultar estructura de la tabla
        schema = "PSDA"
        table = "ftc6852"
        query = f"DESCRIBE TABLE {schema}.{table}"
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se pudieron obtener las columnas de la tabla")
            return None
        
        # Organizar columnas por número de fotocelda y tipo de estadística
        fotoceldas_organizadas = {}
        for row in result.result_set:
            column_name = row[0]  # Nombre de la columna
            column_upper = column_name.upper()
            
            # Filtrar solo columnas que parezcan fotoceldas (RFC*)
            if 'RFC' in column_upper:
                # Extraer número de fotocelda (ej: RFC1Avg -> 1)
                match = re.search(r'RFC(\d+)', column_upper)
                if match:
                    num_fotocelda = int(match.group(1))
                    
                    # Determinar tipo de estadística
                    stat_type = None
                    for stat in STAT_TYPES:
                        if stat.upper() in column_upper:
                            stat_type = stat
                            break
                    
                    if stat_type:
                        if num_fotocelda not in fotoceldas_organizadas:
                            fotoceldas_organizadas[num_fotocelda] = {}
                        fotoceldas_organizadas[num_fotocelda][stat_type] = column_name
        
        logger.info(f"✅ Fotoceldas disponibles encontradas: {len(fotoceldas_organizadas)} fotoceldas")
        return fotoceldas_organizadas
        
    except Exception as e:
        logger.error(f"❌ Error al obtener fotoceldas disponibles: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return None
    finally:
        if client:
            client.close()


def seleccionar_fotoceldas():
    """
    Permite seleccionar las fotoceldas y tipo de estadística de forma interactiva.
    Si se presiona Enter, se usan las fotoceldas por defecto (Avg).
    
    Returns:
        list: Lista de nombres de atributos seleccionados (ej: ["R_FC1_Avg", "R_FC2_Max"])
    """
    print("\n" + "="*60)
    print("SELECCIÓN DE FOTOCELDAS Y TIPO DE ESTADÍSTICA")
    print("="*60)
    
    # Obtener fotoceldas disponibles
    print("\n📡 Obteniendo fotoceldas disponibles desde ClickHouse...")
    fotoceldas_organizadas = obtener_fotoceldas_disponibles()
    
    if fotoceldas_organizadas is None or len(fotoceldas_organizadas) == 0:
        print("⚠️  No se pudieron obtener las fotoceldas disponibles.")
        print("   Usando fotoceldas por defecto.")
        return DEFAULT_PHOTODIODES
    
    # Paso 1: Seleccionar números de fotoceldas
    print(f"\n📊 Fotoceldas disponibles:")
    numeros_fotoceldas = sorted(fotoceldas_organizadas.keys())
    for num in numeros_fotoceldas:
        stats_disponibles = list(fotoceldas_organizadas[num].keys())
        stats_str = ", ".join(stats_disponibles)
        es_default = num <= 5  # RFC1 a RFC5 son las por defecto
        default_mark = " (por defecto)" if es_default else ""
        print(f"  {num}. RFC{num} - Tipos disponibles: {stats_str}{default_mark}")
    
    print(f"\n💡 Fotoceldas por defecto: RFC1-RFC5 con tipo Avg")
    print(f"   (Números: {', '.join(map(str, [n for n in numeros_fotoceldas if n <= 5]))})")
    print(f"\n💡 Presiona Enter para usar las fotoceldas por defecto (RFC1-RFC5, Avg)")
    print(f"   O ingresa los números de las fotoceldas separados por comas (ej: 1,2,3)")
    print("-"*60)
    
    seleccion_fotoceldas_input = input(f"\n📌 Selecciona números de fotoceldas: ").strip()
    
    if seleccion_fotoceldas_input == "":
        # Usar fotoceldas por defecto
        print(f"✅ Usando fotoceldas por defecto: RFC1-RFC5 con tipo Avg")
        return DEFAULT_PHOTODIODES
    
    # Procesar selección de fotoceldas
    try:
        numeros_seleccionados = [int(x.strip()) for x in seleccion_fotoceldas_input.split(',')]
        numeros_validos = [n for n in numeros_seleccionados if n in numeros_fotoceldas]
        
        if len(numeros_validos) == 0:
            print("❌ No se seleccionaron fotoceldas válidas. Usando fotoceldas por defecto.")
            return DEFAULT_PHOTODIODES
        
        print(f"✅ Fotoceldas seleccionadas: RFC{', RFC'.join(map(str, numeros_validos))}")
        
    except ValueError:
        print("❌ Error: Formato inválido. Usa números separados por comas (ej: 1,2,3)")
        print("   Usando fotoceldas por defecto.")
        return DEFAULT_PHOTODIODES
    
    # Paso 2: Seleccionar tipo de estadística
    print(f"\n📊 Tipos de estadística disponibles:")
    for idx, stat_type in enumerate(STAT_TYPES, 1):
        es_default = stat_type == "Avg"
        default_mark = " (por defecto)" if es_default else ""
        print(f"  {idx}. {stat_type}{default_mark}")
    
    print(f"\n💡 Tipo por defecto: Avg")
    print(f"💡 Presiona Enter para usar Avg")
    print(f"   O ingresa el número del tipo de estadística (1=Avg, 2=Max, 3=Min, 4=Std)")
    print("-"*60)
    
    seleccion_stat_input = input(f"\n📌 Selecciona tipo de estadística: ").strip()
    
    if seleccion_stat_input == "":
        stat_type_seleccionado = "Avg"
    else:
        try:
            stat_num = int(seleccion_stat_input)
            if 1 <= stat_num <= len(STAT_TYPES):
                stat_type_seleccionado = STAT_TYPES[stat_num - 1]
            else:
                print(f"⚠️  Número fuera de rango. Usando Avg por defecto.")
                stat_type_seleccionado = "Avg"
        except ValueError:
            print("❌ Error: Formato inválido. Usando Avg por defecto.")
            stat_type_seleccionado = "Avg"
    
    print(f"✅ Tipo de estadística seleccionado: {stat_type_seleccionado}")
    
    # Construir lista de atributos seleccionados
    atributos_seleccionados = []
    for num_fotocelda in numeros_validos:
        if num_fotocelda in fotoceldas_organizadas:
            if stat_type_seleccionado in fotoceldas_organizadas[num_fotocelda]:
                # Construir nombre de atributo: R_FC{N}_{StatType}
                attr_name = f"R_FC{num_fotocelda}_{stat_type_seleccionado}"
                atributos_seleccionados.append(attr_name)
            else:
                print(f"⚠️  RFC{num_fotocelda} no tiene tipo {stat_type_seleccionado}. Se omitirá.")
    
    if len(atributos_seleccionados) == 0:
        print("❌ No se pudieron construir atributos válidos. Usando fotoceldas por defecto.")
        return DEFAULT_PHOTODIODES
    
    print(f"✅ Atributos seleccionados: {', '.join(atributos_seleccionados)}")
    print("="*60 + "\n")
    
    return atributos_seleccionados

def download_iv600(start_date, end_date, output_dir):
    """
    Descarga y procesa datos de IV600 desde ClickHouse.
    
    Esta función:
    - Conecta a ClickHouse
    - Consulta datos de curvas IV del trazador manual
    - Calcula parámetros eléctricos (PMP, ISC, VOC, IMP, VMP)
    - Filtra por rango de fechas
    - Guarda los datos en CSV
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🔋 Iniciando descarga de datos IV600 desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Consultar datos
        logger.info("Consultando datos IV600...")
        query = "SELECT * FROM ref_data.iv_curves_trazador_manual"
        data_iv_curves = client.query(query)
        logger.info(f"📊 Datos obtenidos: {len(data_iv_curves.result_set)} registros")
        
        # Procesar datos
        logger.info("Procesando datos...")
        curves_list = []
        for curve in data_iv_curves.result_set:
            currents = curve[4]
            voltages = curve[3]
            powers = [currents[i] * voltages[i] for i in range(len(currents))]
            timestamp = curve[0]
            module = curve[2]
            pmp = max(powers)
            isc = max(currents)
            voc = max(voltages)
            imp = currents[np.argmax(powers)]
            vmp = voltages[np.argmax(powers)]
            curves_list.append([timestamp, module, pmp, isc, voc, imp, vmp])

        # Crear DataFrame
        logger.info("Creando DataFrame...")
        column_names = ["timestamp", "module", "pmp", "isc", "voc", "imp", "vmp"]
        df_curves = pd.DataFrame(curves_list, columns=column_names)
        
        # Convertir timestamp a datetime y asegurar que esté en UTC
        df_curves['timestamp'] = pd.to_datetime(df_curves['timestamp'])
        if df_curves['timestamp'].dt.tz is None:
            df_curves['timestamp'] = df_curves['timestamp'].dt.tz_localize('UTC')
        else:
            df_curves['timestamp'] = df_curves['timestamp'].dt.tz_convert('UTC')
        
        df_curves.set_index('timestamp', inplace=True)
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_curves.index.min()}")
        logger.info(f"   Fecha más reciente: {df_curves.index.max()}")
        
        # Filtrar por fecha usando query para mayor flexibilidad
        logger.info(f"Filtrando datos entre {start_date} y {end_date}...")
        df_curves = df_curves.query('@start_date <= index <= @end_date')
        
        if len(df_curves) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas especificado.")
            logger.info("Ajustando el rango de fechas al rango disponible en los datos...")
            df_curves = df_curves.sort_index()
        else:
            logger.info(f"✅ Se encontraron {len(df_curves)} registros en el rango especificado.")

        # Crear carpeta específica para IV600
        section_dir = os.path.join(output_dir, 'iv600')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'raw_iv600_data.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_curves.to_csv(output_filepath)
        logger.info(f"✅ Datos guardados exitosamente. Total de registros: {len(df_curves)}")
        logger.info(f"📅 Rango de fechas: {df_curves.index.min()} a {df_curves.index.max()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos IV600: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")

def download_iv600_curves_complete(start_date, end_date, output_dir, hora_inicio="00:00", hora_fin="23:59"):
    """
    Descarga los datos completos de las curvas IV desde ClickHouse.
    
    Esta función:
    - Conecta a ClickHouse
    - Consulta datos de curvas IV del trazador manual
    - Filtra por rango de fechas y horario
    - Expande cada curva en múltiples filas (una por cada punto)
    - Guarda los datos completos en CSV para gráficos I-V y P-V
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        hora_inicio (str): Hora de inicio del rango horario (formato HH:MM)
        hora_fin (str): Hora de fin del rango horario (formato HH:MM)
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🔋 Iniciando descarga de curvas IV completas desde ClickHouse...")
    logger.info(f"🕐 Rango horario: {hora_inicio} - {hora_fin}")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Consultar datos
        logger.info("Consultando datos IV600...")
        query = "SELECT * FROM ref_data.iv_curves_trazador_manual"
        data_iv_curves = client.query(query)
        logger.info(f"📊 Datos obtenidos: {len(data_iv_curves.result_set)} curvas")
        
        # Procesar datos y expandir curvas
        logger.info("Procesando y expandiendo curvas...")
        curves_data = []
        
        for curve in data_iv_curves.result_set:
            timestamp = curve[0]
            module = curve[2]
            voltages = curve[3]  # Array de voltajes
            currents = curve[4]  # Array de corrientes
            
            # Convertir timestamp a datetime
            if isinstance(timestamp, str):
                timestamp_dt = pd.to_datetime(timestamp)
            else:
                timestamp_dt = pd.to_datetime(timestamp)
            
            # Asegurar timezone UTC
            if timestamp_dt.tz is None:
                timestamp_dt = timestamp_dt.tz_localize('UTC')
            else:
                timestamp_dt = timestamp_dt.tz_convert('UTC')
            
            # Filtrar por rango de fechas
            if start_date <= timestamp_dt <= end_date:
                # Filtrar por rango horario
                hora_actual = timestamp_dt.strftime('%H:%M')
                hora_actual_minutos = int(hora_actual.split(':')[0]) * 60 + int(hora_actual.split(':')[1])
                hora_inicio_minutos = int(hora_inicio.split(':')[0]) * 60 + int(hora_inicio.split(':')[1])
                hora_fin_minutos = int(hora_fin.split(':')[0]) * 60 + int(hora_fin.split(':')[1])
                
                if hora_inicio_minutos <= hora_actual_minutos <= hora_fin_minutos:
                    # Expandir curva: crear una fila por cada punto
                    if len(voltages) == len(currents):
                        for i in range(len(voltages)):
                            voltage = voltages[i]
                            current = currents[i]
                            power = voltage * current
                            
                            curves_data.append({
                                'timestamp': timestamp_dt,
                                'module': module,
                                'voltage': voltage,
                                'current': current,
                                'power': power
                            })
        
        if len(curves_data) == 0:
            logger.warning("⚠️  No se encontraron curvas en el rango de fechas y horario especificado.")
            return False
        
        # Crear DataFrame
        logger.info("Creando DataFrame...")
        df_curves_complete = pd.DataFrame(curves_data)
        
        # Ordenar por timestamp y módulo
        df_curves_complete = df_curves_complete.sort_values(['timestamp', 'module', 'voltage'])
        
        logger.info(f"📊 Total de puntos de curva: {len(df_curves_complete)}")
        logger.info(f"📊 Total de curvas: {df_curves_complete.groupby(['timestamp', 'module']).ngroups}")
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_curves_complete['timestamp'].min()}")
        logger.info(f"   Fecha más reciente: {df_curves_complete['timestamp'].max()}")
        logger.info(f"   Módulos únicos: {df_curves_complete['module'].nunique()}")
        
        # Crear carpeta específica para IV600 Curves
        section_dir = os.path.join(output_dir, 'iv600_curves')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'raw_iv600_curves.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_curves_complete.to_csv(output_filepath, index=False)
        
        logger.info(f"✅ Datos guardados exitosamente")
        logger.info(f"📊 Total de puntos: {len(df_curves_complete):,}")
        logger.info(f"📊 Columnas: timestamp, module, voltage, current, power")
        logger.info(f"📅 Rango de fechas: {df_curves_complete['timestamp'].min()} a {df_curves_complete['timestamp'].max()}")
        logger.info(f"🕐 Rango horario aplicado: {hora_inicio} - {hora_fin}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de curvas IV completas: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")

def download_pv_glasses(start_date, end_date, output_dir, attributes=None):
    """
    Descarga y procesa datos de PV Glasses desde ClickHouse.
    
    Esta función usa los nombres correctos de columnas en ClickHouse:
    - Esquema: "PSDA"
    - Tabla: "ftc6852"
    - Columnas en ClickHouse: RFC1Avg, RFC2Avg, RFC3Avg, RFC4Avg, RFC5Avg
    - Columnas en output: R_FC1_Avg, R_FC2_Avg, R_FC3_Avg, R_FC4_Avg, R_FC5_Avg
    
    Filtra por horario (13:00-18:00), calcula REF como promedio de R_FC1_Avg y R_FC2_Avg,
    y guarda en CSV en la carpeta pv_glasses dentro del directorio de salida.
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        attributes (list, optional): Lista de atributos/fotoceldas a descargar.
                                     Si es None, usa las fotoceldas por defecto (R_FC1_Avg a R_FC5_Avg).
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🔋 Iniciando descarga de datos PV Glasses desde ClickHouse...")
    
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=CLICKHOUSE_CONFIG['port'],
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato para ClickHouse
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Usar fotoceldas por defecto si no se especifican
        if attributes is None:
            attributes = DEFAULT_PHOTODIODES  # R_FC1_Avg, R_FC2_Avg, etc.
        
        # Obtener nombres de columnas en ClickHouse usando el mapeo
        clickhouse_columns = []
        column_mapping = {}  # Mapeo de columnas ClickHouse -> nombres estándar
        for attr in attributes:
            if attr in ATTRIBUTE_TO_COLUMN:
                ch_col = ATTRIBUTE_TO_COLUMN[attr]
                clickhouse_columns.append(ch_col)
                column_mapping[ch_col] = attr
            else:
                logger.warning(f"⚠️  Atributo '{attr}' no encontrado en mapeo ATTRIBUTE_TO_COLUMN")
        
        if not clickhouse_columns:
            logger.error("❌ No se encontraron columnas válidas para consultar")
            return False
        
        # Construir consulta SQL usando los nombres correctos de ClickHouse
        columns_str = ", ".join(clickhouse_columns)
        query = f"""
        SELECT 
            timestamp,
            {columns_str}
        FROM PSDA.ftc6852 
        WHERE timestamp >= '{start_str}' 
        AND timestamp <= '{end_str}'
        ORDER BY timestamp
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query}")
        
        # Ejecutar consulta
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se obtuvieron datos de PV Glasses desde ClickHouse")
            return False
        
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame - los nombres de columnas vienen de ClickHouse (RFC1Avg, etc.)
        df_columns = ['timestamp'] + clickhouse_columns
        df_glasses = pd.DataFrame(result.result_set, columns=df_columns)
        
        # Renombrar columnas de ClickHouse a nombres estándar (R_FC1_Avg, etc.)
        column_rename_map = {'timestamp': '_time'}
        for ch_col, std_col in column_mapping.items():
            column_rename_map[ch_col] = std_col
        
        df_glasses.rename(columns=column_rename_map, inplace=True)
        
        # Convertir timestamp a datetime
        df_glasses['_time'] = pd.to_datetime(df_glasses['_time'])
        
        # Establecer índice de tiempo
        df_glasses.set_index('_time', inplace=True)
        
        logger.info(f"📅 Rango de fechas obtenido: {df_glasses.index.min()} a {df_glasses.index.max()}")
        
        # Filtrar por horario (13:00 a 18:00) - opcional según el análisis original
        df_glasses_filtered = df_glasses.between_time('12:00', '21:00')
        logger.info(f"🕐 Después del filtro horario (12:00-21:00): {len(df_glasses_filtered)} registros")
        
        # Calcular columna REF como promedio de R_FC1_Avg y R_FC2_Avg
        if 'R_FC1_Avg' in df_glasses_filtered.columns and 'R_FC2_Avg' in df_glasses_filtered.columns:
            df_glasses_filtered = df_glasses_filtered.copy()  # Evitar SettingWithCopyWarning
            df_glasses_filtered['REF'] = (df_glasses_filtered['R_FC1_Avg'] + df_glasses_filtered['R_FC2_Avg']) / 2
            logger.info("✅ Columna REF calculada como promedio de R_FC1_Avg y R_FC2_Avg")
        
        # Crear carpeta específica para PV Glasses
        section_dir = os.path.join(output_dir, 'pv_glasses')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar archivo en la carpeta de sección
        output_filepath = os.path.join(section_dir, 'raw_pv_glasses_data.csv')
        
        # Resetear índice para guardar '_time' como columna
        df_to_save = df_glasses_filtered.reset_index()
        df_to_save.to_csv(output_filepath, index=False)
        
        logger.info(f"💾 Archivo guardado: {output_filepath}")
        logger.info(f"📊 Total de registros guardados: {len(df_to_save):,}")
        logger.info(f"📅 Rango final: {df_to_save['_time'].min()} a {df_to_save['_time'].max()}")
        
        # Verificar si cubre el periodo "1 año"
        fecha_necesaria = pd.to_datetime('2025-08-05')
        if pd.to_datetime(df_to_save['_time'].max()) >= fecha_necesaria:
            logger.info(f"✅ Los datos SÍ cubren el periodo '1 año' (hasta {fecha_necesaria.strftime('%Y-%m-%d')})")
        else:
            fecha_max = pd.to_datetime(df_to_save['_time'].max())
            logger.info(f"⚠️ Los datos llegan hasta {fecha_max.strftime('%Y-%m-%d')}")
            logger.info(f"   Para cubrir '1 año' se necesita hasta {fecha_necesaria.strftime('%Y-%m-%d')}")
        
        logger.info("✅ Datos PV Glasses guardados exitosamente desde ClickHouse")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos PV Glasses desde ClickHouse: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    
    finally:
        # Cerrar conexión ClickHouse si existe
        if client:
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")

def download_dustiq_clickhouse(start_date, end_date, output_dir):
    """
    Descarga y procesa datos de DustIQ desde ClickHouse.
    
    Esta función:
    - Esquema: "PSDA"
    - Tabla: "dustiq"
    - Atributo: "SR_C11_Avg"
    - Convierte datos de formato largo a formato ancho (pivot)
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🌪️  Iniciando descarga de datos DustIQ desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato correcto para ClickHouse (asegurar timezone UTC)
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Consultar datos de dustiq desde el esquema PSDA
        logger.info("Consultando datos DustIQ desde ClickHouse...")
        query = f"""
        SELECT 
            Stamptime,
            Attribute,
            Measure
        FROM PSDA.dustiq 
        WHERE Stamptime >= '{start_str}' AND Stamptime <= '{end_str}'
        AND Attribute = 'SR_C11_Avg'
        ORDER BY Stamptime, Attribute
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query[:200]}...")
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se encontraron datos de DustIQ en ClickHouse")
            return False
            
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame
        logger.info("Procesando datos...")
        df_dustiq = pd.DataFrame(result.result_set, columns=['Stamptime', 'Attribute', 'Measure'])
        
        # Convertir Stamptime a datetime y asegurar que esté en UTC
        df_dustiq['Stamptime'] = pd.to_datetime(df_dustiq['Stamptime'])
        if df_dustiq['Stamptime'].dt.tz is None:
            df_dustiq['Stamptime'] = df_dustiq['Stamptime'].dt.tz_localize('UTC')
        else:
            df_dustiq['Stamptime'] = df_dustiq['Stamptime'].dt.tz_convert('UTC')

        # Pivotar los datos para convertir de long format a wide format
        logger.info("Pivotando datos de long format a wide format...")

        # Primero, manejar duplicados agregando por promedio
        logger.info("Manejando duplicados agrupando por promedio...")
        df_dustiq_grouped = df_dustiq.groupby(['Stamptime', 'Attribute'])['Measure'].mean().reset_index()

        # Ahora hacer el pivot sin duplicados
        df_dustiq_pivot = df_dustiq_grouped.pivot(index='Stamptime', columns='Attribute', values='Measure')

        # Renombrar el índice
        df_dustiq_pivot.index.name = 'timestamp'
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_dustiq_pivot.index.min()}")
        logger.info(f"   Fecha más reciente: {df_dustiq_pivot.index.max()}")

        # Verificar que hay datos en el rango especificado
        if len(df_dustiq_pivot) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas especificado.")
            return False

        # Crear carpeta específica para DustIQ
        section_dir = os.path.join(output_dir, 'dustiq')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'raw_dustiq_data.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_dustiq_pivot.to_csv(output_filepath)

        logger.info(f"✅ Datos DustIQ desde ClickHouse guardados exitosamente")
        logger.info(f"📊 Total de registros: {len(df_dustiq_pivot)}")
        logger.info(f"📅 Rango de fechas: {df_dustiq_pivot.index.min()} a {df_dustiq_pivot.index.max()}")

        # Mostrar estadísticas básicas
        logger.info("📊 Estadísticas de los datos:")
        if 'SR_C11_Avg' in df_dustiq_pivot.columns:
            logger.info(f"   SR_C11_Avg - Rango: {df_dustiq_pivot['SR_C11_Avg'].min():.3f} a {df_dustiq_pivot['SR_C11_Avg'].max():.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos DustIQ desde ClickHouse: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")

def download_soiling_kit_clickhouse(start_date, end_date, output_dir):
    """
    Descarga y procesa datos del Soiling Kit desde ClickHouse.
    
    Esta función:
    - Esquema: "PSDA"
    - Tabla: "soiling_kit"
    - Columnas: "timestamp", "Isc(e)", "Isc(p)", "Te(C)", "Tp(C)"
    - La tabla ya tiene las columnas en formato ancho (wide format)
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🌪️  Iniciando descarga de datos del Soiling Kit desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato correcto para ClickHouse (asegurar timezone UTC)
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Consultar datos del Soiling Kit desde PSDA.soiling_kit
        # La tabla ya tiene las columnas en formato ancho (wide format)
        logger.info("Consultando datos del Soiling Kit desde ClickHouse...")
        query = f"""
        SELECT 
            timestamp,
            `Isc(e)`,
            `Isc(p)`,
            `Te(C)`,
            `Tp(C)`
        FROM PSDA.soiling_kit 
        WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}'
        ORDER BY timestamp
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query[:200]}...")
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se encontraron datos del Soiling Kit en ClickHouse")
            return False
            
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame con el orden correcto: timestamp, Isc(e), Isc(p), Te(C), Tp(C)
        logger.info("Procesando datos...")
        df_soilingkit = pd.DataFrame(result.result_set, columns=['timestamp', 'Isc(e)', 'Isc(p)', 'Te(C)', 'Tp(C)'])
        
        # Convertir timestamp a datetime y asegurar que esté en UTC
        df_soilingkit['timestamp'] = pd.to_datetime(df_soilingkit['timestamp'])
        if df_soilingkit['timestamp'].dt.tz is None:
            df_soilingkit['timestamp'] = df_soilingkit['timestamp'].dt.tz_localize('UTC')
        else:
            df_soilingkit['timestamp'] = df_soilingkit['timestamp'].dt.tz_convert('UTC')
        
        # Reordenar columnas según el orden correcto: timestamp, Isc(e), Isc(p), Te(C), Tp(C)
        column_order = ['timestamp', 'Isc(e)', 'Isc(p)', 'Te(C)', 'Tp(C)']
        # Seleccionar solo las columnas en el orden correcto
        df_soilingkit = df_soilingkit[column_order]
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_soilingkit['timestamp'].min()}")
        logger.info(f"   Fecha más reciente: {df_soilingkit['timestamp'].max()}")
        
        # Verificar que hay datos en el rango especificado
        if len(df_soilingkit) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas especificado.")
            return False
        
        # Crear carpeta específica para Soiling Kit
        section_dir = os.path.join(output_dir, 'soiling_kit')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'soiling_kit_raw_data.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_soilingkit.to_csv(output_filepath, index=False)
        
        logger.info(f"✅ Datos del Soiling Kit desde ClickHouse guardados exitosamente")
        logger.info(f"📊 Total de registros: {len(df_soilingkit)}")
        logger.info(f"📅 Rango de fechas: {df_soilingkit['timestamp'].min()} a {df_soilingkit['timestamp'].max()}")

        # Mostrar estadísticas básicas
        logger.info("📊 Estadísticas de los datos:")
        if 'Isc(e)' in df_soilingkit.columns:
            logger.info(f"   Isc(e) - Rango: {df_soilingkit['Isc(e)'].min():.3f} a {df_soilingkit['Isc(e)'].max():.3f}")
        if 'Isc(p)' in df_soilingkit.columns:
            logger.info(f"   Isc(p) - Rango: {df_soilingkit['Isc(p)'].min():.3f} a {df_soilingkit['Isc(p)'].max():.3f}")
        if 'Te(C)' in df_soilingkit.columns:
            logger.info(f"   Te(C) - Rango: {df_soilingkit['Te(C)'].min():.1f} a {df_soilingkit['Te(C)'].max():.1f}")
        if 'Tp(C)' in df_soilingkit.columns:
            logger.info(f"   Tp(C) - Rango: {df_soilingkit['Tp(C)'].min():.1f} a {df_soilingkit['Tp(C)'].max():.1f}")
        
        # Mostrar información sobre la estructura de datos
        logger.info("📋 Estructura de datos del Soiling Kit:")
        logger.info(f"   - Isc(e): Corriente de cortocircuito de la celda expuesta/sucia")
        logger.info(f"   - Isc(p): Corriente de cortocircuito de la celda protegida/limpia (referencia)")
        logger.info(f"   - Te(C): Temperatura de la celda expuesta/sucia en Celsius")
        logger.info(f"   - Tp(C): Temperatura de la celda protegida/limpia en Celsius")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos del Soiling Kit desde ClickHouse: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")

def download_soiling_kit_long_clickhouse(start_date, end_date, output_dir):
    """
    Descarga y procesa datos del Soiling Kit desde ClickHouse (formato largo).
    
    Esta función:
    - Esquema: "PSDA"
    - Tabla: "soilingkit" (sin guion bajo)
    - Columnas: "Stamptime", "Attribute", "Measure" (formato largo)
    - Convierte datos de formato largo a formato ancho (pivot)
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🌪️  Iniciando descarga de datos del Soiling Kit (formato largo) desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato correcto para ClickHouse (asegurar timezone UTC)
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Consultar datos del Soiling Kit desde PSDA.soilingkit (formato largo)
        logger.info("Consultando datos del Soiling Kit (formato largo) desde ClickHouse...")
        query = f"""
        SELECT 
            Stamptime,
            Attribute,
            Measure
        FROM PSDA.soilingkit 
        WHERE Stamptime >= '{start_str}' AND Stamptime <= '{end_str}'
        ORDER BY Stamptime, Attribute
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query[:200]}...")
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se encontraron datos del Soiling Kit (formato largo) en ClickHouse")
            return False
            
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame
        logger.info("Procesando datos...")
        df_soilingkit = pd.DataFrame(result.result_set, columns=['Stamptime', 'Attribute', 'Measure'])
        
        # Convertir Stamptime a datetime y asegurar que esté en UTC
        df_soilingkit['Stamptime'] = pd.to_datetime(df_soilingkit['Stamptime'])
        if df_soilingkit['Stamptime'].dt.tz is None:
            df_soilingkit['Stamptime'] = df_soilingkit['Stamptime'].dt.tz_localize('UTC')
        else:
            df_soilingkit['Stamptime'] = df_soilingkit['Stamptime'].dt.tz_convert('UTC')

        # Mostrar atributos únicos encontrados
        atributos_unicos = df_soilingkit['Attribute'].unique()
        logger.info(f"📊 Atributos encontrados: {', '.join(atributos_unicos)}")
        
        # Pivotar los datos para convertir de long format a wide format
        logger.info("Pivotando datos de long format a wide format...")

        # Primero, manejar duplicados agregando por promedio
        logger.info("Manejando duplicados agrupando por promedio...")
        df_soilingkit_grouped = df_soilingkit.groupby(['Stamptime', 'Attribute'])['Measure'].mean().reset_index()

        # Ahora hacer el pivot sin duplicados
        df_soilingkit_pivot = df_soilingkit_grouped.pivot(index='Stamptime', columns='Attribute', values='Measure')

        # Renombrar el índice
        df_soilingkit_pivot.index.name = 'timestamp'
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_soilingkit_pivot.index.min()}")
        logger.info(f"   Fecha más reciente: {df_soilingkit_pivot.index.max()}")

        # Verificar que hay datos en el rango especificado
        if len(df_soilingkit_pivot) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas especificado.")
            return False

        # Crear carpeta específica para Soiling Kit (formato largo)
        section_dir = os.path.join(output_dir, 'soilingkit')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'soilingkit_raw_data.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_soilingkit_pivot.to_csv(output_filepath)

        logger.info(f"✅ Datos del Soiling Kit (formato largo) desde ClickHouse guardados exitosamente")
        logger.info(f"📊 Total de registros: {len(df_soilingkit_pivot)}")
        logger.info(f"📅 Rango de fechas: {df_soilingkit_pivot.index.min()} a {df_soilingkit_pivot.index.max()}")

        # Mostrar estadísticas básicas por atributo
        logger.info("📊 Estadísticas de los datos:")
        for attr in df_soilingkit_pivot.columns:
            if attr in df_soilingkit_pivot.columns:
                logger.info(f"   {attr} - Rango: {df_soilingkit_pivot[attr].min():.3f} a {df_soilingkit_pivot[attr].max():.3f}")
                logger.info(f"   {attr} - Promedio: {df_soilingkit_pivot[attr].mean():.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos del Soiling Kit (formato largo) desde ClickHouse: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")


def download_pvstand_clickhouse(start_date, end_date, output_dir):
    """
    Descarga y procesa datos de PVStand desde ClickHouse.
    
    Esta función:
    - Esquema: "PSDA"
    - Tablas: "perc1fixed" y "perc2fixed"
    - Columnas: "timestamp", "module", "pmax", "imax", "umax"
    - Combina datos de ambas tablas usando UNION ALL
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🔋 Iniciando descarga de datos PVStand desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato correcto para ClickHouse (asegurar timezone UTC)
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Consultar datos de PVStand desde las tablas perc1fixed y perc2fixed
        logger.info("Consultando datos PVStand desde ClickHouse...")
        query = f"""
        SELECT 
            timestamp,
            'perc1fixed' as module,
            pmax,
            imax,
            umax
        FROM PSDA.perc1fixed 
        WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}'
        
        UNION ALL
        
        SELECT 
            timestamp,
            'perc2fixed' as module,
            pmax,
            imax,
            umax
        FROM PSDA.perc2fixed 
        WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}'
        
        ORDER BY timestamp
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query[:200]}...")
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se encontraron datos de PVStand en ClickHouse")
            return False
            
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame
        logger.info("Procesando datos...")
        df_pvstand = pd.DataFrame(result.result_set, columns=['timestamp', 'module', 'pmax', 'imax', 'umax'])
        
        # Convertir timestamp a datetime y asegurar que esté en UTC
        df_pvstand['timestamp'] = pd.to_datetime(df_pvstand['timestamp'])
        if df_pvstand['timestamp'].dt.tz is None:
            df_pvstand['timestamp'] = df_pvstand['timestamp'].dt.tz_localize('UTC')
        else:
            df_pvstand['timestamp'] = df_pvstand['timestamp'].dt.tz_convert('UTC')

        # Establecer timestamp como índice
        df_pvstand.set_index('timestamp', inplace=True)
        
        # Ordenar por timestamp (importante para series temporales)
        logger.info("Ordenando datos por timestamp...")
        df_pvstand = df_pvstand.sort_index()
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_pvstand.index.min()}")
        logger.info(f"   Fecha más reciente: {df_pvstand.index.max()}")

        # Verificar que hay datos en el rango especificado
        if len(df_pvstand) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas especificado.")
            return False

        # Mostrar distribución por módulo
        module_counts = df_pvstand['module'].value_counts()
        logger.info("📊 Distribución por módulo:")
        for module, count in module_counts.items():
            logger.info(f"   - {module}: {count} registros")

        # Crear carpeta específica para PVStand
        section_dir = os.path.join(output_dir, 'pvstand')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'raw_pvstand_iv_data.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_pvstand.to_csv(output_filepath)

        logger.info(f"✅ Datos PVStand desde ClickHouse guardados exitosamente")
        logger.info(f"📊 Total de registros: {len(df_pvstand)}")
        logger.info(f"📅 Rango de fechas: {df_pvstand.index.min()} a {df_pvstand.index.max()}")

        # Mostrar estadísticas básicas por módulo
        logger.info("📊 Estadísticas de los datos por módulo:")
        for module in ['perc1fixed', 'perc2fixed']:
            if module in df_pvstand['module'].values:
                module_data = df_pvstand[df_pvstand['module'] == module]
                logger.info(f"\n{module}:")
                logger.info(f"   pmax - Rango: {module_data['pmax'].min():.3f} a {module_data['pmax'].max():.3f}")
                logger.info(f"   imax - Rango: {module_data['imax'].min():.3f} a {module_data['imax'].max():.3f}")
                logger.info(f"   umax - Rango: {module_data['umax'].min():.3f} a {module_data['umax'].max():.3f}")
        
        # Mostrar información sobre la estructura de datos
        logger.info("\n📋 Estructura de datos del PVStand:")
        logger.info(f"   - module: Identificador del módulo (perc1fixed/perc2fixed)")
        logger.info(f"   - pmax: Potencia máxima del módulo")
        logger.info(f"   - imax: Corriente máxima del módulo")
        logger.info(f"   - umax: Voltaje máximo del módulo")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos PVStand desde ClickHouse: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")

def download_pv_modules_temperature_clickhouse(start_date, end_date, output_dir):
    """
    Descarga y procesa datos de temperatura de módulos fotovoltaicos desde ClickHouse.
    
    Esta función descarga datos de temperatura que se utilizan tanto en análisis de PVStand
    como en IV600. Los datos provienen de:
    - Esquema: "PSDA"
    - Tabla: "fixed_plant_atamo_1" (misma tabla que RefCells)
    - Columnas: "timestamp", "1TE416(C)", "1TE418(C)"
    - Filtra por horario (12:00-21:00) como en el análisis de PVGlasses
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🌡️  Iniciando descarga de datos de temperatura de módulos fotovoltaicos desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato correcto para ClickHouse (asegurar timezone UTC)
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Consultar datos de temperatura desde ClickHouse
        # Los datos están en la misma tabla que RefCells: PSDA.fixed_plant_atamo_1
        logger.info("Consultando datos de temperatura de módulos fotovoltaicos desde ClickHouse...")
        query = f"""
        SELECT 
            timestamp,
            `1TE416(C)`,
            `1TE418(C)`
        FROM PSDA.fixed_plant_atamo_1 
        WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}'
        ORDER BY timestamp
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query[:200]}...")
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se encontraron datos de temperatura de módulos fotovoltaicos en ClickHouse")
            logger.info("💡 Verificando tabla: PSDA.fixed_plant_atamo_1")
            return False
            
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame
        logger.info("Procesando datos...")
        df_temp = pd.DataFrame(result.result_set, columns=['timestamp', '1TE416(C)', '1TE418(C)'])
        
        # Convertir timestamp a datetime y asegurar que esté en UTC
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'])
        if df_temp['timestamp'].dt.tz is None:
            df_temp['timestamp'] = df_temp['timestamp'].dt.tz_localize('UTC')
        else:
            df_temp['timestamp'] = df_temp['timestamp'].dt.tz_convert('UTC')
        
        # Establecer timestamp como índice
        df_temp.set_index('timestamp', inplace=True)
        
        # Ordenar por timestamp
        logger.info("Ordenando datos por timestamp...")
        df_temp = df_temp.sort_index()
        
        # Filtrar por horario (12:00-21:00) como en el análisis de PVGlasses
        logger.info("Aplicando filtro horario (12:00-21:00)...")
        df_temp_filtered = df_temp.between_time('12:00', '21:00')
        logger.info(f"📊 Registros después del filtro horario: {len(df_temp_filtered)}")
        
        # Renombrar índice a TIMESTAMP para compatibilidad con el código existente
        df_temp_filtered.index.name = 'TIMESTAMP'
        
        # Resetear índice para guardar con TIMESTAMP como columna
        df_temp_filtered = df_temp_filtered.reset_index()
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_temp_filtered['TIMESTAMP'].min()}")
        logger.info(f"   Fecha más reciente: {df_temp_filtered['TIMESTAMP'].max()}")
        
        # Verificar que hay datos en el rango especificado
        if len(df_temp_filtered) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas y horario especificado.")
            return False
        
        # Crear carpeta específica para temperatura de módulos fotovoltaicos
        # Se guarda en temperatura/ para compatibilidad con análisis existentes
        section_dir = os.path.join(output_dir, 'temperatura')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'data_temp.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_temp_filtered.to_csv(output_filepath, index=False)
        
        logger.info(f"✅ Datos de temperatura de módulos fotovoltaicos desde ClickHouse guardados exitosamente")
        logger.info(f"📊 Total de registros: {len(df_temp_filtered)}")
        logger.info(f"📅 Rango de fechas: {df_temp_filtered['TIMESTAMP'].min()} a {df_temp_filtered['TIMESTAMP'].max()}")
        
        # Mostrar estadísticas básicas
        logger.info("📊 Estadísticas de los datos:")
        if '1TE416(C)' in df_temp_filtered.columns:
            logger.info(f"   1TE416(C) - Rango: {df_temp_filtered['1TE416(C)'].min():.2f} a {df_temp_filtered['1TE416(C)'].max():.2f} °C")
            logger.info(f"   1TE416(C) - Promedio: {df_temp_filtered['1TE416(C)'].mean():.2f} °C")
        if '1TE418(C)' in df_temp_filtered.columns:
            logger.info(f"   1TE418(C) - Rango: {df_temp_filtered['1TE418(C)'].min():.2f} a {df_temp_filtered['1TE418(C)'].max():.2f} °C")
            logger.info(f"   1TE418(C) - Promedio: {df_temp_filtered['1TE418(C)'].mean():.2f} °C")
        
        # Mostrar información sobre la estructura de datos
        logger.info("\n📋 Estructura de datos de temperatura de módulos fotovoltaicos:")
        logger.info(f"   - TIMESTAMP: Fecha y hora de la medición")
        logger.info(f"   - 1TE416(C): Temperatura del módulo sucio (perc1fixed)")
        logger.info(f"   - 1TE418(C): Temperatura del módulo de referencia (perc2fixed)")
        logger.info(f"   - Nota: Estos datos se utilizan tanto en análisis de PVStand como en IV600")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos de temperatura de módulos fotovoltaicos desde ClickHouse: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")


def download_solys2_clickhouse(start_date, end_date, output_dir):
    """
    Descarga y procesa datos de radiación solar (Solys2) desde ClickHouse.
    
    Esta función:
    - Esquema: "PSDA"
    - Tabla: "meteo6857"
    - Columnas: timestamp, GHIAvg, DHIAvg, DNIAvg
    - Renombra columnas: GHIAvg -> GHI, DHIAvg -> DHI, DNIAvg -> DNI
    - Renombra timestamp -> fecha hora
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("☀️  Iniciando descarga de datos Solys2 desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato correcto para ClickHouse (asegurar timezone UTC)
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Consultar datos de solys2 desde el esquema PSDA
        # La tabla ya tiene las columnas en formato ancho
        logger.info("Consultando datos Solys2 desde ClickHouse...")
        query = f"""
        SELECT 
            timestamp,
            GHIAvg,
            DHIAvg,
            DNIAvg
        FROM PSDA.meteo6857 
        WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}'
        ORDER BY timestamp
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query[:200]}...")
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se encontraron datos de Solys2 en ClickHouse")
            return False
            
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame
        logger.info("Procesando datos...")
        df_solys2 = pd.DataFrame(result.result_set, columns=['timestamp', 'GHIAvg', 'DHIAvg', 'DNIAvg'])
        
        # Convertir timestamp a datetime y asegurar que esté en UTC
        df_solys2['timestamp'] = pd.to_datetime(df_solys2['timestamp'])
        if df_solys2['timestamp'].dt.tz is None:
            df_solys2['timestamp'] = df_solys2['timestamp'].dt.tz_localize('UTC')
        else:
            df_solys2['timestamp'] = df_solys2['timestamp'].dt.tz_convert('UTC')

        # Establecer timestamp como índice
        df_solys2.set_index('timestamp', inplace=True)
        
        # Renombrar el índice a 'fecha hora'
        df_solys2.index.name = 'fecha hora'
        
        # Renombrar las columnas: GHIAvg -> GHI, DHIAvg -> DHI, DNIAvg -> DNI
        column_rename_map = {
            'GHIAvg': 'GHI',
            'DHIAvg': 'DHI',
            'DNIAvg': 'DNI'
        }
        
        df_solys2.rename(columns=column_rename_map, inplace=True)
        
        # Reordenar columnas en el orden especificado: fecha hora, GHI, DHI, DNI
        ordered_columns = ['GHI', 'DHI', 'DNI']
        available_columns = [col for col in ordered_columns if col in df_solys2.columns]
        
        # Si hay columnas adicionales, agregarlas al final
        other_columns = [col for col in df_solys2.columns if col not in ordered_columns]
        final_column_order = available_columns + other_columns
        
        df_solys2 = df_solys2[final_column_order]
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_solys2.index.min()}")
        logger.info(f"   Fecha más reciente: {df_solys2.index.max()}")

        # Verificar que hay datos en el rango especificado
        if len(df_solys2) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas especificado.")
            return False

        # Crear carpeta específica para Solys2
        section_dir = os.path.join(output_dir, 'solys2')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'raw_solys2_data.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_solys2.to_csv(output_filepath)

        logger.info(f"✅ Datos Solys2 desde ClickHouse guardados exitosamente")
        logger.info(f"📊 Total de registros: {len(df_solys2)}")
        logger.info(f"📅 Rango de fechas: {df_solys2.index.min()} a {df_solys2.index.max()}")
        logger.info(f"📊 Columnas: {', '.join(df_solys2.columns.tolist())}")

        # Mostrar estadísticas básicas
        logger.info("📊 Estadísticas de los datos:")
        for col in ['GHI', 'DHI', 'DNI']:
            if col in df_solys2.columns:
                logger.info(f"   {col} - Rango: {df_solys2[col].min():.3f} a {df_solys2[col].max():.3f}")
                logger.info(f"   {col} - Promedio: {df_solys2[col].mean():.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos Solys2: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")


def procesar_solys2_base_referencia(solys2_csv_path, output_dir, umbral_poa=None, umbral_clear_sky=None):
    """
    Procesa datos Solys2 para generar la base de referencia de irradiancia (filtrada).
    
    2.1) Calcula POA (Plane of Array) según localidad (latitud, longitud, inclinación, azimut).
    2.2) Calcula GHI clear-sky teórico (modelo Ineichen).
    2.3) Calcula clear_sky_ratio = GHI_medido / GHI_clear_sky.
    2.4) Aplica filtros: POA >= UMBRAL_POA, clear_sky_ratio >= UMBRAL_CLEAR_SKY.
    2.5) Guarda: solys2_poa_500_clear_sky.csv (BASE DE REFERENCIA).
    
    Args:
        solys2_csv_path (str): Ruta al CSV de Solys2 (ej. raw_solys2_data.csv).
        output_dir (str): Directorio base de salida (se guarda en output_dir/solys2/).
        umbral_poa (float, optional): Mínimo POA [W/m²]. Por defecto UMBRAL_POA (500).
        umbral_clear_sky (float, optional): Mínimo ratio clear sky. Por defecto UMBRAL_CLEAR_SKY (0.8).
        
    Returns:
        str: Ruta al CSV generado, o None si pvlib no está disponible o hay error.
    """
    if not PVLIB_AVAILABLE:
        logger.warning("⚠️  pvlib no está disponible. No se puede generar la base de referencia Solys2.")
        return None
    if umbral_poa is None:
        umbral_poa = UMBRAL_POA
    if umbral_clear_sky is None:
        umbral_clear_sky = UMBRAL_CLEAR_SKY

    try:
        logger.info("📐 Procesando Solys2 → base de referencia (POA + clear-sky Ineichen)...")
        logger.info(f"   Latitud: {SITE_CONFIG['latitude']}°")
        logger.info(f"   Longitud: {SITE_CONFIG['longitude']}°")
        logger.info(f"   Altitud: {SITE_CONFIG['altitude']} m")
        logger.info(f"   Inclinación panel: {SITE_CONFIG['surface_tilt']}°")
        logger.info(f"   Azimut panel: {SITE_CONFIG['surface_azimuth']}°")
        logger.info(f"   Umbral POA: {umbral_poa} W/m² | Umbral clear_sky_ratio: {umbral_clear_sky}")

        df = pd.read_csv(solys2_csv_path)
        time_col = [c for c in df.columns if any(t in c.lower() for t in ['time', 'fecha', 'timestamp', 'date'])]
        if not time_col:
            logger.error("❌ No se encontró columna de tiempo en el CSV Solys2.")
            return None
        time_col = time_col[0]
        df[time_col] = pd.to_datetime(df[time_col])
        if df[time_col].dt.tz is None:
            df[time_col] = df[time_col].dt.tz_localize('UTC')
        else:
            df[time_col] = df[time_col].dt.tz_convert('UTC')
        df = df.set_index(time_col)
        df.index.name = 'timestamp'

        for col in ['GHI', 'DHI', 'DNI']:
            if col not in df.columns:
                logger.error(f"❌ Falta columna {col} en el CSV Solys2.")
                return None

        times = df.index
        loc = Location(
            latitude=SITE_CONFIG['latitude'],
            longitude=SITE_CONFIG['longitude'],
            tz=SITE_CONFIG['tz'],
            altitude=SITE_CONFIG['altitude']
        )

        # 2.1) Posición solar y POA
        solar_pos = loc.get_solarposition(times)
        clearsky = loc.get_clearsky(times, model='ineichen')
        ghi_cs = clearsky['ghi'].reindex(times).fillna(0)

        poa = get_total_irradiance(
            surface_tilt=SITE_CONFIG['surface_tilt'],
            surface_azimuth=SITE_CONFIG['surface_azimuth'],
            solar_zenith=solar_pos['apparent_zenith'],
            solar_azimuth=solar_pos['azimuth'],
            dni=df['DNI'].values,
            ghi=df['GHI'].values,
            dhi=df['DHI'].values,
        )
        df['POA'] = poa['poa_global'].values

        # 2.2) GHI clear-sky (Ineichen) y 2.3) ratio
        df['GHI_clear_sky'] = ghi_cs.values
        df['clear_sky_ratio'] = np.where(
            df['GHI_clear_sky'] > 1e-6,
            df['GHI'] / df['GHI_clear_sky'],
            np.nan
        )

        # 2.4) Filtros
        mask = (df['POA'] >= umbral_poa) & (df['clear_sky_ratio'] >= umbral_clear_sky)
        df_ref = df.loc[mask].copy()
        n_antes = len(df)
        n_despues = len(df_ref)

        # 2.5) Guardar
        section_dir = os.path.join(output_dir, 'solys2')
        os.makedirs(section_dir, exist_ok=True)
        out_path = os.path.join(section_dir, 'solys2_poa_500_clear_sky.csv')
        df_ref.to_csv(out_path)
        logger.info(f"✅ Base de referencia guardada: {out_path}")
        logger.info(f"   Registros antes del filtro: {n_antes} | Después (POA≥{umbral_poa}, ratio≥{umbral_clear_sky}): {n_despues}")
        return out_path

    except Exception as e:
        logger.error(f"❌ Error al procesar Solys2 base de referencia: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def filtrar_por_irradiancia_referencia(csv_path, referencia_csv_path, output_path, tolerance_minutes=5, nombre_modulo=''):
    """
    Filtra cualquier CSV con columna de tiempo dejando solo registros que coinciden con
    períodos de buena irradiancia según la base de referencia (POA ≥ 500, clear_sky_ratio ≥ 0.8).
    Aplicable a todos los módulos (IV600, PV Glasses, DustIQ, Soiling Kit, PVStand, Temperatura, RefCells).
    
    Usa merge_asof: cada registro se asocia al último timestamp de referencia anterior o igual;
    si está dentro de tolerance_minutes, se conserva.
    
    Args:
        csv_path (str): Ruta al CSV del módulo (debe tener columna de tiempo).
        referencia_csv_path (str): Ruta al CSV de referencia (solys2_poa_500_clear_sky.csv).
        output_path (str): Ruta completa del CSV de salida filtrado.
        tolerance_minutes (int): Ventana en minutos para asociar timestamp a referencia.
        nombre_modulo (str): Nombre del módulo para mensajes de log (opcional).
        
    Returns:
        str: output_path si OK, None si error.
    """
    try:
        nombre = nombre_modulo or os.path.basename(csv_path)
        df = pd.read_csv(csv_path)
        time_col = [c for c in df.columns if any(t in c.lower() for t in ['time', 'fecha', 'timestamp', 'date'])]
        if not time_col:
            logger.warning(f"⚠️  [{nombre}] No se encontró columna de tiempo. Se omite.")
            return None
        time_col = time_col[0]
        df[time_col] = pd.to_datetime(df[time_col])
        if df[time_col].dt.tz is None:
            df[time_col] = df[time_col].dt.tz_localize('UTC')
        else:
            df[time_col] = df[time_col].dt.tz_convert('UTC')
        df = df.sort_values(time_col).reset_index(drop=True)

        df_ref = pd.read_csv(referencia_csv_path)
        time_col_ref = [c for c in df_ref.columns if any(t in c.lower() for t in ['time', 'fecha', 'timestamp', 'date'])]
        if not time_col_ref:
            logger.error("❌ No se encontró columna de tiempo en el CSV de referencia.")
            return None
        time_col_ref = time_col_ref[0]
        df_ref[time_col_ref] = pd.to_datetime(df_ref[time_col_ref])
        if df_ref[time_col_ref].dt.tz is None:
            df_ref[time_col_ref] = df_ref[time_col_ref].dt.tz_localize('UTC')
        else:
            df_ref[time_col_ref] = df_ref[time_col_ref].dt.tz_convert('UTC')
        ref_times = df_ref[[time_col_ref]].drop_duplicates().sort_values(time_col_ref)

        tolerance = pd.Timedelta(minutes=tolerance_minutes)
        merged = pd.merge_asof(
            df,
            ref_times.rename(columns={time_col_ref: '_ref_time'}),
            left_on=time_col,
            right_on='_ref_time',
            direction='backward',
            tolerance=tolerance,
        )
        df_filtrado = merged[merged['_ref_time'].notna()].drop(columns=['_ref_time'])
        n_antes = len(df)
        n_despues = len(df_filtrado)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_filtrado.to_csv(output_path, index=False)
        logger.info(f"✅ [{nombre}] Filtrado: {output_path} | {n_antes} → {n_despues} registros")
        return output_path
    except Exception as e:
        logger.error(f"❌ Error al filtrar {nombre_modulo or csv_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


# Configuración: módulos a los que se aplica el filtro POA/clear-sky (section, archivo raw, nombre archivo salida)
MODULOS_FILTRO_POA_CLEAR_SKY = [
    ('iv600', 'raw_iv600_data.csv', 'iv600_poa_500_clear_sky.csv'),
    ('pv_glasses', 'raw_pv_glasses_data.csv', 'pv_glasses_poa_500_clear_sky.csv'),
    ('dustiq', 'raw_dustiq_data.csv', 'dustiq_poa_500_clear_sky.csv'),
    ('soilingkit', 'soilingkit_raw_data.csv', 'soilingkit_poa_500_clear_sky.csv'),
    ('pvstand', 'raw_pvstand_iv_data.csv', 'pvstand_poa_500_clear_sky.csv'),
    ('temperatura', 'data_temp.csv', 'temperatura_poa_500_clear_sky.csv'),
    ('refcells', 'refcells_data.csv', 'refcells_poa_500_clear_sky.csv'),
]


# RefCells: columnas de irradiancia POA; solo mantener filas con ambas >= 500 W/m²
REFCELLS_COL_SUCIA = "1RC411(w.m-2)"
REFCELLS_COL_LIMPIA = "1RC412(w.m-2)"
UMBRAL_POA_REFCELLS_W_M2 = 500


def _aplicar_filtro_poa_refcells(csv_path):
    """
    Filtra el CSV de refcells (ya filtrado por referencia) dejando solo filas con
    irradiancia POA >= 500 W/m² en ambas celdas (1RC411 y 1RC412).
    Sobrescribe el archivo. Devuelve True si OK.
    """
    try:
        df = pd.read_csv(csv_path)
        for col in (REFCELLS_COL_SUCIA, REFCELLS_COL_LIMPIA):
            if col not in df.columns:
                logger.warning(f"   [refcells] No se encontró columna {col}; no se aplica filtro POA.")
                return True
        n_antes = len(df)
        mask = (df[REFCELLS_COL_SUCIA] >= UMBRAL_POA_REFCELLS_W_M2) & (df[REFCELLS_COL_LIMPIA] >= UMBRAL_POA_REFCELLS_W_M2)
        df = df.loc[mask].reset_index(drop=True)
        df.to_csv(csv_path, index=False)
        logger.info(f"   [refcells] Filtro POA (≥{UMBRAL_POA_REFCELLS_W_M2} W/m² en ambas celdas): {n_antes} → {len(df)} registros")
        return True
    except Exception as e:
        logger.error(f"❌ Error al aplicar filtro POA en refcells: {e}")
        return False


def aplicar_filtro_poa_clear_sky_a_todos(output_dir, referencia_csv_path, tolerance_minutes=5):
    """
    Aplica el filtro por irradiancia (POA + clear-sky) a todos los módulos que tengan archivo raw.
    Salida en cada carpeta: <modulo>_poa_500_clear_sky.csv
    Para refcells, además se aplica filtro POA sobre las propias celdas (≥500 W/m² en ambas).
    """
    if not os.path.isfile(referencia_csv_path):
        logger.error(f"❌ No existe la base de referencia: {referencia_csv_path}")
        return []
    rutas_ok = []
    for section, raw_name, out_name in MODULOS_FILTRO_POA_CLEAR_SKY:
        raw_path = os.path.join(output_dir, section, raw_name)
        if not os.path.isfile(raw_path):
            logger.info(f"   [{section}] Sin archivo {raw_name}; se omite.")
            continue
        out_path = os.path.join(output_dir, section, out_name)
        if filtrar_por_irradiancia_referencia(raw_path, referencia_csv_path, out_path, tolerance_minutes, section):
            rutas_ok.append(out_path)
            if section == "refcells":
                _aplicar_filtro_poa_refcells(out_path)
    return rutas_ok


def filtrar_soiling_kit_por_irradiancia(soiling_kit_csv_path, referencia_csv_path, output_dir, tolerance_minutes=5, section='soiling_kit'):
    """
    Filtra Soiling Kit por irradiancia (wrapper que usa la función genérica).
    Mantiene compatibilidad con llamadas existentes (opción 6, descargar todo).
    """
    out_path = os.path.join(output_dir, section, f'{section}_poa_500_clear_sky.csv')
    return filtrar_por_irradiancia_referencia(
        soiling_kit_csv_path, referencia_csv_path, out_path, tolerance_minutes, section
    )


def _mediodia_solar_utc_para_fecha(fecha, loc):
    """
    Calcula la hora UTC del mediodía solar para una fecha dada en la ubicación dada.
    El mediodía solar es el instante en que la elevación solar es máxima (cenit mínimo).
    
    Args:
        fecha: date o datetime (solo se usa la fecha).
        loc: objeto pvlib.location.Location (con lat, lon, tz='UTC').
    Returns:
        pd.Timestamp: instante UTC del mediodía solar (timezone-aware).
    """
    if hasattr(fecha, 'date'):
        fecha = fecha.date()
    # Generar timestamps cada minuto para ese día en UTC
    inicio = pd.Timestamp(fecha).tz_localize('UTC')
    fin = inicio + pd.Timedelta(days=1) - pd.Timedelta(minutes=1)
    times = pd.date_range(start=inicio, end=fin, freq='1min')
    sol = loc.get_solarposition(times)
    # Mediodía solar = máxima elevación (índice donde elevation es max)
    idx_max = sol['elevation'].idxmax()
    return idx_max


def soiling_kit_seleccionar_mediodia_solar(soiling_kit_csv_path, output_dir, section='soiling_kit'):
    """
    Para cada día, calcula el mediodía solar (UTC) y selecciona la sesión de 5 minutos
    del Soiling Kit cuya hora central esté más cercana a ese mediodía solar.
    Genera un CSV con una fila por día (sesión de 5 min más cercana al mediodía solar).
    
    Args:
        soiling_kit_csv_path (str): Ruta al CSV del Soiling Kit (raw o filtrado por irradiancia).
        output_dir (str): Directorio base; salida en output_dir/<section>/.
        section (str): Sección de datos ('soiling_kit' o 'soilingkit'). Define carpeta y nombres de archivos de salida.
    Returns:
        str: Ruta al CSV generado (<section>_solar_noon.csv), o None si hay error.
    """
    if not PVLIB_AVAILABLE:
        logger.warning("⚠️  pvlib no está disponible. No se puede calcular mediodía solar.")
        return None
    try:
        logger.info("☀️  Seleccionando sesión de 5 min más cercana al mediodía solar...")

        df = pd.read_csv(soiling_kit_csv_path)
        time_col = [c for c in df.columns if any(t in c.lower() for t in ['time', 'fecha', 'timestamp', 'date'])]
        if not time_col:
            logger.error("❌ No se encontró columna de tiempo en el CSV del Soiling Kit.")
            return None
        time_col = time_col[0]
        df[time_col] = pd.to_datetime(df[time_col])
        if df[time_col].dt.tz is None:
            df[time_col] = df[time_col].dt.tz_localize('UTC')
        else:
            df[time_col] = df[time_col].dt.tz_convert('UTC')

        loc = Location(
            latitude=SITE_CONFIG['latitude'],
            longitude=SITE_CONFIG['longitude'],
            tz=SITE_CONFIG['tz'],
            altitude=SITE_CONFIG['altitude'],
        )

        # Agrupar en ventanas de 5 minutos: floor al inicio del intervalo de 5 min
        df['_bin_5min'] = df[time_col].dt.floor('5min')
        # Centro del intervalo de 5 min (representativo para "sesión de 5 min")
        df['_center_5min'] = df['_bin_5min'] + pd.Timedelta(minutes=2.5)

        columnas_dato = [c for c in df.columns if c not in (time_col, '_bin_5min', '_center_5min')]
        # Una fila por ventana de 5 min: promedios de Isc(e), Isc(p), Te(C), Tp(C)
        agregado = df.groupby('_bin_5min', as_index=False).agg(
            {**{c: 'mean' for c in columnas_dato}, '_center_5min': 'first'}
        )
        agregado = agregado.rename(columns={'_bin_5min': 'timestamp_bin', '_center_5min': 'timestamp_center'})
        agregado['_date'] = agregado['timestamp_bin'].dt.date

        # Para cada fecha, calcular mediodía solar UTC y elegir la ventana 5 min más cercana
        # Solo se aceptan ventanas a ≤ MAX_DIST_SOLAR_NOON_MIN minutos del mediodía solar
        fechas_unicas = agregado['_date'].unique()
        filas_seleccionadas = []
        dias_descartados = 0
        for fecha in sorted(fechas_unicas):
            mediodia_utc = _mediodia_solar_utc_para_fecha(fecha, loc)
            sub = agregado[agregado['_date'] == fecha]
            if sub.empty:
                continue
            # Distancia en tiempo al mediodía solar (valor absoluto)
            sub = sub.copy()
            sub['_dist'] = (sub['timestamp_center'] - mediodia_utc).abs()
            mejor_idx = sub['_dist'].idxmin()
            dist_min = sub.loc[mejor_idx, '_dist'].total_seconds() / 60.0
            if dist_min > MAX_DIST_SOLAR_NOON_MIN:
                dias_descartados += 1
                continue
            filas_seleccionadas.append(sub.loc[mejor_idx])

        if dias_descartados > 0:
            logger.info(f"   Días descartados (ventana > {MAX_DIST_SOLAR_NOON_MIN} min del mediodía solar): {dias_descartados}")
        if not filas_seleccionadas:
            logger.warning("⚠️  No se encontraron datos para ninguna fecha.")
            return None

        out_df = pd.DataFrame(filas_seleccionadas)
        # Distancia al mediodía solar en minutos (valor absoluto)
        out_df['dist_solar_noon_min'] = out_df['_dist'].dt.total_seconds() / 60.0
        out_df = out_df.drop(columns=['_dist', 'timestamp_bin', '_date'], errors='ignore')
        # Nota: el cálculo de SR se realiza en la sección análisis (analysis/sr), no aquí.
        # Filtro de corriente: conservar solo filas con Isc(e) >= UMBRAL_ISC_MIN e Isc(p) >= UMBRAL_ISC_MIN
        if 'Isc(e)' in out_df.columns and 'Isc(p)' in out_df.columns:
            n_antes_isc = len(out_df)
            out_df = out_df[(out_df['Isc(e)'] >= UMBRAL_ISC_MIN) & (out_df['Isc(p)'] >= UMBRAL_ISC_MIN)].copy()
            if n_antes_isc > len(out_df):
                logger.info(f"   Filtro corriente (Isc ≥ {UMBRAL_ISC_MIN} A): {n_antes_isc} → {len(out_df)} días.")
        if len(out_df) == 0:
            logger.warning("⚠️  No quedaron registros tras los filtros.")
            return None
        out_df = out_df.rename(columns={'timestamp_center': 'timestamp'})
        # Salida: timestamp, dist_solar_noon_min, resto de columnas (sin SR; SR se calcula en sección análisis)
        base_cols = ['timestamp', 'dist_solar_noon_min']
        columnas_orden = base_cols + [c for c in out_df.columns if c not in base_cols]
        out_df = out_df[[c for c in columnas_orden if c in out_df.columns]]

        # Estadísticos de la distancia (minutos) al mediodía solar
        d = out_df['dist_solar_noon_min']
        stats = {
            'min_min': d.min(),
            'max_min': d.max(),
            'media_min': d.mean(),
            'mediana_min': d.median(),
            'std_min': d.std(),
            'p05_min': d.quantile(0.05),
            'p25_min': d.quantile(0.25),
            'p75_min': d.quantile(0.75),
            'p95_min': d.quantile(0.95),
        }
        logger.info("📊 Distancia ventana → mediodía solar (minutos, valor absoluto):")
        logger.info(f"   Mínimo:    {stats['min_min']:.2f} min")
        logger.info(f"   Máximo:    {stats['max_min']:.2f} min")
        logger.info(f"   Media:     {stats['media_min']:.2f} min")
        logger.info(f"   Mediana:   {stats['mediana_min']:.2f} min")
        logger.info(f"   Desv. std: {stats['std_min']:.2f} min")
        logger.info(f"   P05:       {stats['p05_min']:.2f} min  |  P25: {stats['p25_min']:.2f} min  |  P75: {stats['p75_min']:.2f} min  |  P95: {stats['p95_min']:.2f} min")
        n = len(d)
        umbrales = [10, 15, 30, 45]
        logger.info("   Días con distancia ≤ umbral:")
        for umbral in umbrales:
            count = (d <= umbral).sum()
            pct = 100 * count / n
            stats[f'count_le_{umbral}_min'] = int(count)
            stats[f'pct_le_{umbral}_min'] = round(pct, 1)
            logger.info(f"      ≤ {umbral:2} min: {count:4} días  ({pct:5.1f}%)")
        logger.info(f"   Total: {n} días")

        section_dir = os.path.join(output_dir, section)
        os.makedirs(section_dir, exist_ok=True)
        out_path = os.path.join(section_dir, f'{section}_solar_noon.csv')
        out_path_stats = os.path.join(section_dir, f'{section}_solar_noon_dist_stats.csv')
        out_df.to_csv(out_path, index=False)
        pd.DataFrame([stats]).to_csv(out_path_stats, index=False)
        logger.info(f"✅ Soiling Kit (sesión mediodía solar) guardado: {out_path}")
        logger.info(f"   Estadísticos de distancia guardados: {out_path_stats}")
        logger.info(f"   Una fila por día: {len(out_df)} días. (SR: ejecutar aparte python -m analysis.sr.calcular_sr)")
        return out_path

    except Exception as e:
        logger.error(f"❌ Error al seleccionar sesión mediodía solar: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def download_refcells_clickhouse(start_date, end_date, output_dir):
    """
    Descarga y procesa datos de celdas de referencia desde ClickHouse.
    
    Esta función descarga desde ClickHouse:
    - Esquema: PSDA
    - Tabla: fixed_plant_atamo_1
    - Columnas: timestamp, 1RC411(w.m-2), 1RC412(w.m-2)
    
    Args:
        start_date (datetime): Fecha de inicio del rango (con timezone)
        end_date (datetime): Fecha de fin del rango (con timezone)
        output_dir (str): Directorio donde guardar los archivos
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario
    """
    logger.info("🔋 Iniciando descarga de datos de celdas de referencia desde ClickHouse...")
    client = None
    
    try:
        # Conectar a ClickHouse
        logger.info("Conectando a ClickHouse...")
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=int(CLICKHOUSE_CONFIG['port']),
            username=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password']
        )
        logger.info("✅ Conexión a ClickHouse establecida")
        
        # Convertir fechas al formato para ClickHouse
        if isinstance(start_date, pd.Timestamp):
            start_date_utc = pd.Timestamp(start_date)
        else:
            start_date_utc = pd.to_datetime(start_date)
            
        if isinstance(end_date, pd.Timestamp):
            end_date_utc = pd.Timestamp(end_date)
        else:
            end_date_utc = pd.to_datetime(end_date)
        
        # Asegurar timezone UTC
        if start_date_utc.tz is None:
            start_date_utc = start_date_utc.tz_localize('UTC')
        else:
            start_date_utc = start_date_utc.tz_convert('UTC')
            
        if end_date_utc.tz is None:
            end_date_utc = end_date_utc.tz_localize('UTC')
        else:
            end_date_utc = end_date_utc.tz_convert('UTC')
        
        start_str = start_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date_utc.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📅 Consultando datos desde {start_str} hasta {end_str}")
        
        # Configuración de la consulta
        schema = "PSDA"
        table = "fixed_plant_atamo_1"
        columns_to_query = ["timestamp", "1RC411(w.m-2)", "1RC412(w.m-2)"]
        
        logger.info(f"📊 Configuración:")
        logger.info(f"   Esquema: {schema}")
        logger.info(f"   Tabla: {table}")
        logger.info(f"   Columnas: {', '.join(columns_to_query)}")
        
        # Consultar datos
        query = f"""
        SELECT 
            timestamp,
            `1RC411(w.m-2)`,
            `1RC412(w.m-2)`
        FROM {schema}.{table}
        WHERE timestamp >= '{start_str}' AND timestamp <= '{end_str}'
        ORDER BY timestamp
        """
        
        logger.info("Ejecutando consulta ClickHouse...")
        logger.info(f"Consulta: {query[:200]}...")
        
        result = client.query(query)
        
        if not result.result_set:
            logger.warning("⚠️  No se encontraron datos de ref cells en ClickHouse")
            return False
        
        logger.info(f"📊 Datos obtenidos: {len(result.result_set)} registros")
        
        # Convertir a DataFrame
        logger.info("Procesando datos...")
        df_refcells = pd.DataFrame(result.result_set, columns=columns_to_query)
        
        # Convertir timestamp a datetime
        df_refcells['timestamp'] = pd.to_datetime(df_refcells['timestamp'])
        if df_refcells['timestamp'].dt.tz is None:
            df_refcells['timestamp'] = df_refcells['timestamp'].dt.tz_localize('UTC')
        else:
            df_refcells['timestamp'] = df_refcells['timestamp'].dt.tz_convert('UTC')
        
        # Establecer timestamp como índice para resample
        df_refcells.set_index('timestamp', inplace=True)
        df_refcells = df_refcells.sort_index()
        
        # Aplicar resample a 1 minuto (promedio) si es necesario
        # Verificar si ya está en resolución de 1 minuto
        if len(df_refcells) > 1:
            time_diff = df_refcells.index.to_series().diff().median()
            if time_diff > pd.Timedelta(minutes=1.5):
                logger.info("Aplicando resample a 1 minuto...")
                df_refcells = df_refcells.resample('1min').mean().dropna(how='all')
                logger.info(f"📊 Registros después del resample: {len(df_refcells)}")
        
        # Resetear índice para guardar
        df_refcells = df_refcells.reset_index()
        
        # Mostrar información sobre el rango de fechas en los datos
        logger.info(f"📅 Rango de fechas en los datos:")
        logger.info(f"   Fecha más antigua: {df_refcells['timestamp'].min()}")
        logger.info(f"   Fecha más reciente: {df_refcells['timestamp'].max()}")
        
        # Verificar que hay datos en el rango especificado
        if len(df_refcells) == 0:
            logger.warning("⚠️  No se encontraron datos en el rango de fechas especificado.")
            return False
        
        # Crear carpeta específica para RefCells
        section_dir = os.path.join(output_dir, 'refcells')
        os.makedirs(section_dir, exist_ok=True)
        logger.info(f"📁 Carpeta de sección: {section_dir}")
        
        # Guardar datos
        output_filepath = os.path.join(section_dir, 'refcells_data.csv')
        logger.info(f"💾 Guardando datos en: {output_filepath}")
        df_refcells.to_csv(output_filepath, index=False)
        
        logger.info(f"✅ Datos de celdas de referencia desde ClickHouse guardados exitosamente")
        logger.info(f"📊 Total de registros: {len(df_refcells)}")
        logger.info(f"📊 Columnas: {', '.join(df_refcells.columns.tolist())}")
        logger.info(f"📅 Rango de fechas: {df_refcells['timestamp'].min()} a {df_refcells['timestamp'].max()}")
        
        # Mostrar estadísticas básicas
        logger.info("📊 Estadísticas de los datos:")
        for col in ['1RC411(w.m-2)', '1RC412(w.m-2)']:
            if col in df_refcells.columns:
                logger.info(f"   {col} - Rango: {df_refcells[col].min():.3f} a {df_refcells[col].max():.3f} W/m²")
                logger.info(f"   {col} - Promedio: {df_refcells[col].mean():.3f} W/m²")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en la descarga de datos de celdas de referencia desde ClickHouse: {e}")
        import traceback
        logger.error(f"Detalles del error:\n{traceback.format_exc()}")
        return False
    finally:
        if client:
            logger.info("Cerrando conexión a ClickHouse...")
            client.close()
            logger.info("✅ Conexión a ClickHouse cerrada")


# ============================================================================
# GRÁFICOS ESTÁTICOS (MATPLOTLIB)
# ============================================================================

def _estatico_get_time_index(df, time_terms=None):
    """Obtiene la columna de tiempo y deja el DataFrame indexado por ella."""
    if time_terms is None:
        time_terms = ['time', 'fecha', 'timestamp', 'date', '_time']
    time_col = [col for col in df.columns if any(term in col.lower() for term in time_terms)]
    if not time_col:
        return df
    time_col = time_col[0]
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col)
    return df


def crear_grafico_pv_glasses_estatico(csv_filepath):
    """Gráfico estático PV Glasses (todas las series en un eje Y)."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        if '_time' in df.columns:
            df['_time'] = pd.to_datetime(df['_time'])
            df = df.set_index('_time')
        else:
            df = _estatico_get_time_index(df)
        columnas = [c for c in ['R_FC1_Avg', 'R_FC2_Avg', 'R_FC3_Avg', 'R_FC4_Avg', 'R_FC5_Avg'] if c in df.columns]
        if not columnas:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        for col, color in zip(columnas, colors[: len(columnas)]):
            if col in df.columns:
                ax.plot(df.index, df[col], label=col.replace('_Avg', ''), color=color, linewidth=0.8, alpha=0.9)
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Radiación (W/m²)')
        ax.set_title('PV Glasses')
        ax.legend(loc='best', fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_pv_glasses.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático PV Glasses: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_solys2_estatico(csv_filepath):
    """Gráfico estático Solys2 (GHI, DHI, DNI)."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        df = _estatico_get_time_index(df)
        columnas = [c for c in ['GHI', 'DHI', 'DNI'] if c in df.columns]
        if not columnas:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        for col, color in zip(columnas, colors):
            ax.plot(df.index, df[col], label=col, color=color, linewidth=0.8, alpha=0.9)
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Radiación (W/m²)')
        ax.set_title('Solys2 - Radiación solar')
        ax.legend(loc='best', fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_solys2.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático Solys2: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_iv600_estatico(csv_filepath):
    """Gráfico estático IV600 (pmp, isc, voc, imp, vmp)."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        df = _estatico_get_time_index(df)
        columnas = [c for c in ['pmp', 'isc', 'voc', 'imp', 'vmp'] if c in df.columns]
        if not columnas:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        nombres = ['PMP', 'ISC', 'VOC', 'IMP', 'VMP']
        for col, color, nom in zip(columnas, colors, nombres[: len(columnas)]):
            ax.plot(df.index, df[col], label=nom, color=color, linewidth=0.8, alpha=0.9)
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Valor')
        ax.set_title('IV600')
        ax.legend(loc='best', fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_iv600.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático IV600: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_pvstand_estatico(csv_filepath):
    """Gráfico estático PVStand (pmax, imax, umax)."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        df = _estatico_get_time_index(df)
        columnas = [c for c in ['pmax', 'imax', 'umax'] if c in df.columns]
        if not columnas:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        for col, color in zip(columnas, colors):
            ax.plot(df.index, df[col], label=col, color=color, linewidth=0.8, alpha=0.9)
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Valor')
        ax.set_title('PVStand')
        ax.legend(loc='best', fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_pvstand.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático PVStand: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_soiling_kit_estatico(csv_filepath):
    """
    Gráfico estático Soiling Kit con todos los parámetros:
    - Eje Y izquierdo: Isc(e), Isc(p) (corrientes)
    - Eje Y derecho: Te(C), Tp(C) (temperaturas)
    """
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        df = _estatico_get_time_index(df)
        columnas_izq = ['Isc(e)', 'Isc(p)']
        columnas_der = ['Te(C)', 'Tp(C)']
        has_left = any(c in df.columns for c in columnas_izq)
        has_right = any(c in df.columns for c in columnas_der)
        if not has_left and not has_right:
            return None
        fig, ax1 = plt.subplots(figsize=(12, 5))
        colors_izq = ['#1f77b4', '#ff7f0e']
        colors_der = ['#2ca02c', '#d62728']
        if has_left:
            for col, color in zip(columnas_izq, colors_izq):
                if col in df.columns:
                    ax1.plot(df.index, df[col], label=col, color=color, linewidth=0.8, alpha=0.9)
            ax1.set_ylabel('Isc (A)', color='#333')
            ax1.tick_params(axis='y', labelcolor='#333')
            ax1.legend(loc='upper left', fontsize=8)
        if has_right:
            ax2 = ax1.twinx()
            for col, color in zip(columnas_der, colors_der):
                if col in df.columns:
                    ax2.plot(df.index, df[col], label=col, color=color, linewidth=0.8, alpha=0.9, linestyle='--')
            ax2.set_ylabel('Temperatura (°C)', color='#333')
            ax2.tick_params(axis='y', labelcolor='#333')
            ax2.legend(loc='upper right', fontsize=8)
        ax1.set_xlabel('Fecha')
        ax1.set_title('Soiling Kit - Corrientes (izq) y Temperaturas (der)')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        fig.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_soiling_kit.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático Soiling Kit: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_temperatura_estatico(csv_filepath):
    """Gráfico estático Temperatura de módulos."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        df = _estatico_get_time_index(df)
        columnas = [c for c in df.columns if c != 'año_mes' and df[c].dtype in (np.float64, np.int64)]
        if not columnas:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        for col, color in zip(columnas, colors * ((len(columnas) // 4) + 1)):
            ax.plot(df.index, df[col], label=col, color=color, linewidth=0.8, alpha=0.9)
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Temperatura (°C)')
        ax.set_title('Temperatura de Módulos Fotovoltaicos')
        ax.legend(loc='best', fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_temperatura.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático Temperatura: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_refcells_estatico(csv_filepath):
    """Gráfico estático RefCells."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        df = _estatico_get_time_index(df)
        columnas = [c for c in df.columns if df[c].dtype in (np.float64, np.int64)]
        if not columnas:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        for col, color in zip(columnas, colors * ((len(columnas) // 5) + 1)):
            ax.plot(df.index, df[col], label=col, color=color, linewidth=0.8, alpha=0.9)
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Radiación (W/m²)')
        ax.set_title('RefCells')
        ax.legend(loc='best', fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_refcells.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático RefCells: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_dustiq_estatico(csv_filepath):
    """Gráfico estático DustIQ."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    try:
        df = pd.read_csv(csv_filepath)
        df = _estatico_get_time_index(df)
        columnas = [c for c in df.columns if df[c].dtype in (np.float64, np.int64)]
        if not columnas:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        for col, color in zip(columnas, colors * ((len(columnas) // 5) + 1)):
            ax.plot(df.index, df[col], label=col, color=color, linewidth=0.8, alpha=0.9)
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Valor')
        ax.set_title('DustIQ')
        ax.legend(loc='best', fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=25)
        plt.tight_layout()
        output_dir = os.path.dirname(csv_filepath)
        path = os.path.join(output_dir, 'grafico_dustiq.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"✅ Gráfico estático guardado: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error gráfico estático DustIQ: {e}")
        if MATPLOTLIB_AVAILABLE:
            plt.close('all')
        return None


def crear_grafico_generico_estatico(csv_filepath, tipo_datos):
    """
    Crea un gráfico estático (PNG) para el tipo de datos indicado.
    Returns:
        str: Ruta al PNG generado, o None si no aplica o hay error.
    """
    if not MATPLOTLIB_AVAILABLE:
        return None
    if tipo_datos == 'pv_glasses':
        return crear_grafico_pv_glasses_estatico(csv_filepath)
    if tipo_datos == 'solys2':
        return crear_grafico_solys2_estatico(csv_filepath)
    if tipo_datos == 'iv600':
        return crear_grafico_iv600_estatico(csv_filepath)
    if tipo_datos == 'pvstand':
        return crear_grafico_pvstand_estatico(csv_filepath)
    if tipo_datos in ('soiling_kit', 'soilingkit'):
        return crear_grafico_soiling_kit_estatico(csv_filepath)
    if tipo_datos == 'temperatura':
        return crear_grafico_temperatura_estatico(csv_filepath)
    if tipo_datos == 'refcells':
        return crear_grafico_refcells_estatico(csv_filepath)
    if tipo_datos == 'dustiq':
        return crear_grafico_dustiq_estatico(csv_filepath)
    if tipo_datos == 'iv600_curves_complete':
        return None  # Sin gráfico estático por defecto para curvas completas
    return None


# ============================================================================
# MENÚ INTERACTIVO PARA SELECCIONAR QUÉ DESCARGAR
# ============================================================================

def mostrar_menu():
    """Muestra el menú de opciones de descarga."""
    print("\n" + "="*60)
    print("MENÚ DE DESCARGA DE DATOS")
    print("="*60)
    print("\nOpciones disponibles desde ClickHouse:")
    print("  1. IV600 (puntos característicos)")
    print("  2. Curvas IV600")
    print("  3. Ambas (IV600 y PV Glasses)")
    print("  4. PV Glasses")
    print("  5. DustIQ")
    print("  6. Soiling Kit (tabla soilingkit)")
    print("  7. PVStand")
    print("  8. Temperatura de Módulos Fotovoltaicos")
    print("  9. Solys2 (Radiación solar)")
    print(" 10. RefCells (Celdas de referencia)")
    print(" 11. Procesar Solys2 → base de referencia (POA + clear-sky, filtros)")
    print(" 12. Aplicar filtro POA/clear-sky a todos los módulos")
    print(" 13. Soiling Kit (soilingkit): sesión mediodía solar (Data)")
    print(" 14. Descargar todo (todos los módulos: IV600, PV Glasses, DustIQ, Soiling Kit, PVStand, Temperatura, Solys2, RefCells)")
    print("  0. Salir")
    print("\n  (SR: ejecutar aparte: python -m analysis.sr.calcular_sr)")
    print("-"*60)


def ejecutar_descargas(start_date, end_date, opcion, fotoceldas_seleccionadas=None):
    """
    Ejecuta las descargas según la opción seleccionada.
    
    Args:
        start_date (datetime): Fecha de inicio
        end_date (datetime): Fecha de fin
        opcion (str): Opción seleccionada ('1', '2', '3', o '0')
        fotoceldas_seleccionadas (list, optional): Lista de fotoceldas seleccionadas para PV Glasses
    """
    resultados = {}
    
    if opcion == '1':
        # Solo IV600 desde ClickHouse
        print("\n🔋 Iniciando descarga de IV600 desde ClickHouse...")
        resultados['iv600'] = download_iv600(start_date, end_date, OUTPUT_DIR)

    elif opcion == '2':
        # Curvas IV completas desde ClickHouse
        print("\n🔋 Iniciando descarga de curvas IV completas desde ClickHouse...")
        # Solicitar rango horario
        hora_inicio, hora_fin = configurar_rango_horario()
        resultados['iv600_curves_complete'] = download_iv600_curves_complete(
            start_date, end_date, OUTPUT_DIR, hora_inicio, hora_fin
        )

    elif opcion == '3':
        # Ambas: IV600 y PV Glasses desde ClickHouse
        print("\n🔋 Iniciando descarga de IV600 desde ClickHouse...")
        resultados['iv600'] = download_iv600(start_date, end_date, OUTPUT_DIR)
        
        # Limpiar memoria y dar tiempo para cerrar conexiones
        gc.collect()
        
        print("\n🔋 Iniciando descarga de PV Glasses desde ClickHouse...")
        if fotoceldas_seleccionadas is None:
            fotoceldas_seleccionadas = DEFAULT_PHOTODIODES
        resultados['pv_glasses'] = download_pv_glasses(start_date, end_date, OUTPUT_DIR, fotoceldas_seleccionadas)
        
        # Limpiar memoria después de ambas descargas
        gc.collect()
        
    elif opcion == '4':
        # PV Glasses desde ClickHouse
        print("\n🔋 Iniciando descarga de PV Glasses desde ClickHouse...")
        if fotoceldas_seleccionadas is None:
            fotoceldas_seleccionadas = DEFAULT_PHOTODIODES
        resultados['pv_glasses'] = download_pv_glasses(start_date, end_date, OUTPUT_DIR, fotoceldas_seleccionadas)
        
    elif opcion == '5':
        # DustIQ desde ClickHouse
        print("\n🌪️  Iniciando descarga de DustIQ desde ClickHouse...")
        resultados['dustiq'] = download_dustiq_clickhouse(start_date, end_date, OUTPUT_DIR)

    elif opcion == '6':
        # Soiling Kit (tabla soilingkit) desde ClickHouse
        print("\n🌪️  Iniciando descarga del Soiling Kit (tabla soilingkit) desde ClickHouse...")
        resultados['soilingkit'] = download_soiling_kit_long_clickhouse(start_date, end_date, OUTPUT_DIR)
        if resultados['soilingkit']:
            ref_path = os.path.join(OUTPUT_DIR, 'solys2', 'solys2_poa_500_clear_sky.csv')
            sk_path = os.path.join(OUTPUT_DIR, 'soilingkit', 'soilingkit_raw_data.csv')
            if os.path.exists(ref_path) and os.path.exists(sk_path):
                filtrar_soiling_kit_por_irradiancia(sk_path, ref_path, OUTPUT_DIR, section='soilingkit')

    elif opcion == '7':
        # PVStand desde ClickHouse
        print("\n🔋 Iniciando descarga de PVStand desde ClickHouse...")
        resultados['pvstand'] = download_pvstand_clickhouse(start_date, end_date, OUTPUT_DIR)

    elif opcion == '8':
        # Temperatura de módulos fotovoltaicos desde ClickHouse
        print("\n🌡️  Iniciando descarga de temperatura de módulos fotovoltaicos desde ClickHouse...")
        resultados['pv_modules_temp'] = download_pv_modules_temperature_clickhouse(start_date, end_date, OUTPUT_DIR)

    elif opcion == '9':
        # Solys2 desde ClickHouse
        print("\n☀️  Iniciando descarga de Solys2 desde ClickHouse...")
        resultados['solys2'] = download_solys2_clickhouse(start_date, end_date, OUTPUT_DIR)
        if resultados['solys2'] and PVLIB_AVAILABLE:
            raw_solys2_path = os.path.join(OUTPUT_DIR, 'solys2', 'raw_solys2_data.csv')
            if os.path.exists(raw_solys2_path):
                procesar_solys2_base_referencia(raw_solys2_path, OUTPUT_DIR)

    elif opcion == '10':
        # RefCells desde ClickHouse
        print("\n🔋 Iniciando descarga de RefCells desde ClickHouse...")
        resultados['refcells'] = download_refcells_clickhouse(start_date, end_date, OUTPUT_DIR)

    elif opcion == '11':
        # Procesar Solys2 a base de referencia (sin descargar)
        raw_path = os.path.join(OUTPUT_DIR, 'solys2', 'raw_solys2_data.csv')
        if not os.path.exists(raw_path):
            print(f"\n⚠️  No existe {raw_path}. Descarga primero Solys2 (opción 9).")
        elif not PVLIB_AVAILABLE:
            print("\n⚠️  pvlib no está instalado. Instala con: pip install pvlib")
        else:
            print("\n📐 Procesando Solys2 a base de referencia (POA, clear-sky Ineichen, filtros)...")
            procesar_solys2_base_referencia(raw_path, OUTPUT_DIR)
        return

    elif opcion == '12':
        # Aplicar filtro POA/clear-sky a todos los módulos (IV600, PV Glasses, DustIQ, Soiling Kit, PVStand, Temperatura, RefCells)
        ref_path = os.path.join(OUTPUT_DIR, 'solys2', 'solys2_poa_500_clear_sky.csv')
        if not os.path.exists(ref_path):
            print(f"\n⚠️  No existe {ref_path}. Genera antes la base de referencia (opción 9 u opción 11).")
            return
        print("\n🔍 Aplicando filtro POA/clear-sky a todos los módulos...")
        rutas = aplicar_filtro_poa_clear_sky_a_todos(OUTPUT_DIR, ref_path)
        if rutas:
            print(f"   ✅ Filtrados {len(rutas)} módulo(s).")
        else:
            print("   ⚠️  No se encontraron archivos raw en ninguna carpeta de módulo.")
        return

    elif opcion == '13':
        # Soiling Kit (soilingkit): sesión mediodía solar (solo Data; SR en opción 14)
        sk_filtrado = os.path.join(OUTPUT_DIR, 'soilingkit', 'soilingkit_poa_500_clear_sky.csv')
        sk_raw = os.path.join(OUTPUT_DIR, 'soilingkit', 'soilingkit_raw_data.csv')
        if os.path.exists(sk_filtrado):
            csv_a_usar = sk_filtrado
            print("\n☀️  Usando Soiling Kit (soilingkit) filtrado. Seleccionando sesión mediodía solar...")
        elif os.path.exists(sk_raw):
            csv_a_usar = sk_raw
            print("\n☀️  Usando Soiling Kit (soilingkit) crudo. Seleccionando sesión mediodía solar...")
        else:
            print(f"\n⚠️  No hay datos soilingkit. Descarga primero (opción 6) o genera el filtrado (opción 12).")
            return
        soiling_kit_seleccionar_mediodia_solar(csv_a_usar, OUTPUT_DIR, section='soilingkit')
        return

    elif opcion == '14':
        # Descargar todos los módulos en secuencia (Solys2 antes de Soiling Kit para poder filtrar después)
        foton = fotoceldas_seleccionadas if fotoceldas_seleccionadas is not None else DEFAULT_PHOTODIODES
        print("\n" + "="*60)
        print("DESCARGA DE TODOS LOS MÓDULOS")
        print("="*60)

        print("\n🔋 [1/8] IV600...")
        resultados['iv600'] = download_iv600(start_date, end_date, OUTPUT_DIR)
        gc.collect()

        print("\n🔋 [2/8] PV Glasses...")
        resultados['pv_glasses'] = download_pv_glasses(start_date, end_date, OUTPUT_DIR, foton)
        gc.collect()

        print("\n🌪️  [3/8] DustIQ...")
        resultados['dustiq'] = download_dustiq_clickhouse(start_date, end_date, OUTPUT_DIR)
        gc.collect()

        print("\n☀️  [4/8] Solys2...")
        resultados['solys2'] = download_solys2_clickhouse(start_date, end_date, OUTPUT_DIR)
        if resultados['solys2'] and PVLIB_AVAILABLE:
            raw_solys2_path = os.path.join(OUTPUT_DIR, 'solys2', 'raw_solys2_data.csv')
            if os.path.exists(raw_solys2_path):
                procesar_solys2_base_referencia(raw_solys2_path, OUTPUT_DIR)
        gc.collect()

        print("\n🌪️  [5/8] Soiling Kit (soilingkit)...")
        resultados['soilingkit'] = download_soiling_kit_long_clickhouse(start_date, end_date, OUTPUT_DIR)
        gc.collect()

        print("\n🔋 [6/8] PVStand...")
        resultados['pvstand'] = download_pvstand_clickhouse(start_date, end_date, OUTPUT_DIR)
        gc.collect()

        print("\n🌡️  [7/8] Temperatura de módulos...")
        resultados['pv_modules_temp'] = download_pv_modules_temperature_clickhouse(start_date, end_date, OUTPUT_DIR)
        gc.collect()

        print("\n🔋 [8/8] RefCells...")
        resultados['refcells'] = download_refcells_clickhouse(start_date, end_date, OUTPUT_DIR)

        # Aplicar filtro POA/clear-sky a todos los módulos descargados
        ref_path = os.path.join(OUTPUT_DIR, 'solys2', 'solys2_poa_500_clear_sky.csv')
        if os.path.isfile(ref_path):
            print("\n🔍 Aplicando filtro POA/clear-sky a todos los módulos...")
            aplicar_filtro_poa_clear_sky_a_todos(OUTPUT_DIR, ref_path)
        # Procesamiento: selección ventana Soiling Kit más cercana al mediodía solar (después de filtros)
        sk_filtrado = os.path.join(OUTPUT_DIR, 'soilingkit', 'soilingkit_poa_500_clear_sky.csv')
        sk_raw = os.path.join(OUTPUT_DIR, 'soilingkit', 'soilingkit_raw_data.csv')
        csv_sk = sk_filtrado if os.path.isfile(sk_filtrado) else sk_raw
        if os.path.isfile(csv_sk) and PVLIB_AVAILABLE:
            print("\n☀️  Soiling Kit: selección ventana más cercana al mediodía solar...")
            soiling_kit_seleccionar_mediodia_solar(csv_sk, OUTPUT_DIR, section='soilingkit')

    elif opcion == '0':
        print("\n👋 Saliendo...")
        return
    else:
        print("\n❌ Opción inválida. Por favor selecciona una opción válida.")
        return
    
    # Mostrar resumen de resultados
    print("\n" + "="*60)
    print("RESUMEN DE DESCARGAS")
    print("="*60)
    
    # Mapeo de resultados a información de archivos
    archivos_descargados = []
    
    if 'iv600' in resultados:
        estado = "✅ Exitoso" if resultados['iv600'] else "❌ Fallido"
        print(f"  IV600: {estado}")
        if resultados['iv600']:
            archivos_descargados.append(('iv600', os.path.join(OUTPUT_DIR, 'iv600', 'raw_iv600_data.csv')))
    
    if 'pv_glasses' in resultados:
        estado = "✅ Exitoso" if resultados['pv_glasses'] else "❌ Fallido"
        print(f"  PV Glasses: {estado}")
        if resultados['pv_glasses']:
            archivos_descargados.append(('pv_glasses', os.path.join(OUTPUT_DIR, 'pv_glasses', 'raw_pv_glasses_data.csv')))
    
    if 'iv600_curves_complete' in resultados:
        estado = "✅ Exitoso" if resultados['iv600_curves_complete'] else "❌ Fallido"
        print(f"  Curvas IV Completas: {estado}")
        if resultados['iv600_curves_complete']:
            archivos_descargados.append(('iv600', os.path.join(OUTPUT_DIR, 'iv600', 'raw_iv600_curves_complete.csv')))
    
    if 'dustiq' in resultados:
        estado = "✅ Exitoso" if resultados['dustiq'] else "❌ Fallido"
        print(f"  DustIQ: {estado}")
        if resultados['dustiq']:
            archivos_descargados.append(('dustiq', os.path.join(OUTPUT_DIR, 'dustiq', 'raw_dustiq_data.csv')))
    
    if 'soilingkit' in resultados:
        estado = "✅ Exitoso" if resultados['soilingkit'] else "❌ Fallido"
        print(f"  Soiling Kit (soilingkit): {estado}")
        if resultados['soilingkit']:
            archivos_descargados.append(('soilingkit', os.path.join(OUTPUT_DIR, 'soilingkit', 'soilingkit_raw_data.csv')))
    
    if 'pvstand' in resultados:
        estado = "✅ Exitoso" if resultados['pvstand'] else "❌ Fallido"
        print(f"  PVStand: {estado}")
        if resultados['pvstand']:
            archivos_descargados.append(('pvstand', os.path.join(OUTPUT_DIR, 'pvstand', 'raw_pvstand_iv_data.csv')))
    
    if 'pv_modules_temp' in resultados:
        estado = "✅ Exitoso" if resultados['pv_modules_temp'] else "❌ Fallido"
        print(f"  Temperatura de Módulos Fotovoltaicos: {estado}")
        if resultados['pv_modules_temp']:
            archivos_descargados.append(('temperatura', os.path.join(OUTPUT_DIR, 'temperatura', 'data_temp.csv')))
    
    if 'solys2' in resultados:
        estado = "✅ Exitoso" if resultados['solys2'] else "❌ Fallido"
        print(f"  Solys2: {estado}")
        if resultados['solys2']:
            archivos_descargados.append(('solys2', os.path.join(OUTPUT_DIR, 'solys2', 'raw_solys2_data.csv')))
    
    if 'refcells' in resultados:
        estado = "✅ Exitoso" if resultados['refcells'] else "❌ Fallido"
        print(f"  RefCells: {estado}")
        if resultados['refcells']:
            archivos_descargados.append(('refcells', os.path.join(OUTPUT_DIR, 'refcells', 'refcells_data.csv')))
    
    print("="*60 + "\n")
    
    # Preguntar si quiere crear gráficos para los archivos descargados exitosamente
    if archivos_descargados and MATPLOTLIB_AVAILABLE:
        print("\n" + "="*60)
        print("GENERACIÓN DE GRÁFICOS")
        print("="*60)
        crear_graficos = input("\n¿Deseas crear gráficos estáticos de los datos descargados? (s/n): ").strip().lower()
        
        if crear_graficos == 's':
            for tipo_datos, archivo_path in archivos_descargados:
                if os.path.exists(archivo_path):
                    logger.info(f"📊 Creando gráfico para {tipo_datos}...")
                    grafico_estatico_path = crear_grafico_generico_estatico(archivo_path, tipo_datos)
                    if grafico_estatico_path:
                        print(f"  ✅ Gráfico: {grafico_estatico_path}")
                else:
                    logger.warning(f"⚠️  Archivo no encontrado: {archivo_path}")
    elif archivos_descargados and not MATPLOTLIB_AVAILABLE:
        logger.warning("⚠️  Matplotlib no está disponible. No se pueden generar gráficos.")


# ============================================================================
# CONFIGURACIÓN INICIAL AL EJECUTAR EL SCRIPT
# ============================================================================

if __name__ == "__main__":
    # Configurar fechas de forma interactiva
    START_DATE, END_DATE = configurar_fechas()
    
    # Mostrar configuración final
    logger.info(f"Rango de fechas: {START_DATE.strftime('%Y-%m-%d')} a {END_DATE.strftime('%Y-%m-%d')}")
    logger.info(f"Directorio de salida: {OUTPUT_DIR}")
    
    # Mostrar menú y ejecutar descargas
    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == '0':
            print("\n👋 ¡Hasta luego!")
            break
        
        if opcion in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14']:
            # Si la opción incluye PV Glasses, permitir seleccionar fotoceldas (opción 14 usa defaults)
            fotoceldas_seleccionadas = None
            if opcion in ['3', '4']:
                fotoceldas_seleccionadas = seleccionar_fotoceldas()
            elif opcion == '14':
                fotoceldas_seleccionadas = DEFAULT_PHOTODIODES  # descargar todo con fotoceldas por defecto
            
            ejecutar_descargas(START_DATE, END_DATE, opcion, fotoceldas_seleccionadas)
            
            # Preguntar si quiere hacer otra descarga
            continuar = input("\n¿Deseas realizar otra descarga? (s/n): ").strip().lower()
            if continuar != 's':
                print("\n👋 ¡Hasta luego!")
                break
        else:
            print("\n❌ Opción inválida. Por favor selecciona 0–14.")

