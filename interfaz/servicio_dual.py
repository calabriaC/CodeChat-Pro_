"""Servicio del «Chat Dual»: comunicación bidireccional A ⇄ B por el canal BSC.

No implementa codificación, canal, decodificación ni fórmulas. Cada mensaje se
transmite con `core.simulador.simular_transmision` (a través de `servicio`) y
los valores teóricos se piden a `core.matematicas`. Aquí solo se guardan los
resultados de la conversación y se cuentan/comparan secuencias ya producidas.

La conversación se guarda en su propio archivo JSON (independiente del
Historial general) con el mismo formato de registro que `persistencia`.
"""

from __future__ import annotations

import itertools
import json
import random
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from interfaz import persistencia, servicio
from interfaz.estilos import C
from interfaz.servicio import ResultadoTransmision, simular_transmision

USUARIOS = ("A", "B")
NOMBRES = {"A": "Usuario A", "B": "Usuario B"}
LONGITUDES_DUAL = (3, 5, 7)
N_INICIAL = 3
P_INICIAL = servicio.P_POR_DEFECTO
LONGITUD_MAXIMA = 500
SEMILLA_INICIAL = 2026

FORMATO = "codechat-pro/chat-dual"
VERSION = 1
NOMBRE_ARCHIVO = "chat_dual.json"
CARPETA_ARCHIVO = "chat_dual_archivadas"


def receptor_de(emisor: str) -> str:
    if emisor not in USUARIOS:
        raise ValueError(f"Emisor desconocido: {emisor!r}")
    return "B" if emisor == "A" else "A"


# ---------------------------------------------------------------------------
# Estado de recepción (depende solo del resultado real)
# ---------------------------------------------------------------------------
# clave → (texto para el receptor, texto para el emisor, color, icono, explicación)
ESTADOS_DUAL = {
    "correcto": ("Recuperado correctamente", "Entregado correctamente", C.VERDE, "exito",
                 "El texto recuperado coincide bit a bit con el enviado."),
    "con_errores": ("Recibido con errores", "Entregado con errores", C.AMBAR, "alerta",
                    "El texto es UTF‑8 válido, pero quedaron errores residuales tras la decodificación."),
    "no_reconstruible": ("No reconstruible como texto", "Llegó ilegible", C.ERROR, "fallo",
                         "Los bytes recuperados no forman UTF‑8 válido."),
    "empate": ("Empate en la decodificación", "Llegó con empates", C.MORADO, "alerta",
               "Algunos bloques tuvieron tantos unos como ceros («?»): no hay mayoría."),
}


def estado_dual(r: ResultadoTransmision) -> str:
    if r.hay_empates:
        return "empate"
    if r.exito:
        return "correcto"
    if not r.utf8_valido:
        return "no_reconstruible"
    return "con_errores"


def texto_visible(texto: str) -> str:
    """Hace visibles los caracteres de control que el ruido pueda producir (␀, ␇…)."""
    return "".join(chr(0x2400 + ord(c)) if ord(c) < 32 and c not in "\n\t"
                   else ("␡" if ord(c) == 127 else c) for c in texto)


@dataclass
class MensajeDual:
    """Un mensaje de la conversación con el resultado real de su transmisión."""

    numero: int
    emisor: str
    receptor: str
    resultado: ResultadoTransmision      # incluye la copia de n, p, parámetros y C usados
    fecha: datetime = field(default_factory=datetime.now)

    # ---- atajos de lectura (solo comparan secuencias del núcleo) ----------
    @property
    def texto_original(self) -> str:
        return self.resultado.texto or ""

    @property
    def caracteres(self) -> int:
        return len(self.texto_original)

    @property
    def bytes_utf8(self) -> int:
        return len(self.texto_original.encode("utf-8"))

    @property
    def estado(self) -> str:
        return estado_dual(self.resultado)

    @property
    def texto_recuperado(self) -> str | None:
        """Texto reconstruido desde los bits recuperados; None si hay empates ('?')."""
        return self.resultado.texto_recuperado

    @property
    def texto_recuperado_visual(self) -> str | None:
        """Representación segura: «�» = byte no decodificable; ␀, ␇… = controles."""
        t = self.texto_recuperado
        return None if t is None else texto_visible(t)

    @property
    def bytes_recuperados_hex(self) -> str:
        """Bytes recuperados en hexadecimal ('??' si el byte contiene empates)."""
        bits = self.resultado.recuperado
        return " ".join("??" if "?" in bits[i:i + 8] else f"{int(bits[i:i + 8], 2):02X}"
                        for i in range(0, len(bits) - len(bits) % 8, 8))

    @property
    def posiciones_error(self) -> list[int]:
        """Posiciones (desde 1) de los bits codificados que el canal invirtió."""
        r = self.resultado
        return [i + 1 for i, (a, b) in enumerate(zip(r.codificado, r.recibido)) if a != b]

    @property
    def posiciones_residuales(self) -> list[int]:
        """Posiciones (desde 1) de los bits de información decididos incorrectamente."""
        r = self.resultado
        return [i + 1 for i, (a, b) in enumerate(zip(r.bits_originales, r.recuperado))
                if b != "?" and a != b]

    @property
    def posiciones_empate(self) -> list[int]:
        return [i + 1 for i, b in enumerate(self.resultado.recuperado) if b == "?"]


@dataclass
class MetricasAcumuladas:
    """Totales de la conversación. Las tasas se calculan sumando conteos, nunca
    promediando las tasas de cada mensaje (eso ponderaría igual a mensajes cortos y largos)."""

    mensajes: int = 0
    enviados_a: int = 0
    enviados_b: int = 0
    bits_originales: int = 0
    bits_codificados: int = 0
    errores_canal: int = 0
    errores_residuales: int = 0
    empates: int = 0
    bits_decididos: int = 0
    configuraciones: set = field(default_factory=set)   # {(n, p)} usadas

    @property
    def ber_residual(self) -> float | None:
        """Σ errores residuales / Σ bits decididos (None si no hay bits decididos)."""
        return self.errores_residuales / self.bits_decididos if self.bits_decididos else None

    @property
    def ber_canal(self) -> float | None:
        """Σ bits invertidos por el canal / Σ bits transmitidos."""
        return self.errores_canal / self.bits_codificados if self.bits_codificados else None

    @property
    def tasa_efectiva(self) -> float | None:
        """Σ bits de información / Σ bits transmitidos (coincide con 1/n si n no cambió)."""
        return self.bits_originales / self.bits_codificados if self.bits_codificados else None


def _transmitir(texto: str, n: int, p: float, id_: int, origen: str = "chat_dual") -> ResultadoTransmision:
    bits = servicio.texto_a_bits(texto)
    sim = simular_transmision(bits, n, p)          # núcleo matemático (core/)
    return servicio.reconstruir(
        n=n, p=p, origen=origen, texto=texto,
        bits_originales=sim["original"], codificado=sim["codificado"],
        recibido=sim["recibido_codificado"], recuperado=sim["recuperado"],
        recibido_sin_codigo=sim["recibido_sin_codigo"],
        ber_sin_codigo=sim["ber_sin_codigo"], ber_con_codigo=sim["ber_con_codigo"],
        id=id_,   # numeración propia: no consume los ids del Historial general
        metricas_simulador={c: sim[c] for c in
                            ("empates", "bits_decididos", "tasa_empates", "errores_residuales")
                            if c in sim})


def validar_texto(texto: str) -> None:
    if not texto or not texto.strip():
        raise ValueError("El mensaje está vacío.")
    if len(texto) > LONGITUD_MAXIMA:
        raise ValueError(f"El mensaje supera los {LONGITUD_MAXIMA} caracteres.")


class ConversacionDual:
    """Conversación entre A y B. Cada envío es una transmisión independiente."""

    def __init__(self, mensajes: list[MensajeDual] | None = None):
        self.mensajes: list[MensajeDual] = list(mensajes or [])
        self._continuar_numeracion()

    def _continuar_numeracion(self) -> None:
        ultimo = max((m.numero for m in self.mensajes), default=0)
        ultimo_id = max((m.resultado.id for m in self.mensajes), default=0)
        self._numeros = itertools.count(ultimo + 1)
        self._ids = itertools.count(ultimo_id + 1)

    def enviar(self, emisor: str, texto: str, n: int, p: float) -> MensajeDual:
        """Transmite `texto` de `emisor` a su interlocutor con los parámetros (n, p).

        Lanza ValueError si el texto está vacío o si el núcleo rechaza n o p.
        """
        receptor = receptor_de(emisor)
        validar_texto(texto)
        r = _transmitir(texto, n, p, next(self._ids))
        mensaje = MensajeDual(next(self._numeros), emisor, receptor, r, fecha=r.fecha)
        self.mensajes.append(mensaje)
        return mensaje

    def limpiar(self) -> None:
        self.mensajes.clear()
        self._continuar_numeracion()

    def enviados_por(self, usuario: str) -> int:
        return sum(1 for m in self.mensajes if m.emisor == usuario)

    def recibidos_por(self, usuario: str) -> int:
        return sum(1 for m in self.mensajes if m.receptor == usuario)

    def metricas(self) -> MetricasAcumuladas:
        m = MetricasAcumuladas()
        for msj in self.mensajes:
            r = msj.resultado
            m.mensajes += 1
            m.enviados_a += msj.emisor == "A"
            m.enviados_b += msj.emisor == "B"
            m.bits_originales += len(r.bits_originales)
            m.bits_codificados += len(r.codificado)
            m.errores_canal += r.errores_canal
            m.errores_residuales += r.errores_residuales
            m.empates += r.empates
            m.bits_decididos += r.bits_decididos
            m.configuraciones.add((r.n, r.p))
        return m


# ---------------------------------------------------------------------------
# Comparación de códigos (mismo mensaje y misma p para n = 3, 5, 7)
# ---------------------------------------------------------------------------
def comparar_codigos(texto: str, p: float, semilla: int | None,
                     longitudes=LONGITUDES_DUAL) -> list[ResultadoTransmision]:
    """Transmite el mismo texto con cada n. Con `semilla`, el ruido es reproducible.

    `core.canal_bsc` usa el módulo `random`; se siembra temporalmente y después se
    restaura su estado, para no alterar el resto de la aplicación.
    """
    validar_texto(texto)
    estado = random.getstate()
    try:
        resultados = []
        for i, n in enumerate(longitudes, 1):
            if semilla is not None:
                random.seed(f"{semilla}-{n}")   # cada n tiene su propia secuencia reproducible
            resultados.append(_transmitir(texto, n, p, i, origen="chat_dual"))
        return resultados
    finally:
        random.setstate(estado)


# ---------------------------------------------------------------------------
# Persistencia local de la conversación (archivo propio)
# ---------------------------------------------------------------------------
def ruta_por_defecto() -> Path:
    return persistencia.directorio_datos() / NOMBRE_ARCHIVO


def _a_dict(m: MensajeDual) -> dict:
    return {"numero": m.numero, "emisor": m.emisor, "receptor": m.receptor,
            "fecha": m.fecha.isoformat(timespec="seconds"),
            "transmision": persistencia.a_dict(m.resultado, incluir_contenido=True)}


def _desde_dict(d: dict) -> MensajeDual:
    if not isinstance(d, dict):
        raise ValueError("el mensaje no es un objeto JSON")
    emisor, receptor = d.get("emisor"), d.get("receptor")
    if emisor not in USUARIOS or receptor != receptor_de(emisor):
        raise ValueError("emisor/receptor inválidos")
    numero = d.get("numero")
    if isinstance(numero, bool) or not isinstance(numero, int):
        raise ValueError("número de mensaje inválido")
    crudo = dict(d.get("transmision") or {})
    if crudo.get("origen") != "chat_dual":
        raise ValueError("la transmisión no pertenece al Chat Dual")
    # Se reutiliza la validación del historial general (que solo conoce sus orígenes).
    crudo["origen"] = "chat"
    r = persistencia.desde_dict(crudo)
    r.origen = "chat_dual"
    if r.texto is None:
        raise ValueError("el mensaje no contiene texto")
    return MensajeDual(numero, emisor, receptor, r, fecha=datetime.fromisoformat(d["fecha"]))


class AlmacenChatDual:
    """Guarda la conversación activa; «Nueva conversación» la archiva, no la borra."""

    def __init__(self, ruta: Path | None = None):
        self.ruta = Path(ruta) if ruta else ruta_por_defecto()

    def cargar(self) -> tuple[list[MensajeDual], str | None]:
        """(mensajes, aviso). Si el archivo está dañado se conserva una copia y se empieza vacío."""
        if not self.ruta.exists():
            return [], None
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
                raise ValueError("no es una conversación del Chat Dual")
            if not isinstance(datos.get("version"), int) or datos["version"] > VERSION:
                raise ValueError("versión de formato no soportada")
            crudos = datos.get("mensajes")
            if not isinstance(crudos, list):
                raise ValueError("el campo «mensajes» no es una lista")
            mensajes = [_desde_dict(c) for c in crudos]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            copia = self.ruta.with_name(f"chat_dual.danado-{datetime.now():%Y%m%d-%H%M%S}.json")
            try:
                shutil.copy2(self.ruta, copia)
                donde = f"\n\nSe conservó una copia en:\n{copia}"
            except OSError:
                donde = ""
            return [], f"No se pudo leer la conversación guardada del Chat Dual ({e}).{donde}"
        mensajes.sort(key=lambda m: (m.fecha, m.numero))
        return mensajes, None

    def _documento(self, mensajes) -> dict:
        return {"formato": FORMATO, "version": VERSION,
                "generado": datetime.now().isoformat(timespec="seconds"),
                "mensajes": [_a_dict(m) for m in mensajes]}

    def guardar(self, mensajes) -> None:
        persistencia.escribir_json(self.ruta, self._documento(mensajes))

    def archivar(self, mensajes) -> Path | None:
        """Copia la conversación a la carpeta de archivadas y deja la activa vacía."""
        destino = None
        if mensajes:
            destino = self.ruta.parent / CARPETA_ARCHIVO / f"conversacion-{datetime.now():%Y%m%d-%H%M%S}.json"
            persistencia.escribir_json(destino, self._documento(mensajes))
        self.guardar([])
        return destino
