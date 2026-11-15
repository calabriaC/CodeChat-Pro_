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


# ---------------------------------------------------------------------------
# Conversión texto ↔ bits (presentación)
# ---------------------------------------------------------------------------
def texto_a_bits(texto: str) -> str:
    """Representa un texto como bits (UTF‑8, 8 bits por byte)."""
    return "".join(f"{byte:08b}" for byte in texto.encode("utf-8"))


def bits_a_texto(bits: str) -> str:
    """Reconstruye texto UTF‑8 a partir de bits; los bytes inválidos se marcan con �."""
    utiles = len(bits) - len(bits) % 8
    datos = bytes(int(bits[i:i + 8], 2) for i in range(0, utiles, 8) if "?" not in bits[i:i + 8])
    return datos.decode("utf-8", errors="replace")


def bits_aleatorios(longitud: int) -> str:
    return "".join(random.choice("01") for _ in range(longitud))


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
    id: int = field(default_factory=lambda: next(_contador_ids))
    fecha: datetime = field(default_factory=datetime.now)

    # ---- valores derivados para la vista --------------------------------
    @property
    def texto_recuperado(self) -> str | None:
        return None if self.texto is None else bits_a_texto(self.recuperado)

    @property
    def errores_canal(self) -> int:
        return sum(self.errores_por_bloque)

    @property
    def total_bloques(self) -> int:
        return len(self.errores_por_bloque)

    @property
    def bloques_corregidos(self) -> int:
        return sum(1 for e, ok in zip(self.errores_por_bloque, self.bloque_correcto) if e and ok)

    @property
    def bloques_fallidos(self) -> int:
        return sum(1 for ok in self.bloque_correcto if not ok)

    @property
    def bits_erroneos(self) -> int:
        return sum(a != b for a, b in zip(self.bits_originales, self.recuperado))

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
    codificado = sim["codificado"]
    recibido = sim["recibido_codificado"]
    recuperado = sim["recuperado"]

    errores_por_bloque = [
        sum(a != b for a, b in zip(codificado[i:i + n], recibido[i:i + n]))
        for i in range(0, len(codificado), n)
    ]
    bloque_correcto = [o == r for o, r in zip(bits, recuperado)]

    return ResultadoTransmision(
        n=n,
        p=p,
        origen=origen,
        texto=texto,
        bits_originales=sim["original"],
        codificado=codificado,
        recibido=recibido,
        recuperado=recuperado,
        recibido_sin_codigo=sim["recibido_sin_codigo"],
        ber_sin_codigo=sim["ber_sin_codigo"],
        ber_con_codigo=sim["ber_con_codigo"],
        parametros=calcular_parametros(n),
        capacidad=capacidad_shannon(p),
        errores_por_bloque=errores_por_bloque,
        bloque_correcto=bloque_correcto,
    )


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
