"""
Propagación de incertidumbres (GUM).

Modelo aditivo + escala para sensores:
  u(x)² = u_add² + (u_scale * x)²

Propagación para Δm (independencia m_soiled, m_clean):
  u(Δm)² = u(m_soiled)² + u(m_clean)²
"""

import numpy as np


def u_sensor(x, u_add, u_scale):
    """
    Incertidumbre estándar (k=1) de una magnitud con modelo aditivo + escala.

    u(x)² = u_add² + (u_scale * x)²

    Parámetros
    ----------
    x : float o array
        Valor(es) de la magnitud (mismas unidades que u_add).
    u_add : float
        Incertidumbre estándar aditiva (k=1), mismas unidades que x.
    u_scale : float
        Incertidumbre de escala (k=1), adimensional (ej. 0.01 = 1%).

    Returns
    -------
    float o array
        u(x) en las mismas unidades que x.
    """
    x = np.asarray(x, dtype=float)
    return np.sqrt(u_add ** 2 + (u_scale * x) ** 2)


def u_delta_m(u_m_soiled, u_m_clean):
    """
    Incertidumbre estándar de Δm = m_soiled - m_clean (masas independientes).

    u(Δm)² = u(m_soiled)² + u(m_clean)²

    Parámetros
    ----------
    u_m_soiled, u_m_clean : float o array
        Incertidumbres estándar (k=1) de cada pesada, mismas unidades.

    Returns
    -------
    float o array
        u(Δm) en las mismas unidades.
    """
    u_m_soiled = np.asarray(u_m_soiled, dtype=float)
    u_m_clean = np.asarray(u_m_clean, dtype=float)
    return np.sqrt(u_m_soiled ** 2 + u_m_clean ** 2)


def u_expanded(u_std, k=2):
    """Incertidumbre expandida U = k * u (p. ej. k=2 → ~95 %)."""
    return k * np.asarray(u_std, dtype=float)
