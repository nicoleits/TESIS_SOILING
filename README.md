# si_test

Este directorio es **un único repositorio Git**: el código de `TESIS_SOILING/` y el resto del proyecto se versionan juntos. En `.gitignore` se excluyen entornos virtuales (`.venv/`, etc.), datos tabulares e imágenes (`*.csv`, `*.png`, …), y otros artefactos pesados listados en ese fichero. El historial del antiguo repo anidado de `TESIS_SOILING`, si existía, queda respaldado bajo `_git_backups/` (no se sube a Git).

## Entorno Python

Los archivos `*.txt` no se versionan en este repositorio (incluido un hipotético `requirements.txt`). Para instalar dependencias usa el fichero **`requirements.pip`**, que sí está en Git.

### Crear un entorno virtual (recomendado)

Desde la raíz del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows (cmd/PowerShell)
```

### Instalar dependencias

```bash
pip install -r requirements.pip
```

Si prefieres no activar el venv, puedes invocar el intérprete directamente, por ejemplo:

```bash
.venv/bin/python run_tesis_pre_sr_iqr.py --solo-sr
```

### Añadir paquetes nuevos

1. Instálalos con `pip install nombre_paquete`.
2. Actualiza **`requirements.pip`** con la nueva línea (nombre y, si hace falta, versión fija).
3. Haz commit de `requirements.pip` para que el resto del equipo reproduzca el mismo entorno.
