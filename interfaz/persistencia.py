"""Persistencia local del historial en JSON (sin servicios externos ni telemetría).

Formato versionado:

    {
      "formato": "codechat-pro/historial",
      "version": 1,
      "generado": "2026-11-15T14:32:00",
      "incluye_contenido": true,
      "registros": [ {...}, ... ]
    }

Los registros completos guardan las secuencias necesarias para reconstruir
los detalles de transmisión; los parámetros del código y la capacidad se
recalculan con `core.matematicas` al cargarlos.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from interfaz import servicio

FORMATO = "codechat-pro/historial"
VERSION = 1
NOMBRE_ARCHIVO = "historial.json"


class ErrorHistorial(Exception):
    """El archivo de historial existe pero no se pudo leer o validar."""


# ---------------------------------------------------------------------------
# Ubicación
# ---------------------------------------------------------------------------
def directorio_datos() -> Path:
    """Directorio de datos de la aplicación, estable y escribible por el usuario."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "CodeChatPro"


def ruta_historial() -> Path:
    return directorio_datos() / NOMBRE_ARCHIVO


# ---------------------------------------------------------------------------
# Conversión registro ↔ dict
# ---------------------------------------------------------------------------
_CAMPOS_TEXTO = ("bits_originales", "codificado", "recibido", "recuperado", "recibido_sin_codigo")


def a_dict(r: servicio.ResultadoTransmision, incluir_contenido: bool = True) -> dict:
    """Serializa un resultado. Sin contenido: solo parámetros y métricas."""
    d = {
        "id": r.id,
        "fecha": r.fecha.isoformat(timespec="seconds"),
        "origen": r.origen,
        "n": r.n,
        "p": r.p,
        "ber_sin_codigo": r.ber_sin_codigo,
        "ber_con_codigo": r.ber_con_codigo,
    }
    if incluir_contenido:
        d["texto"] = r.texto
        for campo in _CAMPOS_TEXTO:
            d[campo] = getattr(r, campo)
    else:
        d.update({
            "es_texto": r.texto is not None,
            "bits_informacion": len(r.bits_originales),
            "bits_transmitidos": len(r.codificado),
            "bits_alterados_canal": r.errores_canal,
            "bits_erroneos_tras_decodificar": r.bits_erroneos,
            "ber_canal": r.ber_canal,
            "bloques_totales": r.total_bloques,
            "bloques_afectados": r.bloques_afectados,
            "bloques_con_errores_corregidos": r.bloques_corregidos,
            "bloques_fallidos": r.bloques_fallidos,
            "estado": r.estado,
            "empates": r.empates,
            "bits_decididos": r.bits_decididos,
            "tasa_empates": r.tasa_empates,
            "t": r.t,
            "tasa": r.parametros["tasa"],
            "capacidad_shannon": r.capacidad,
            "error_residual_teorico": r.error_residual_teorico,
        })
    return d


def _exigir(d: dict, clave: str, tipos) -> object:
    if clave not in d:
        raise ValueError(f"falta el campo «{clave}»")
    valor = d[clave]
    # bool es subclase de int en Python: no se acepta como número.
    if isinstance(valor, bool) or not isinstance(valor, tipos):
        raise ValueError(f"el campo «{clave}» tiene un tipo inválido")
    return valor


def desde_dict(d: dict) -> servicio.ResultadoTransmision:
    """Reconstruye un resultado completo con tipos correctos. Lanza ValueError si no es válido."""
    if not isinstance(d, dict):
        raise ValueError("el registro no es un objeto JSON")
    texto = d.get("texto")
    if texto is not None and not isinstance(texto, str):
        raise ValueError("el campo «texto» tiene un tipo inválido")
    secuencias = {c: _exigir(d, c, str) for c in _CAMPOS_TEXTO}
    for nombre, valor in secuencias.items():
        if any(b not in "01?" for b in valor):
            raise ValueError(f"«{nombre}» contiene símbolos no binarios")
    n = _exigir(d, "n", int)
    if n not in servicio.VALORES_N:
        raise ValueError(f"n = {n} no es una longitud soportada")
    p = float(_exigir(d, "p", (int, float)))
    if not 0 <= p <= servicio.P_MAXIMA:
        raise ValueError(f"p = {p} fuera de rango")
    if len(secuencias["codificado"]) != len(secuencias["bits_originales"]) * n:
        raise ValueError("las longitudes de las secuencias no son coherentes")
    origen = _exigir(d, "origen", str)
    if origen not in ("chat", "laboratorio"):
        raise ValueError(f"origen desconocido: {origen}")
    try:
        fecha = datetime.fromisoformat(_exigir(d, "fecha", str))
    except ValueError as e:
        raise ValueError("fecha con formato inválido") from e
    return servicio.reconstruir(
        n=n, p=p, origen=origen, texto=texto,
        ber_sin_codigo=float(_exigir(d, "ber_sin_codigo", (int, float))),
        ber_con_codigo=(None if d.get("ber_con_codigo", 0) is None
                        else float(_exigir(d, "ber_con_codigo", (int, float)))),
        id=_exigir(d, "id", int), fecha=fecha, **secuencias)


def documento(registros, incluir_contenido: bool = True) -> dict:
    return {
        "formato": FORMATO,
        "version": VERSION,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "incluye_contenido": incluir_contenido,
        "registros": [a_dict(r, incluir_contenido) for r in registros],
    }


# ---------------------------------------------------------------------------
# Lectura / escritura
# ---------------------------------------------------------------------------
def escribir_json(ruta: Path, datos: dict) -> None:
    """Escritura atómica en UTF‑8 (archivo temporal + reemplazo)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=ruta.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporal)
        raise


class AlmacenHistorial:
    """Guarda y carga el historial en un único archivo JSON."""

    def __init__(self, ruta: Path | None = None):
        self.ruta = Path(ruta) if ruta else ruta_historial()

    def cargar(self) -> list[servicio.ResultadoTransmision]:
        """Devuelve los registros guardados ([] si no hay archivo).

        Si el archivo está dañado lanza ErrorHistorial tras dejar una copia de
        seguridad intacta junto al original; nunca lo borra.
        """
        if not self.ruta.exists():
            return []
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
                raise ValueError("no es un archivo de historial de CodeChat Pro")
            if not isinstance(datos.get("version"), int) or datos["version"] > VERSION:
                raise ValueError(f"versión de formato no soportada: {datos.get('version')}")
            if datos.get("incluye_contenido") is False:
                raise ValueError("el archivo solo contiene métricas y no puede reconstruirse")
            crudos = datos.get("registros")
            if not isinstance(crudos, list):
                raise ValueError("el campo «registros» no es una lista")
            registros, vistos = [], set()
            for i, crudo in enumerate(crudos, 1):
                try:
                    r = desde_dict(crudo)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"registro {i}: {e}") from e
                if r.id in vistos:        # evita duplicados
                    continue
                vistos.add(r.id)
                registros.append(r)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
            copia = self._respaldar()
            mensaje = f"No se pudo leer el historial guardado ({e})."
            if copia:
                mensaje += f"\n\nSe conservó una copia del archivo original en:\n{copia}"
            raise ErrorHistorial(mensaje) from e
        registros.sort(key=lambda r: (r.fecha, r.id))
        return registros

    def _respaldar(self) -> Path | None:
        sello = datetime.now().strftime("%Y%m%d-%H%M%S")
        copia = self.ruta.with_name(f"historial.danado-{sello}.json")
        try:
            shutil.copy2(self.ruta, copia)
            return copia
        except OSError:
            return None

    def guardar(self, registros) -> None:
        escribir_json(self.ruta, documento(registros, incluir_contenido=True))

    def borrar(self) -> None:
        """Elimina los registros del almacenamiento persistente."""
        escribir_json(self.ruta, documento([], incluir_contenido=True))


def exportar(ruta: Path, registros, incluir_contenido: bool = True) -> int:
    """Exporta una copia del historial; devuelve el número de registros escritos."""
    datos = documento(registros, incluir_contenido)
    escribir_json(Path(ruta), datos)
    return len(datos["registros"])
