"""
Configuración común del análisis: periodo de estudio (1 año).

Usado por agregación semanal, gráficos de intercomparación y otros análisis
para limitar los datos al intervalo 01/08/2024 - 01/08/2025.
"""
# Periodo de análisis: 03 ago 2024 — 04 ago 2025 (sin 2 primeros ni 4 últimos días)
PERIODO_ANALISIS_INICIO = "2024-08-03"
PERIODO_ANALISIS_FIN = "2025-08-04"

# RefCells: corte 4 días antes (resto hasta PERIODO_ANALISIS_FIN)
REFCELLS_FECHA_MAX = "2025-05-20"
