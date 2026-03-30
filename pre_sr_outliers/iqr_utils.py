"""Vallas de Tukey (1.5·IQR) sobre series numéricas."""

from __future__ import annotations

import numpy as np
import pandas as pd

TUKEY_K = 1.5


def tukey_outlier_mask(series: pd.Series) -> pd.Series:
    """
    True donde el valor finito está fuera de [Q1 - k·IQR, Q3 + k·IQR].
    Si IQR es 0 o no hay datos, devuelve todo False.
    """
    vals = pd.to_numeric(series, errors="coerce")
    valid = vals[np.isfinite(vals)]
    if valid.empty:
        return pd.Series(False, index=vals.index)

    q1 = float(valid.quantile(0.25))
    q3 = float(valid.quantile(0.75))
    iqr = q3 - q1
    if not np.isfinite(iqr) or abs(iqr) < 1e-12:
        return pd.Series(False, index=vals.index)

    lower = q1 - TUKEY_K * iqr
    upper = q3 + TUKEY_K * iqr
    m = (vals < lower) | (vals > upper)
    return m.fillna(False)


def mask_union_nan(df: pd.DataFrame, cols: list[str]) -> int:
    """
    Para cada columna en cols, marca outliers Tukey; en filas donde cualquier
    columna es outlier, pone NaN en todas las cols. Devuelve filas afectadas.
    """
    if not cols:
        return 0
    present = [c for c in cols if c in df.columns]
    if not present:
        return 0
    union = pd.Series(False, index=df.index)
    for c in present:
        union = union | tukey_outlier_mask(df[c])
    n = int(union.sum())
    if n:
        df.loc[union, present] = np.nan
    return n


def mask_per_column(df: pd.DataFrame, cols: list[str]) -> dict[str, int]:
    """Outliers por columna de forma independiente (solo esa celda → NaN)."""
    counts: dict[str, int] = {}
    for c in cols:
        if c not in df.columns:
            continue
        m = tukey_outlier_mask(df[c])
        n = int(m.sum())
        if n:
            df.loc[m, c] = np.nan
        counts[c] = n
    return counts


def mask_groupby_columns(
    df: pd.DataFrame, group_col: str, value_cols: list[str]
) -> dict[str, dict[str, int]]:
    """IQR dentro de cada grupo (p. ej. module) por columna numérica."""
    out: dict[str, dict[str, int]] = {}
    if group_col not in df.columns:
        return out
    for g, idx in df.groupby(group_col, dropna=False).groups.items():
        sub = df.loc[idx]
        out[str(g)] = {}
        for c in value_cols:
            if c not in sub.columns:
                continue
            m = tukey_outlier_mask(sub[c])
            n = int(m.sum())
            if n:
                df.loc[sub.index[m], c] = np.nan
            out[str(g)][c] = n
    return out
