"""Puente entre la interfaz y el núcleo matemático (`core/`).

Este módulo NO implementa codificación, canal, decodificación ni fórmulas:
únicamente llama a las funciones públicas de `core/` y adapta sus
resultados a estructuras cómodas de presentar en pantalla (texto ↔ bits,
conteo visual de bloques, etc.).
"""

from __future__ import annotations

import contextlib
import io
import itertools
import random
from dataclasses import dataclass, field
from datetime import datetime

# `core.matematicas` imprime valores de ejemplo al importarse; se silencia
# esa salida para no ensuciar la consola de la aplicación.
with contextlib.redirect_stdout(io.StringIO()):
    from core.matematicas import (
        calcular_parametros,
        capacidad_shannon,
        entropia_binaria,
        probabilidad_error_residual,
    )
    from core.canal_bsc import transmitir_bsc
    from core.codificador import codificar_repeticion
    from core.decodificador import decodificar_repeticion
    from core.metricas import calcular_ber
    from core.simulador import simular_transmision
    from core.experimentos import ejecutar_experimentos

# Solo se ofrecen longitudes impares: el simulador del núcleo rechaza los
# empates de la decodificación por mayoría que producen las longitudes pares.
VALORES_N = tuple(range(1, 22, 2))
N_POR_DEFECTO = 5
P_POR_DEFECTO = 0.10
P_MAXIMA = 0.5
LONGITUDES_ANALISIS = (3, 5, 7)

_contador_ids = itertools.count(1)


def _nuevo_id() -> int:
    return next(_contador_ids)


def sincronizar_ids(maximo_existente: int) -> None:
    """Continúa la numeración tras el mayor id cargado (evita ids repetidos)."""
    global _contador_ids
    _contador_ids = itertools.count(max(0, int(maximo_existente)) + 1)


# ---------------------------------------------------------------------------
# Conversión texto ↔ bits (presentación)
# ---------------------------------------------------------------------------
def texto_a_bits(texto: str) -> str:
    """Representa un texto como bits (UTF‑8, 8 bits por byte)."""
    return "".join(f"{byte:08b}" for byte in texto.encode("utf-8"))


def _bytes_de_bits(bits: str) -> bytes:
    utiles = len(bits) - len(bits) % 8
    return bytes(int(bits[i:i + 8], 2) for i in range(0, utiles, 8) if "?" not in bits[i:i + 8])


def bits_a_texto(bits: str) -> str:
    """Reconstruye texto UTF‑8 a partir de bits; los bytes inválidos se marcan con �."""
    return _bytes_de_bits(bits).decode("utf-8", errors="replace")


def es_utf8_valido(bits: str) -> bool:
    """True si los bits forman una secuencia UTF‑8 estrictamente válida."""
    if len(bits) % 8 or "?" in bits:
        return False
    try:
        _bytes_de_bits(bits).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return False
    return True


def bits_aleatorios(longitud: int) -> str:
    return "".join(random.choice("01") for _ in range(longitud))


# ---------------------------------------------------------------------------
# Análisis por bloques (solo compara secuencias ya producidas por el núcleo)
# ---------------------------------------------------------------------------
def analizar_bloques(bits: str, codificado: str, recibido: str, recuperado: str,
                     n: int) -> tuple[list[int], list[bool]]:
    """Bits alterados por bloque (enviado vs recibido) y si cada bloque se decodificó bien."""
    errores = [sum(a != b for a, b in zip(codificado[i:i + n], recibido[i:i + n]))
               for i in range(0, len(codificado), n)]
    correcto = [o == r for o, r in zip(bits, recuperado)]
    return errores, correcto


# ---------------------------------------------------------------------------
# Resultado de una transmisión
# ---------------------------------------------------------------------------
@dataclass
class ResultadoTransmision:
    n: int
    p: float
    origen: str  # "chat" | "laboratorio"
    texto: str | None
    bits_originales: str
    codificado: str
    recibido: str
    recuperado: str
    recibido_sin_codigo: str
    ber_sin_codigo: float
    ber_con_codigo: float
    parametros: dict
    capacidad: float
    errores_por_bloque: list[int]
    bloque_correcto: list[bool]
    id: int = field(default_factory=_nuevo_id)
    fecha: datetime = field(default_factory=datetime.now)

    # ---- valores derivados para la vista --------------------------------
    @property
    def texto_recuperado(self) -> str | None:
        return None if self.texto is None else bits_a_texto(self.recuperado)

    @property
    def utf8_valido(self) -> bool:
        return es_utf8_valido(self.recuperado)

    @property
    def errores_canal(self) -> int:
        """Bits que el canal invirtió en la secuencia codificada."""
        return sum(self.errores_por_bloque)

    @property
    def total_bloques(self) -> int:
        return len(self.errores_por_bloque)

    @property
    def bloques_afectados(self) -> int:
        """Bloques con al menos un bit alterado por el canal."""
        return sum(1 for e in self.errores_por_bloque if e)

    @property
    def bloques_corregidos(self) -> int:
        """Bloques con errores del canal que, aun así, se decodificaron correctamente."""
        return sum(1 for e, ok in zip(self.errores_por_bloque, self.bloque_correcto) if e and ok)

    @property
    def bloques_recuperados(self) -> int:
        """Bloques decodificados correctamente (con o sin errores del canal)."""
        return sum(1 for ok in self.bloque_correcto if ok)

    @property
    def bloques_fallidos(self) -> int:
        return sum(1 for ok in self.bloque_correcto if not ok)

    @property
    def bits_erroneos(self) -> int:
        """Bits de información incorrectos tras decodificar."""
        return sum(a != b for a, b in zip(self.bits_originales, self.recuperado))

    @property
    def ber_canal(self) -> float:
        """BER antes de decodificar: bits codificados enviados vs recibidos (core.metricas)."""
        return calcular_ber(self.codificado, self.recibido)

    @property
    def error_residual_teorico(self) -> float | None:
        """Pₑ teórico de core.matematicas para (n, p); None si no es aplicable."""
        try:
            return probabilidad_error_residual(self.n, self.p)
        except ValueError:
            return None

    @property
    def exito(self) -> bool:
        return self.recuperado == self.bits_originales

    @property
    def estado(self) -> str:
        """'sin_errores' | 'corregido' | 'residual' | 'ambiguo'."""
        if "?" in self.recuperado:   # empate en la decodificación por mayoría
            return "ambiguo"
        if not self.exito:
            return "residual"
        return "corregido" if self.errores_canal else "sin_errores"

    @property
    def t(self) -> int:
        return self.parametros["errores_corregibles"]


def transmitir(bits: str, n: int, p: float, texto: str | None = None,
               origen: str = "laboratorio") -> ResultadoTransmision:
    """Ejecuta `core.simulador.simular_transmision` y empaqueta su resultado.

    Lanza las mismas excepciones (ValueError/TypeError) que el núcleo.
    """
    sim = simular_transmision(bits, n, p)
    return reconstruir(
        n=n, p=p, origen=origen, texto=texto,
        bits_originales=sim["original"], codificado=sim["codificado"],
        recibido=sim["recibido_codificado"], recuperado=sim["recuperado"],
        recibido_sin_codigo=sim["recibido_sin_codigo"],
        ber_sin_codigo=sim["ber_sin_codigo"], ber_con_codigo=sim["ber_con_codigo"])


def reconstruir(*, n: int, p: float, origen: str, texto: str | None, bits_originales: str,
                codificado: str, recibido: str, recuperado: str, recibido_sin_codigo: str,
                ber_sin_codigo: float, ber_con_codigo: float, id: int | None = None,
                fecha: datetime | None = None) -> ResultadoTransmision:
    """Crea un ResultadoTransmision a partir de secuencias ya simuladas (p. ej. al cargar JSON).

    Los parámetros y la capacidad se vuelven a pedir a `core.matematicas`.
    """
    errores, correcto = analizar_bloques(bits_originales, codificado, recibido, recuperado, n)
    extra = {}
    if id is not None:
        extra["id"] = id
    if fecha is not None:
        extra["fecha"] = fecha
    return ResultadoTransmision(
        n=n, p=p, origen=origen, texto=texto,
        bits_originales=bits_originales, codificado=codificado, recibido=recibido,
        recuperado=recuperado, recibido_sin_codigo=recibido_sin_codigo,
        ber_sin_codigo=ber_sin_codigo, ber_con_codigo=ber_con_codigo,
        parametros=calcular_parametros(n), capacidad=capacidad_shannon(p),
        errores_por_bloque=errores, bloque_correcto=correcto, **extra)


def transmitir_texto(texto: str, n: int, p: float) -> ResultadoTransmision:
    return transmitir(texto_a_bits(texto), n, p, texto=texto, origen="chat")


# ---------------------------------------------------------------------------
# Valores teóricos (todos calculados por core.matematicas)
# ---------------------------------------------------------------------------
def parametros(n: int) -> dict:
    return calcular_parametros(n)


def capacidad(p: float) -> float:
    return capacidad_shannon(p)


def entropia(p: float) -> float:
    return entropia_binaria(p)


def error_residual(n: int, p: float) -> float:
    return probabilidad_error_residual(n, p)


def curva_teorica(p: float, longitudes=VALORES_N) -> list[tuple[float, float]]:
    """Puntos (R, Pₑ) de la fórmula de error residual del núcleo."""
    return [(calcular_parametros(n)["tasa"], probabilidad_error_residual(n, p)) for n in longitudes]


def experimentos(p: float, longitud_bits: int, longitudes=LONGITUDES_ANALISIS) -> list[dict]:
    """Ejecuta `core.experimentos.ejecutar_experimentos` sobre bits aleatorios."""
    mensaje = bits_aleatorios(longitud_bits)
    return ejecutar_experimentos(mensaje, p, longitudes)


# ---------------------------------------------------------------------------
# Operaciones elementales (para el ejemplo interactivo de Teoría)
# ---------------------------------------------------------------------------
def codificar(bits: str, n: int) -> str:
    return codificar_repeticion(bits, n)


def decodificar(bits: str, n: int) -> str:
    return decodificar_repeticion(bits, n)


def canal_bsc(bits: str, p: float) -> str:
    return transmitir_bsc(bits, p)
