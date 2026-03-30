"""
Colores fijos por metodología y etiquetas matplotlib (mathtext) con subíndices:
  P_max → P_mpp (subíndice mpp), I_sc (subíndice sc).

Usar en todos los gráficos SR multi-instrumento para coherencia visual y nomenclatura.
"""
from __future__ import annotations

# Orden de referencia (leyendas / ejes): alineado al pipeline de agregación semanal.
CANONICAL_INSTRUMENT_ORDER = [
    "Soiling Kit",
    "DustIQ",
    "RefCells",
    "PVStand Pmax",
    "PVStand Isc",
    "IV600 Pmax",
    "IV600 Isc",
    "PV Glasses",
]

# Soiling Kit en rojo (criterio explícito); resto estable y distinguible entre sí.
METODO_COLORS: dict[str, str] = {
    "Soiling Kit": "#D32F2F",
    "DustIQ": "#FF6F00",
    "RefCells": "#388E3C",
    "PVStand Pmax": "#1976D2",
    "PVStand Isc": "#7B1FA2",
    "IV600 Pmax": "#C2185B",
    "IV600 Isc": "#0097A7",
    "PV Glasses": "#6D4C41",
}

DEFAULT_METODO_COLOR = "#9E9E9E"

# Resolución PNG para figuras de memoria / publicación (antes 150). Usar en savefig: dpi=THESIS_FIG_DPI
THESIS_FIG_DPI = 220

# Fragmentos reutilizables en títulos (mathtext).
# \mathrm{…} en P e I evita la cursiva por defecto del modo math ($P$ → P itálica).
TITULO_IV600_PM_PP_ISC = r"IV600 $\mathrm{P}_{\mathrm{mpp}}$/$\mathrm{I}_{\mathrm{sc}}$"

# PVStand + IV600 con ambas magnitudes (P_mpp e I_sc).
TITULO_PVSTAND_E_IV600_PM_PP_ISC = (
    r"PVStand $\mathrm{P}_{\mathrm{mpp}}$/$\mathrm{I}_{\mathrm{sc}}$ e "
    r"IV600 $\mathrm{P}_{\mathrm{mpp}}$/$\mathrm{I}_{\mathrm{sc}}$"
)


def color_metodo(nombre: str) -> str:
    return METODO_COLORS.get(nombre, DEFAULT_METODO_COLOR)


def etiqueta_metodo_mathtext(nombre: str) -> str:
    """Leyendas y ticks: mathtext matplotlib."""
    if nombre == "PVStand Pmax":
        return r"PVStand $\mathrm{P}_{\mathrm{mpp}}$"
    if nombre == "PVStand Isc":
        return r"PVStand $\mathrm{I}_{\mathrm{sc}}$"
    if nombre == "IV600 Pmax":
        return r"IV600 $\mathrm{P}_{\mathrm{mpp}}$"
    if nombre == "IV600 Isc":
        return r"IV600 $\mathrm{I}_{\mathrm{sc}}$"
    return str(nombre)


def ticklabels_mathtext(nombres) -> list:
    return [etiqueta_metodo_mathtext(str(n)) for n in nombres]


def orden_instrumentos(nombres) -> list:
    """Orden estable: canonico primero, luego alfabético."""
    s = set(nombres)
    ordered = [x for x in CANONICAL_INSTRUMENT_ORDER if x in s]
    rest = sorted(s - set(ordered), key=str)
    return ordered + rest


def titulo_reemplazar_iv600_pmax_isc(texto: str) -> str:
    """Sustituye la frase literal usada en títulos por notación P_mpp / I_sc."""
    return texto.replace("IV600 Pmax/Isc", TITULO_IV600_PM_PP_ISC)


def configure_matplotlib_for_thesis():
    """
    Locale español + fuentes base más grandes para figuras de memoria / artículo.
    Los textos con fontsize explícito siguen usando ese valor; conviene subirlos
    en cada gráfico o apoyarse en estos defaults donde no se fija tamaño.
    """
    import matplotlib.pyplot as plt

    plt.rcParams["axes.formatter.use_locale"] = True
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.titlesize": 15,
            "axes.labelsize": 14,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "legend.fontsize": 12,
            "figure.titlesize": 15,
        }
    )
