"""Vista «Chat Dual»: dos usuarios (A y B) conversan a través del canal BSC.

Cada envío se transmite con el núcleo matemático (ver `servicio_dual`): el receptor
ve solo lo que realmente recuperó la decodificación por mayoría. Este módulo es
presentación: no calcula BER, capacidades ni decodifica nada por su cuenta.
"""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpinBox, QToolTip, QVBoxLayout, QWidget,
)

from interfaz import servicio, servicio_dual
from interfaz.componentes import (
    AreaDesplazable, ControlProbabilidad, ControlSegmentado, DialogoDetalle, EncabezadoPagina,
    FlujoLayout, VisorBits, boton_copiar, etiqueta, formato_ber, formato_p, icono_label, repulir,
    separador, texto_ajustable,
)
from interfaz.estilos import PILA_MONO, C, fuente, fuente_mono, qcolor, rgba
from interfaz.grafica import GraficaBarras
from interfaz.iconos import icono
from interfaz.marcos import PanelTecnico
from interfaz.marcos_globales import PanelSecundario
from interfaz.servicio_dual import ESTADOS_DUAL, NOMBRES, ConversacionDual, MensajeDual
from interfaz.vista_chat import Conversacion, EntradaMensaje, _ConTextoAjustable

# Identidad de cada usuario: (color principal, color secundario, degradado de su burbuja)
COLORES = {
    "A": (C.AZUL_ELECTRICO, C.AZUL, ("#1767D8", "#0B3577")),
    "B": (C.ROJO, C.ROJO_CLARO, ("#C42A3D", "#6A1424")),
}
# Colores de la visualización de bits (según el significado de cada etapa)
COLOR_ORIGINAL = C.AZUL_ELECTRICO
COLOR_CODIFICADO = C.AZUL
COLOR_RUIDO = C.ROJO
COLOR_RECUPERADO = C.VERDE
COLOR_RESIDUAL = C.AMBAR

ANCHO_CONTROL = 300
BITS_POR_PAGINA = 8           # una página del inspector de bloques = 1 byte
MAX_BITS_VISOR = 4096
MAX_POSICIONES = 80
NO_DISPONIBLE = "No disponible"


# ===========================================================================
# Utilidades de presentación
# ===========================================================================
def _html_bits(bits: str, referencia: str | None = None, color: str = C.TEXTO,
               color_distinto: str = COLOR_RUIDO, fondo_distinto: str = "#4A1222",
               color_igual: str | None = None, bloque: int | None = None,
               max_bits: int = MAX_BITS_VISOR) -> str:
    """Secuencia binaria en HTML agrupada por bloques; colorea los bits que difieren."""
    partes: list[str] = []
    tramo: list[str] = []
    estilo_tramo: str | None = None

    def volcar():
        if tramo:
            partes.append(f'<span style="{estilo_tramo}">{"".join(tramo)}</span>')
            tramo.clear()

    for i, b in enumerate(bits[:max_bits]):
        if bloque and i and i % bloque == 0:
            volcar()
            partes.append(" ")
        if b == "?":
            estilo = f"color:{COLOR_RESIDUAL}; background-color:#3D2E12; font-weight:700;"
        elif referencia is not None and i < len(referencia) and referencia[i] != b:
            estilo = f"color:{color_distinto}; background-color:{fondo_distinto}; font-weight:700;"
        else:
            estilo = f"color:{color_igual if (color_igual and referencia is not None) else color};"
        if estilo != estilo_tramo:
            volcar()
            estilo_tramo = estilo
        tramo.append(b)
    volcar()
    if len(bits) > max_bits:
        partes.append(f' <span style="color:{C.TEXTO_TENUE};">… +{len(bits) - max_bits} bits '
                      f'(ver «Secuencias completas»)</span>')
    return "".join(partes)


def _visor(html_bits: str, lineas: int = 4) -> VisorBits:
    v = VisorBits(lineas)
    v.setHtml(f'<div>{html_bits}</div>')
    return v


def _posiciones(lista: list[int]) -> str:
    if not lista:
        return "ninguna"
    texto = ", ".join(map(str, lista[:MAX_POSICIONES]))
    if len(lista) > MAX_POSICIONES:
        texto += f" … (+{len(lista) - MAX_POSICIONES} más)"
    return texto


def _byte_legible(bits8: str) -> str:
    """'0x6C «l»' para un byte; solo informa el carácter si es ASCII imprimible."""
    if len(bits8) < 8 or "?" in bits8:
        return "byte con empates (?)"
    valor = int(bits8, 2)
    car = f" «{chr(valor)}»" if 32 <= valor < 127 else (" (byte de un carácter UTF‑8)"
                                                         if valor >= 128 else " (control)")
    return f"0x{valor:02X}{car}"


# Etiquetas que distinguen el origen de cada valor del inspector
_TIPOS_VALOR = {
    "dato": ("DATO", C.TEXTO_SECUNDARIO, "Dato de entrada de esta transmisión"),
    "codigo": ("CÓDIGO", C.AZUL, "Propiedad del código de repetición (core.matematicas)"),
    "canal": ("CANAL", C.ROJO_CLARO, "Parámetro del canal usado en esta transmisión"),
    "medido": ("SIMULACIÓN", C.VERDE, "Obtenido en esta transmisión concreta (resultado aleatorio)"),
    "teorico": ("TEÓRICO", C.MORADO, "Valor teórico calculado por core.matematicas, no una medición"),
}


def _etiqueta_tipo(tipo: str) -> QLabel:
    texto, color, ayuda = _TIPOS_VALOR[tipo]
    lbl = QLabel(texto)
    lbl.setObjectName("Pildora")
    lbl.setProperty("acento", color)
    lbl.setToolTip(ayuda)
    lbl.setStyleSheet(f"color: {color}; background: {rgba(color, 0.10)}; border: 1px solid {rgba(color, 0.35)};"
                      " border-radius: 4px; padding: 1px 5px; font-size: 9px; font-weight: 700;"
                      " letter-spacing: 0.6px;")
    lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return lbl


class _Avatar(QLabel):
    def __init__(self, usuario: str, lado: int = 38, parent=None):
        super().__init__(usuario, parent)
        color = COLORES[usuario][0]
        self.setFixedSize(lado, lado)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip(NOMBRES[usuario])
        self.setStyleSheet(f"background: {rgba(color, 0.16)}; border: 1px solid {rgba(color, 0.75)};"
                           f" border-radius: {lado // 2}px; color: {COLORES[usuario][1]};"
                           f" font-size: {int(lado * 0.42)}px; font-weight: 800;")


_CORTOS = {  # versión compacta para burbujas estrechas: (receptor, emisor)
    "correcto": ("Correcto", "Entregado"),
    "con_errores": ("Con errores", "Con errores"),
    "no_reconstruible": ("Ilegible", "Ilegible"),
    "empate": ("Empate", "Con empates"),
}


class IndicadorEstado(QWidget):
    """Punto de color + texto del estado de recepción (corto en las burbujas)."""

    def __init__(self, estado: str, propio: bool, compacto: bool = False, parent=None):
        super().__init__(parent)
        receptor, emisor, color, _ic, explicacion = ESTADOS_DUAL[estado]
        if compacto:
            receptor, emisor = _CORTOS[estado]
            explicacion = f"{ESTADOS_DUAL[estado][1 if propio else 0]}: {explicacion}"
        self.estado = estado
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(6)
        punto = QLabel()
        punto.setFixedSize(9, 9)
        punto.setStyleSheet(f"background: {color}; border-radius: 4px;")
        fila.addWidget(punto, 0, Qt.AlignmentFlag.AlignVCenter)
        self.texto = etiqueta(emisor if propio else receptor)
        self.texto.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        fila.addWidget(self.texto)
        self.setToolTip(explicacion)


# ===========================================================================
# Burbujas
# ===========================================================================
class BurbujaDual(_ConTextoAjustable, QFrame):
    """Mensaje limpio: emisor, texto, hora, estado compacto y «Ver detalles».

    `propio=True`: lo escribió el dueño del panel (se muestra el texto que envió).
    `propio=False`: lo recibió (se muestra SOLO lo que recuperó la decodificación).
    Los detalles matemáticos viven en el inspector, no en la burbuja.
    """

    detalles_pedidos = Signal(object)

    def __init__(self, m: MensajeDual, propio: bool, parent=None):
        super().__init__(parent)
        self.m = m
        r = m.resultado
        color, color_claro, (g1, g2) = COLORES[m.emisor]
        self.setObjectName("BurbujaDual")
        self.setProperty("acento", color)
        self.setProperty("propio", propio)
        if propio:
            self.setStyleSheet(f"QFrame#BurbujaDual {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                               f" stop:0 {g1}, stop:1 {g2}); border: 1px solid {rgba(color_claro, 0.7)};"
                               f" border-radius: 12px; }}")
        else:
            self.setStyleSheet(f"QFrame#BurbujaDual {{ background: {C.SUPERFICIE};"
                               f" border: 1px solid {rgba(color, 0.45)}; border-left: 3px solid {color};"
                               f" border-radius: 10px; }}")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(14, 10, 12, 10)
        caja.setSpacing(6)

        # Emisor y hora (los parámetros quedan en el tooltip)
        cab = QHBoxLayout()
        cab.setSpacing(8)
        nombre = etiqueta(NOMBRES[m.emisor], "Etiqueta")
        nombre.setStyleSheet(f"color: {rgba(C.TEXTO, 0.92) if propio else color_claro};"
                             " font-size: 12px; font-weight: 700;")
        cab.addWidget(nombre)
        cab.addStretch(1)
        hora = etiqueta(f"{m.fecha:%H:%M}", "HoraBurbuja")
        hora.setToolTip(f"Mensaje #{m.numero} · {m.fecha:%d/%m/%Y %H:%M:%S}\n"
                        f"Canal usado: n = {r.n} · p = {formato_p(r.p)}")
        cab.addWidget(hora)
        caja.addLayout(cab)

        # Texto: el original para el emisor; el recuperado para el receptor
        visual = m.texto_original if propio else m.texto_recuperado_visual
        if visual is None:
            self._texto_plano = f"[texto no reconstruible: {r.empates} bit(s) empatados]"
        else:
            self._texto_plano = visual
        self._lbl = etiqueta(texto_ajustable(self._texto_plano), "TextoBurbuja", ajustar=True)
        self._lbl.setTextFormat(Qt.TextFormat.PlainText)
        self._lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if visual is None:
            self._lbl.setStyleSheet(f"color: {C.MORADO}; font-style: italic;")
        caja.addWidget(self._lbl)
        if not propio and m.estado == "no_reconstruible":
            nota = etiqueta("Visualización segura: «�» marca bytes no decodificables. "
                            "Los bits reales están en los detalles.", "Ayuda", ajustar=True)
            nota.setStyleSheet("font-size: 11px;")
            caja.addWidget(nota)

        # Estado compacto + detalles
        pie = QHBoxLayout()
        pie.setSpacing(8)
        self.indicador = IndicadorEstado(m.estado, propio, compacto=True)
        pie.addWidget(self.indicador)
        pie.addStretch(1)
        ver = QPushButton("Ver detalles")
        ver.setObjectName("BotonDetalles")
        ver.setCursor(Qt.CursorShape.PointingHandCursor)
        ver.setToolTip("Abrir el inspector matemático de esta transmisión")
        ver.clicked.connect(lambda: self.detalles_pedidos.emit(self.m))
        pie.addWidget(ver)
        caja.addLayout(pie)


class _Nota(QWidget):
    """Nota centrada del sistema (p. ej. «Canal reconfigurado»)."""

    def __init__(self, texto: str, parent=None):
        super().__init__(parent)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 2, 0, 2)
        fila.addStretch(1)
        lbl = etiqueta(texto, "SeparadorFecha")
        lbl.setStyleSheet("font-size: 11px; padding: 3px 12px;")
        fila.addWidget(lbl)
        fila.addStretch(1)


class ConversacionDual(Conversacion):
    """Lista de mensajes de un usuario (reutiliza el desplazamiento del Chat)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lista.setContentsMargins(10, 14, 12, 14)
        self._lista.setSpacing(12)

    @staticmethod
    def _aplicar_limite(widget: QWidget, proporcion: float, ancho: int) -> None:
        # Paneles estrechos: se descuenta el avatar (30 px + separación) y los márgenes.
        maximo = max(190, int((ancho - 22) * proporcion) - 38)
        widget.setMaximumWidth(maximo)
        if isinstance(widget, _ConTextoAjustable):
            widget.ajustar_ancho(maximo)

    def agregar_mensaje(self, burbuja: QWidget, derecha: bool, usuario: str) -> None:
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(8)
        avatar = _Avatar(usuario, 30)
        if derecha:
            fila.addStretch(1)
            fila.addWidget(burbuja)
            fila.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
        else:
            fila.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
            fila.addWidget(burbuja)
            fila.addStretch(1)
        self._limitar(burbuja, 0.86)
        self._insertar(envoltura)

    def agregar_nota(self, texto: str) -> None:
        self._insertar(_Nota(texto))


# ===========================================================================
# Panel de cada usuario
# ===========================================================================
class PanelUsuario(PanelTecnico):
    enviar_pedido = Signal(str, str)        # emisor, texto
    detalles_pedidos = Signal(object)       # MensajeDual

    def __init__(self, usuario: str, parent=None):
        color, color_claro, (g1, g2) = COLORES[usuario]
        otro = servicio_dual.receptor_de(usuario)
        super().__init__(parent, relleno=C.FONDO_VENTANA, borde="#1D3F6E" if usuario == "A" else "#4A1D2A",
                         acento_a=color, acento_b=color_claro, chaflan=16, marca=False)
        self.usuario = usuario
        caja = QVBoxLayout(self)
        caja.setContentsMargins(10, 10, 10, 10)
        caja.setSpacing(6)

        # Cabecera
        cab = QHBoxLayout()
        cab.setContentsMargins(8, 4, 6, 4)
        cab.setSpacing(10)
        cab.addWidget(_Avatar(usuario, 40))
        textos = QVBoxLayout()
        textos.setSpacing(0)
        nombre = etiqueta(NOMBRES[usuario], "TituloTarjeta")
        nombre.setStyleSheet(f"color: {color_claro};")
        textos.addWidget(nombre)
        sub = etiqueta(f"Envía a {NOMBRES[otro]}", "EtiquetaTenue")
        sub.setToolTip(f"{NOMBRES[usuario]} transmite a {NOMBRES[otro]} por el canal BSC")
        textos.addWidget(sub)
        cab.addLayout(textos, 1)
        self._enviados = etiqueta("", "Mono")
        self._recibidos = etiqueta("", "Mono")
        for lbl, ic, ayuda in ((self._enviados, "flecha_arriba", "Mensajes enviados"),
                               (self._recibidos, "flecha_abajo", "Mensajes recibidos")):
            ficha = QFrame()
            ficha.setObjectName("FichaContador")
            ficha.setStyleSheet(f"QFrame#FichaContador {{ background: {C.CAMPO_OSCURO};"
                                f" border: 1px solid {C.BORDE}; border-radius: 6px; }}")
            ficha.setToolTip(ayuda)
            f = QHBoxLayout(ficha)
            f.setContentsMargins(6, 3, 8, 3)
            f.setSpacing(3)
            f.addWidget(icono_label(ic, color_claro, 13))
            f.addWidget(lbl)
            cab.addWidget(ficha, 0, Qt.AlignmentFlag.AlignVCenter)
        caja.addLayout(cab)
        caja.addWidget(separador())

        # Conversación
        self.conversacion = ConversacionDual()
        caja.addWidget(self.conversacion, 1)
        self._vacio: QWidget | None = None
        self._mostrar_vacio()

        # Barra de entrada (siempre visible: la conversación es la que se desplaza)
        self.barra = QFrame()
        self.barra.setObjectName("BarraEntrada")
        self.barra.setProperty("acento", color)
        self.barra.setStyleSheet(
            f"QFrame#BarraEntrada {{ background: {C.PANEL}; border: 1px solid {rgba(color, 0.55)};"
            f" border-radius: 8px; }}"
            f"QFrame#BarraEntrada[alerta=\"true\"] {{ border: 1px solid {C.AMBAR}; }}"
            f"QPlainTextEdit#EntradaMensaje:focus {{ border: 1px solid {rgba(color, 0.75)}; }}")
        fila = QHBoxLayout(self.barra)
        fila.setContentsMargins(8, 8, 8, 8)
        fila.setSpacing(8)
        self.entrada = EntradaMensaje()
        self.entrada.setPlaceholderText(f"Mensaje para {otro}…")
        self.entrada.setToolTip("Enter para enviar · Shift + Enter para nueva línea")
        fila.addWidget(self.entrada, 1, Qt.AlignmentFlag.AlignVCenter)
        self.boton = QPushButton(f"  Enviar a {otro}")
        self.boton.setObjectName("BotonEnviarDual")
        self.boton.setProperty("acento", color)
        self.boton.setIcon(icono("enviar", C.TEXTO, 18))
        self.boton.setIconSize(QSize(18, 18))
        self.boton.setFixedHeight(42)
        self.boton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton.setToolTip(f"Transmitir a {NOMBRES[otro]} (Enter)")
        self.boton.setStyleSheet(
            f"QPushButton#BotonEnviarDual {{ border: 1px solid {rgba(color_claro, 0.7)}; border-radius: 9px;"
            f" padding: 0 14px; font-size: 14px; font-weight: 700;"
            f" background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color}, stop:1 {g2}); }}"
            f"QPushButton#BotonEnviarDual:hover {{ background: {color_claro}; }}"
            f"QPushButton#BotonEnviarDual:disabled {{ background: {C.SUPERFICIE}; color: {C.TEXTO_TENUE};"
            f" border-color: {C.BORDE}; }}")
        fila.addWidget(self.boton, 0, Qt.AlignmentFlag.AlignBottom)
        caja.addWidget(self.barra)
        self.contador = etiqueta(f"0/{servicio_dual.LONGITUD_MAXIMA}", "EtiquetaTenue")
        self.contador.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.contador.setStyleSheet("font-size: 11px;")
        caja.addWidget(self.contador)

        self.entrada.enviar_pedido.connect(self._pedir_envio)
        self.boton.clicked.connect(self._pedir_envio)
        self.entrada.textChanged.connect(self._al_escribir)
        self.set_contadores(0, 0)

    # ---- estado vacío ---------------------------------------------------
    def _mostrar_vacio(self) -> None:
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(10, 40, 10, 10)
        col.setSpacing(8)
        col.addWidget(icono_label("chat", COLORES[self.usuario][1], 34), 0, Qt.AlignmentFlag.AlignHCenter)
        t = etiqueta("Sin mensajes todavía", "Etiqueta")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(t)
        d = etiqueta(f"Escribe abajo para transmitir a {NOMBRES[servicio_dual.receptor_de(self.usuario)]}. "
                     "Lo que llegue del otro usuario será lo que recupere el decodificador.",
                     "EtiquetaTenue", ajustar=True)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(d)
        self._vacio = w
        self.conversacion.agregar_bloque(w)

    def _quitar_vacio(self) -> None:
        if self._vacio is not None:
            self.conversacion.quitar(self._vacio)
            self._vacio = None

    # ---- interacción ----------------------------------------------------
    def _al_escribir(self) -> None:
        self.contador.setText(f"{len(self.entrada.texto())}/{servicio_dual.LONGITUD_MAXIMA}")
        if self.barra.property("alerta"):
            self.barra.setProperty("alerta", False)
            repulir(self.barra)

    def _pedir_envio(self) -> None:
        self.enviar_pedido.emit(self.usuario, self.entrada.texto())

    def alertar_vacio(self) -> None:
        self.barra.setProperty("alerta", True)
        repulir(self.barra)
        self.entrada.setPlaceholderText("El mensaje está vacío: escribe algo para transmitir…")
        self.entrada.setFocus()

    def vaciar_entrada(self) -> None:
        self.entrada.clear()
        self.entrada.setPlaceholderText(
            f"Mensaje para {servicio_dual.receptor_de(self.usuario)}…")

    # ---- contenido ------------------------------------------------------
    def agregar(self, m: MensajeDual) -> None:
        self._quitar_vacio()
        propio = m.emisor == self.usuario
        burbuja = BurbujaDual(m, propio)
        burbuja.detalles_pedidos.connect(self.detalles_pedidos.emit)
        self.conversacion.agregar_mensaje(burbuja, derecha=propio, usuario=m.emisor)

    def agregar_nota(self, texto: str) -> None:
        self._quitar_vacio()
        self.conversacion.agregar_nota(texto)

    def set_contadores(self, enviados: int, recibidos: int) -> None:
        self._enviados.setText(str(enviados))
        self._recibidos.setText(str(recibidos))

    def limpiar(self) -> None:
        self.conversacion.limpiar()
        self._vacio = None
        self._mostrar_vacio()
        self.vaciar_entrada()


# ===========================================================================
# Panel derecho: parámetros + monitor
# ===========================================================================
class _FilaMonitor(QWidget):
    """Fila «etiqueta ……… valor» con una línea de detalle opcional."""

    def __init__(self, titulo: str, color: str = C.TEXTO, ayuda: str = "", parent=None):
        super().__init__(parent)
        if ayuda:
            self.setToolTip(ayuda)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 2, 0, 2)
        caja.setSpacing(0)
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self._titulo = etiqueta(titulo, "EtiquetaSecundaria")
        fila.addWidget(self._titulo, 1)
        self._valor = etiqueta("—", "Mono")
        self._valor.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 700;")
        self._valor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        fila.addWidget(self._valor)
        caja.addLayout(fila)
        self._detalle = etiqueta("", "Ayuda", ajustar=True)
        self._detalle.setStyleSheet("font-size: 11px;")
        self._detalle.hide()
        caja.addWidget(self._detalle)

    def valor(self) -> str:
        return self._valor.text()

    def set(self, valor: str, detalle: str = "") -> None:
        self._valor.setText(valor)
        self._detalle.setText(detalle)
        self._detalle.setVisible(bool(detalle))


class PanelControlDual(AreaDesplazable):
    parametros_cambiados = Signal(int, float)

    def __init__(self, parent=None):
        super().__init__(margenes=(0, 0, 4, 0), espaciado=12, parent=parent)
        self.setFixedWidth(ANCHO_CONTROL)
        lay = self.layout_interno

        # ---- Parámetros del canal -----------------------------------------
        par = PanelSecundario(relleno=C.PANEL, borde="#1D3F6E", acento_a=C.ROJO, acento_b=C.AZUL_ELECTRICO,
                           chaflan=12, marca=False)
        c = QVBoxLayout(par)
        c.setContentsMargins(16, 14, 14, 14)
        c.setSpacing(8)
        cab = QHBoxLayout()
        cab.setSpacing(8)
        cab.addWidget(icono_label("antena", C.ROJO, 20))
        cab.addWidget(etiqueta("Parámetros del canal", "TituloTarjeta"), 1)
        c.addLayout(cab)
        c.addWidget(etiqueta("Propios del Chat Dual y compartidos por A y B. Cada mensaje guarda "
                             "una copia de los valores con que se transmitió.", "Ayuda", ajustar=True))
        c.addWidget(etiqueta("REPETICIÓN n", "Seccion"))
        self.selector_n = ControlSegmentado([f"n = {n}" for n in servicio_dual.LONGITUDES_DUAL])
        self._marcar_n(servicio_dual.N_INICIAL)
        c.addWidget(self.selector_n)
        c.addWidget(etiqueta("PROBABILIDAD p (0 – 0.5)", "Seccion"))
        self.control_p = ControlProbabilidad(servicio_dual.P_INICIAL)
        c.addWidget(self.control_p)
        self._resumen = QLabel()
        self._resumen.setTextFormat(Qt.TextFormat.RichText)
        self._resumen.setWordWrap(True)
        self._resumen.setObjectName("EtiquetaSecundaria")
        c.addWidget(self._resumen)
        self.boton_restablecer = QPushButton("  Restablecer parámetros")
        self.boton_restablecer.setIcon(icono("reiniciar", C.TEXTO_SECUNDARIO, 15))
        self.boton_restablecer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_restablecer.setToolTip(f"Volver a n = {servicio_dual.N_INICIAL} y "
                                          f"p = {formato_p(servicio_dual.P_INICIAL)}")
        c.addWidget(self.boton_restablecer)
        lay.addWidget(par)

        # ---- Monitor -------------------------------------------------------
        mon = PanelTecnico(relleno=C.PANEL, borde="#1D3F6E", acento_a=C.AZUL_ELECTRICO, acento_b=C.ROJO,
                           chaflan=12, marca=False)
        m = QVBoxLayout(mon)
        m.setContentsMargins(16, 14, 14, 14)
        m.setSpacing(4)
        cab = QHBoxLayout()
        cab.setSpacing(8)
        cab.addWidget(icono_label("actividad", C.AZUL, 20))
        cab.addWidget(etiqueta("Monitor de la conversación", "TituloTarjeta"), 1)
        m.addLayout(cab)

        def grupo(titulo: str) -> None:
            m.addSpacing(6)
            m.addWidget(etiqueta(titulo, "Seccion"))

        self.f_total = _FilaMonitor("Mensajes transmitidos")
        self.f_a = _FilaMonitor("Enviados por A", C.AZUL)
        self.f_b = _FilaMonitor("Enviados por B", C.ROJO_CLARO)
        self.f_bits = _FilaMonitor("Bits originales", COLOR_ORIGINAL, "Σ bits UTF‑8 de todos los mensajes")
        self.f_cod = _FilaMonitor("Bits codificados", COLOR_CODIFICADO,
                                  "Σ bits enviados por el canal (bits × n de cada mensaje)")
        self.f_alterados = _FilaMonitor("Bits alterados", COLOR_RUIDO, "Σ bits que el canal invirtió")
        self.f_ber_canal = _FilaMonitor("BER del canal", COLOR_RUIDO,
                                        "Σ bits alterados / Σ bits codificados")
        self.f_residuales = _FilaMonitor("Errores residuales", COLOR_RESIDUAL,
                                         "Σ bits de información decididos incorrectamente")
        self.f_empates = _FilaMonitor("Bits empatados (sin decidir)", C.MORADO,
                                      "Bits con «?»: no son errores, pero tampoco se recuperaron")
        self.f_ber = _FilaMonitor("BER residual acumulado", COLOR_RESIDUAL,
                                  "Σ errores residuales / Σ bits decididos")
        self.f_tasa = _FilaMonitor("Tasa R = k/n", C.AZUL, "Tasa del código con la configuración actual")
        self.f_cap = _FilaMonitor("Capacidad C = 1 − H₂(p)", C.MORADO,
                                  "Límite teórico del canal con la p actual (core.matematicas)")
        for titulo, filas in (("CONVERSACIÓN", (self.f_total, self.f_a, self.f_b)),
                              ("BITS", (self.f_bits, self.f_cod)),
                              ("CANAL BSC · ANTES DE DECODIFICAR", (self.f_alterados, self.f_ber_canal)),
                              ("DECODIFICACIÓN · DESPUÉS", (self.f_residuales, self.f_empates, self.f_ber)),
                              ("CONFIGURACIÓN ACTUAL", (self.f_tasa, self.f_cap))):
            grupo(titulo)
            for f in filas:
                m.addWidget(f)
        self.nota_agregado = etiqueta("", "Ayuda", ajustar=True)
        m.addSpacing(6)
        m.addWidget(self.nota_agregado)
        lay.addWidget(mon)
        lay.addStretch(1)

        self.selector_n.cambiado.connect(lambda _i: self._emitir())
        self.control_p.valor_cambiado.connect(lambda _p: self._emitir())
        self.boton_restablecer.clicked.connect(self.restablecer)
        self._actualizar_resumen()

    # ---- parámetros -----------------------------------------------------
    def _marcar_n(self, n: int) -> None:
        self.selector_n._grupo.button(servicio_dual.LONGITUDES_DUAL.index(n)).setChecked(True)

    def n(self) -> int:
        return servicio_dual.LONGITUDES_DUAL[max(0, self.selector_n.indice())]

    def p(self) -> float:
        return self.control_p.valor()

    def restablecer(self) -> None:
        self._marcar_n(servicio_dual.N_INICIAL)
        self.control_p.set_valor(servicio_dual.P_INICIAL)
        self._emitir()

    def _emitir(self) -> None:
        self._actualizar_resumen()
        self.parametros_cambiados.emit(self.n(), self.p())

    def _actualizar_resumen(self) -> None:
        par = servicio.parametros(self.n())
        t = C.TEXTO
        self._resumen.setText(
            f"k = <b style='color:{t};'>{par['k']}</b> · d<sub>min</sub> = "
            f"<b style='color:{t};'>{par['distancia_minima']}</b> · t = "
            f"<b style='color:{t};'>{par['errores_corregibles']}</b> · R = "
            f"<b style='color:{C.AZUL};'>{par['tasa']:.3f}</b>")

    # ---- monitor --------------------------------------------------------
    def actualizar_monitor(self, conv: ConversacionDual) -> None:
        a = conv.metricas()
        par = servicio.parametros(self.n())
        self.f_total.set(str(a.mensajes))
        self.f_a.set(str(a.enviados_a))
        self.f_b.set(str(a.enviados_b))
        self.f_bits.set(str(a.bits_originales))
        self.f_cod.set(str(a.bits_codificados))
        self.f_alterados.set(str(a.errores_canal))
        self.f_ber_canal.set(formato_ber(a.ber_canal) if a.ber_canal is not None else NO_DISPONIBLE,
                             f"{a.errores_canal} / {a.bits_codificados} bits" if a.mensajes else
                             "sin transmisiones")
        self.f_residuales.set(str(a.errores_residuales))
        self.f_empates.set(str(a.empates), "imposibles con n impar" if not a.empates else "")
        if a.ber_residual is None:
            self.f_ber.set(NO_DISPONIBLE, "sin transmisiones" if not a.mensajes else
                           "ningún bit tuvo decisión (todos empatados)")
        else:
            self.f_ber.set(formato_ber(a.ber_residual),
                           f"{a.errores_residuales} / {a.bits_decididos} bits decididos"
                           + (f" (se excluyen {a.empates} empatados)" if a.empates else ""))
        self.f_tasa.set(f"{par['tasa']:.3f}", f"n = {self.n()} · k = {par['k']}")
        self.f_cap.set(f"{servicio.capacidad(self.p()):.3f}", f"p = {formato_p(self.p())}")
        k = len(a.configuraciones)
        if a.mensajes == 0:
            nota = "Los totales suman conteos de todos los mensajes; las BER no son promedios de BER."
        elif k == 1:
            (n0, p0), = a.configuraciones
            nota = (f"Agregado de {a.mensajes} mensaje(s), todos con n = {n0} y p = {formato_p(p0)}. "
                    "Las BER se calculan con los conteos totales, no promediando BER.")
        else:
            nota = (f"Agregado de {a.mensajes} mensajes con {k} configuraciones (n, p) distintas: los "
                    "totales suman bits de todas ellas. Tasa efectiva acumulada = "
                    f"{a.tasa_efectiva:.3f}. Para comparar códigos usa «Comparar códigos».")
        self.nota_agregado.setText(nota)


# ===========================================================================
# Inspector de bloques (votación por mayoría)
# ===========================================================================
class ComparadorBloques(QWidget):
    """Original → Codificado → Recibido → Recuperado para un rango de bloques.

    Cada columna es un bloque (un bit de información repetido n veces). Clic = seleccionar.
    """

    bloque_elegido = Signal(int)
    FILAS = ("Original", "Codificado", "Recibido", "Recuperado")
    ANCHO_ETIQUETA = 92
    HUECO = 12

    def __init__(self, r: servicio.ResultadoTransmision, parent=None):
        super().__init__(parent)
        self.r = r
        self.inicio, self.cantidad = 0, BITS_POR_PAGINA
        self.seleccion = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(4 * 40 + 24)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_rango(self, inicio: int, cantidad: int) -> None:
        self.inicio, self.cantidad = inicio, cantidad
        self.update()

    def seleccionar(self, i: int) -> None:
        self.seleccion = i
        self.update()

    def _geometria(self):
        n = self.r.n
        visibles = max(1, min(self.cantidad, len(self.r.bits_originales) - self.inicio))
        disponible = self.width() - self.ANCHO_ETIQUETA - self.HUECO * visibles
        celda = max(8.0, min(24.0, disponible / (visibles * n)))
        return n, visibles, celda, celda * n

    def _x_bloque(self, j: int, ancho_col: float) -> float:
        return self.ANCHO_ETIQUETA + j * (ancho_col + self.HUECO)

    def paintEvent(self, _event):
        r = self.r
        n, visibles, celda, ancho_col = self._geometria()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        alto_celda = 24.0
        y0, paso = 22.0, 40.0
        p.setFont(fuente(9, QFont.Weight.DemiBold))
        for k, nombre in enumerate(self.FILAS):
            p.setPen(qcolor(C.TEXTO_SECUNDARIO))
            p.drawText(QRectF(0, y0 + k * paso, self.ANCHO_ETIQUETA - 8, alto_celda),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, nombre)
        fuente_bits = fuente_mono(max(7, int(min(celda, alto_celda) * 0.42)))
        for j in range(visibles):
            i = self.inicio + j
            x = self._x_bloque(j, ancho_col)
            original = r.bits_originales[i]
            enviado = r.codificado[i * n:(i + 1) * n]
            recibido = r.recibido[i * n:(i + 1) * n]
            decidido = r.recuperado[i]
            p.setFont(fuente(8))
            p.setPen(qcolor(C.TEXTO_TENUE))
            p.drawText(QRectF(x, 0, ancho_col, 18), Qt.AlignmentFlag.AlignCenter, f"b{i + 1}")
            if i == self.seleccion:
                p.setPen(QPen(qcolor(C.TEXTO, 200), 1.4))
                p.setBrush(qcolor(C.TEXTO, 14))
                p.drawRoundedRect(QRectF(x - 5, 16, ancho_col + 10, 4 * paso + 4), 6, 6)
            p.setFont(fuente_bits)
            centro = x + ancho_col / 2 - celda / 2
            self._celda(p, QRectF(centro, y0, celda, alto_celda), original, COLOR_ORIGINAL, 150)
            for b in range(n):
                self._celda(p, QRectF(x + b * celda, y0 + paso, celda - 1, alto_celda), enviado[b],
                            COLOR_CODIFICADO, 70)
            for b in range(n):
                alterado = recibido[b] != enviado[b]
                self._celda(p, QRectF(x + b * celda, y0 + 2 * paso, celda - 1, alto_celda), recibido[b],
                            COLOR_RUIDO if alterado else COLOR_CODIFICADO, 200 if alterado else 45)
            ok = decidido == original
            self._celda(p, QRectF(centro, y0 + 3 * paso, celda, alto_celda), decidido,
                        COLOR_RECUPERADO if ok else COLOR_RESIDUAL, 120 if ok else 190)
        p.end()

    @staticmethod
    def _celda(p: QPainter, rect: QRectF, bit: str, color: str, alfa: int) -> None:
        p.setPen(QPen(qcolor(color, 230), 1))
        p.setBrush(qcolor(color, alfa))
        p.drawRoundedRect(rect, 3, 3)
        if rect.width() >= 10:
            p.setPen(QColor(C.TEXTO))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, bit)

    def _indice_en(self, x: float) -> int:
        _n, visibles, _celda, ancho_col = self._geometria()
        for j in range(visibles):
            x0 = self._x_bloque(j, ancho_col)
            if x0 - self.HUECO / 2 <= x <= x0 + ancho_col + self.HUECO / 2:
                return self.inicio + j
        return -1

    def mousePressEvent(self, event):
        i = self._indice_en(event.position().x())
        if i >= 0:
            self.bloque_elegido.emit(i)

    def mouseMoveEvent(self, event):
        i = self._indice_en(event.position().x())
        if i >= 0:
            e = self.r.errores_por_bloque[i]
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"Bloque {i + 1}: {e} bit(s) alterado(s) por el canal", self)


class _DetalleBloque(QFrame):
    """Ficha del bloque seleccionado: todos los pasos de la votación."""

    CAMPOS = ("Bit original", "Grupo codificado", "Grupo recibido", "Inversiones",
              "Votación por mayoría", "Bit decodificado", "Resultado")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MiniDato")
        rejilla = QGridLayout(self)
        rejilla.setContentsMargins(14, 10, 14, 10)
        rejilla.setHorizontalSpacing(18)
        rejilla.setVerticalSpacing(4)
        self.titulo = etiqueta("", "Etiqueta")
        self.titulo.setStyleSheet("font-weight: 700;")
        rejilla.addWidget(self.titulo, 0, 0, 1, 4)
        self.valores: dict[str, QLabel] = {}
        for k, campo in enumerate(self.CAMPOS):
            fila, col = 1 + k // 2, (k % 2) * 2
            rejilla.addWidget(etiqueta(campo, "EtiquetaSecundaria"), fila, col)
            v = QLabel()
            v.setTextFormat(Qt.TextFormat.RichText)
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            rejilla.addWidget(v, fila, col + 1)
            self.valores[campo] = v
        rejilla.setColumnStretch(1, 1)
        rejilla.setColumnStretch(3, 1)

    def mostrar(self, r: servicio.ResultadoTransmision, i: int) -> None:
        n = r.n
        enviado = r.codificado[i * n:(i + 1) * n]
        recibido = r.recibido[i * n:(i + 1) * n]
        mono = f"font-family:{PILA_MONO}; font-size:14px; font-weight:700;"
        marcado = "".join(f"<span style='color:{COLOR_RUIDO};'>{b}</span>" if b != a
                          else f"<span style='color:{COLOR_CODIFICADO};'>{b}</span>"
                          for a, b in zip(enviado, recibido))
        e = r.errores_por_bloque[i]
        unos, ceros = recibido.count("1"), recibido.count("0")
        decidido = r.recuperado[i]
        original = r.bits_originales[i]
        if decidido == "?":
            resultado = f"<b style='color:{COLOR_RESIDUAL};'>Empate: sin mayoría</b>"
        elif decidido == original:
            resultado = (f"<b style='color:{COLOR_RECUPERADO};'>Correcto</b>"
                         + (f" · {e} ≤ t = {r.t}, corregido" if e else " · sin inversiones"))
        else:
            resultado = (f"<b style='color:{COLOR_RESIDUAL};'>Incorrecto</b> · {e} &gt; t = {r.t}")
        voto = ("1" if unos > ceros else "0") if unos != ceros else "empate"
        self.titulo.setText(f"Bloque {i + 1} de {r.total_bloques}  ·  bits {i * n + 1}–{(i + 1) * n} "
                            "de la secuencia codificada")
        v = self.valores
        v["Bit original"].setText(f"<span style='{mono} color:{COLOR_ORIGINAL};'>{original}</span>")
        v["Grupo codificado"].setText(f"<span style='{mono} color:{COLOR_CODIFICADO};'>{enviado}</span>")
        v["Grupo recibido"].setText(f"<span style='{mono}'>{marcado}</span>")
        v["Inversiones"].setText(f"<span style='{mono} color:{COLOR_RUIDO if e else C.TEXTO};'>{e}</span>"
                                 f" de {n}")
        v["Votación por mayoría"].setText(f"{unos} uno(s) contra {ceros} cero(s) → <b>{voto}</b>")
        color_dec = COLOR_RECUPERADO if decidido == original else COLOR_RESIDUAL
        v["Bit decodificado"].setText(f"<span style='{mono} color:{color_dec};'>{html.escape(decidido)}</span>")
        v["Resultado"].setText(resultado)


class VisualizacionTransmision(QFrame):
    """Navegación por bloques y bytes + comparador + ficha del bloque elegido."""

    def __init__(self, m: MensajeDual, parent=None):
        super().__init__(parent)
        self.m = m
        self.r = r = m.resultado
        self.total_bloques = len(r.bits_originales)
        self.total_paginas = max(1, -(-self.total_bloques // BITS_POR_PAGINA))
        self.actual = 0
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(10)

        nav = QHBoxLayout()
        nav.setSpacing(8)

        def boton(nombre_icono: str, ayuda: str, texto: str = "") -> QPushButton:
            b = QPushButton(texto)
            b.setIcon(icono(nombre_icono, C.TEXTO, 15))
            b.setToolTip(ayuda)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if not texto:
                b.setFixedSize(36, 32)
                b.setStyleSheet("padding: 0;")
            return b

        self.bloque_anterior = boton("flecha_izquierda", "Bloque anterior", " Bloque")
        self.bloque_siguiente = boton("flecha_derecha", "Bloque siguiente", " Bloque")
        self.bloque_siguiente.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        nav.addWidget(self.bloque_anterior)
        nav.addWidget(self.bloque_siguiente)
        nav.addSpacing(14)
        self.anterior = boton("flecha_izquierda", "Byte anterior")
        nav.addWidget(self.anterior)
        nav.addWidget(etiqueta("Byte", "EtiquetaSecundaria"))
        self.selector = QSpinBox()
        self.selector.setRange(1, self.total_paginas)
        self.selector.setFixedWidth(84)
        self.selector.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.selector)
        nav.addWidget(etiqueta(f"de {self.total_paginas}", "EtiquetaSecundaria"))
        self.siguiente = boton("flecha_derecha", "Byte siguiente")
        nav.addWidget(self.siguiente)
        nav.addStretch(1)
        self.boton_error = QPushButton("  Siguiente con errores")
        self.boton_error.setObjectName("BotonDetalles")
        self.boton_error.setIcon(icono("alerta", C.ROJO_CLARO, 14))
        self.boton_error.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_error.setToolTip("Saltar al siguiente bloque en el que el canal alteró algún bit")
        self.boton_error.setEnabled(r.errores_canal > 0)
        nav.addWidget(self.boton_error)
        caja.addLayout(nav)

        self.info_byte = QLabel()
        self.info_byte.setTextFormat(Qt.TextFormat.RichText)
        self.info_byte.setObjectName("EtiquetaSecundaria")
        caja.addWidget(self.info_byte)

        marco = QFrame()
        marco.setObjectName("PanelEtapas")
        mc = QVBoxLayout(marco)
        mc.setContentsMargins(14, 12, 14, 12)
        self.comparador = ComparadorBloques(r)
        mc.addWidget(self.comparador)
        caja.addWidget(marco)

        self.detalle = _DetalleBloque()
        caja.addWidget(self.detalle)
        caja.addWidget(self._leyenda())

        self.bloque_anterior.clicked.connect(lambda: self.ir_a_bloque(self.actual - 1))
        self.bloque_siguiente.clicked.connect(lambda: self.ir_a_bloque(self.actual + 1))
        self.anterior.clicked.connect(lambda: self.selector.setValue(self.selector.value() - 1))
        self.siguiente.clicked.connect(lambda: self.selector.setValue(self.selector.value() + 1))
        self.selector.valueChanged.connect(lambda pag: self.ir_a_bloque((pag - 1) * BITS_POR_PAGINA))
        self.boton_error.clicked.connect(self._siguiente_con_errores)
        self.comparador.bloque_elegido.connect(self.ir_a_bloque)

        # Primera vista: el primer bloque alterado por el canal (si lo hay)
        self.ir_a_bloque(next((i for i, e in enumerate(r.errores_por_bloque) if e), 0))

    @staticmethod
    def _leyenda() -> QWidget:
        w = QWidget()
        fila = FlujoLayout(w, espaciado=14)
        for color, texto in ((COLOR_ORIGINAL, "Bit original"),
                             (COLOR_CODIFICADO, "Bit codificado"),
                             (COLOR_RUIDO, "Invertido por el canal"),
                             (COLOR_RECUPERADO, "Recuperado correctamente"),
                             (COLOR_RESIDUAL, "Error residual / empate")):
            item = QWidget()
            f = QHBoxLayout(item)
            f.setContentsMargins(0, 0, 0, 0)
            f.setSpacing(6)
            muestra = QLabel()
            muestra.setFixedSize(13, 13)
            muestra.setStyleSheet(f"background: {rgba(color, 0.55)}; border: 1px solid {color};"
                                  " border-radius: 3px;")
            f.addWidget(muestra)
            f.addWidget(etiqueta(texto, "EtiquetaTenue"))
            fila.addWidget(item)
        return w

    def ir_a_bloque(self, i: int) -> None:
        i = max(0, min(self.total_bloques - 1, i))
        self.actual = i
        pagina = i // BITS_POR_PAGINA + 1
        if self.selector.value() != pagina:
            self.selector.blockSignals(True)
            self.selector.setValue(pagina)
            self.selector.blockSignals(False)
        self._mostrar_pagina(pagina)
        self.comparador.seleccionar(i)
        self.detalle.mostrar(self.r, i)
        self.bloque_anterior.setEnabled(i > 0)
        self.bloque_siguiente.setEnabled(i < self.total_bloques - 1)

    def _mostrar_pagina(self, pagina: int) -> None:
        r = self.r
        inicio = (pagina - 1) * BITS_POR_PAGINA
        self.comparador.set_rango(inicio, BITS_POR_PAGINA)
        self.anterior.setEnabled(pagina > 1)
        self.siguiente.setEnabled(pagina < self.total_paginas)
        original = r.bits_originales[inicio:inicio + BITS_POR_PAGINA]
        recuperado = r.recuperado[inicio:inicio + BITS_POR_PAGINA]
        color = COLOR_RECUPERADO if original == recuperado else COLOR_RESIDUAL
        alterados = sum(r.errores_por_bloque[inicio:inicio + BITS_POR_PAGINA])
        self.info_byte.setText(
            f"Byte {pagina}: original <b style='color:{COLOR_ORIGINAL};'>{_byte_legible(original)}</b> → "
            f"recuperado <b style='color:{color};'>{_byte_legible(recuperado)}</b> · "
            f"<span style='color:{COLOR_RUIDO if alterados else C.TEXTO_TENUE};'>{alterados} bit(s) "
            f"invertido(s) en sus {BITS_POR_PAGINA * r.n} bits transmitidos</span>")

    def _siguiente_con_errores(self) -> None:
        indices = [i for i, e in enumerate(self.r.errores_por_bloque) if e]
        if indices:
            self.ir_a_bloque(next((i for i in indices if i > self.actual), indices[0]))


# ===========================================================================
# Inspector matemático
# ===========================================================================
class _Seccion(PanelSecundario):
    """Etapa del inspector: valores a la izquierda y secuencias a la derecha."""

    def __init__(self, letra: str, titulo: str, nombre_icono: str, color: str,
                 columnas: bool = True, parent=None):
        super().__init__(parent, relleno=C.PANEL, borde=C.BORDE, acento_a=color, acento_b=None,
                         chaflan=10, marca=False)
        self.caja = QVBoxLayout(self)
        self.caja.setContentsMargins(18, 14, 18, 16)
        self.caja.setSpacing(10)
        cab = QHBoxLayout()
        cab.setSpacing(10)
        insignia = QLabel(letra)
        insignia.setFixedSize(26, 26)
        insignia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        insignia.setStyleSheet(f"background: {rgba(color, 0.16)}; color: {color}; border: 1px solid"
                               f" {rgba(color, 0.6)}; border-radius: 6px; font-weight: 800;")
        cab.addWidget(insignia)
        cab.addWidget(icono_label(nombre_icono, color, 20))
        cab.addWidget(etiqueta(titulo, "TituloTarjeta"), 1)
        self.caja.addLayout(cab)
        self._rejilla = QGridLayout()
        self._rejilla.setHorizontalSpacing(12)
        self._rejilla.setVerticalSpacing(7)
        self._rejilla.setColumnStretch(1, 1)
        if columnas:
            cuerpo = QHBoxLayout()
            cuerpo.setSpacing(24)
            izquierda = QVBoxLayout()
            izquierda.addLayout(self._rejilla)
            izquierda.addStretch(1)
            cuerpo.addLayout(izquierda, 5)
            self.derecha = QVBoxLayout()
            self.derecha.setSpacing(8)
            cuerpo.addLayout(self.derecha, 6)
            self.caja.addLayout(cuerpo)
        else:
            self.caja.addLayout(self._rejilla)
            self.derecha = self.caja

    def fila(self, titulo: str, valor: str, tipo: str, color: str = C.TEXTO, ayuda: str = "") -> QLabel:
        k = self._rejilla.rowCount()
        t = etiqueta(titulo, "EtiquetaSecundaria", ajustar=True)
        v = etiqueta(valor, "Mono", ajustar=True)
        v.setStyleSheet(f"color: {color}; font-weight: 700;")
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        for w in (t, v):
            w.setToolTip(ayuda)
        self._rejilla.addWidget(t, k, 0)
        self._rejilla.addWidget(v, k, 1)
        self._rejilla.addWidget(_etiqueta_tipo(tipo), k, 2, Qt.AlignmentFlag.AlignVCenter)
        return v

    def fila_ancha(self, titulo: str, valor: str, tipo: str, color: str = C.TEXTO, ayuda: str = "") -> None:
        """Título + tipo en una fila y el valor largo debajo, a todo el ancho de la columna."""
        k = self._rejilla.rowCount()
        t = etiqueta(titulo, "EtiquetaSecundaria", ajustar=True)
        t.setToolTip(ayuda)
        self._rejilla.addWidget(t, k, 0, 1, 2)
        self._rejilla.addWidget(_etiqueta_tipo(tipo), k, 2, Qt.AlignmentFlag.AlignVCenter)
        v = etiqueta(valor, "Mono", ajustar=True)
        v.setObjectName("CampoValor")
        v.setStyleSheet(f"color: {color}; font-size: 12px; background: {C.CAMPO_OSCURO};"
                        f" border: 1px solid {C.BORDE_SUAVE}; border-radius: 5px; padding: 5px 8px;")
        v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.setToolTip(ayuda)
        self._rejilla.addWidget(v, k + 1, 0, 1, 3)

    def bits(self, titulo: str, html_bits: str, copiar: str, lineas: int = 4) -> None:
        cab = QHBoxLayout()
        cab.setSpacing(6)
        cab.addWidget(etiqueta(titulo, "TituloPaso"), 1)
        cab.addWidget(etiqueta(f"{len(copiar)} bits", "EtiquetaTenue"))
        cab.addWidget(boton_copiar(lambda: copiar, "Copiar la secuencia completa"))
        self.derecha.addLayout(cab)
        self.derecha.addWidget(_visor(html_bits, lineas))

    def texto(self, contenido: str, color: str = C.TEXTO_SECUNDARIO, derecha: bool = True) -> QLabel:
        lbl = etiqueta(contenido, "Etiqueta", ajustar=True)
        lbl.setStyleSheet(f"color: {color}; font-size: 13px;")
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        (self.derecha if derecha else self.caja).addWidget(lbl)
        return lbl


def _tabla_teoria(r: servicio.ResultadoTransmision) -> QWidget:
    """Tabla «magnitud · teórico · simulación» con notas de disponibilidad."""
    par = r.parametros
    teorico_pe = r.error_residual_teorico
    filas = [
        ("Tasa del código", f"R = k/n = {par['tasa']:.4f}",
         f"{len(r.bits_originales)}/{len(r.codificado)} = {len(r.bits_originales) / len(r.codificado):.4f}",
         "Bits de información por bit transmitido. Coinciden siempre: R es fija para el código."),
        ("Probabilidad de inversión", f"p = {formato_p(r.p)}", f"BER canal = {formato_ber(r.ber_canal)}",
         "La fracción de bits invertidos en una transmisión fluctúa alrededor de p."),
        ("Error por bit tras decodificar",
         f"Pₑ = {formato_ber(teorico_pe)}" if teorico_pe is not None else NO_DISPONIBLE,
         (f"BER residual = {formato_ber(r.ber_con_codigo)}" if r.ber_con_codigo is not None
          else NO_DISPONIBLE),
         ("Pₑ es la probabilidad teórica (core.matematicas); la BER es la frecuencia observada."
          if teorico_pe is not None else
          "Pₑ no disponible: la fórmula del núcleo solo está definida para n impar.")
         + ("" if r.ber_con_codigo is not None else
            " BER no disponible: ningún bit tuvo decisión (todos empatados)."),),
        ("Capacidad del canal", f"C = 1 − H₂(p) = {r.capacidad:.4f}", "No aplica",
         "C es un límite teórico del canal (bits de información por uso); no se mide en una transmisión."),
    ]
    w = QFrame()
    w.setObjectName("PanelEtapas")
    g = QGridLayout(w)
    g.setContentsMargins(14, 10, 14, 10)
    g.setHorizontalSpacing(18)
    g.setVerticalSpacing(8)
    for col, (texto, tipo) in enumerate((("Magnitud", None), ("Teórico", "teorico"),
                                         ("Esta simulación", "medido"), ("Interpretación", None))):
        cab = QHBoxLayout()
        cab.setSpacing(6)
        cab.addWidget(etiqueta(texto.upper(), "Seccion"))
        if tipo:
            cab.addWidget(_etiqueta_tipo(tipo))
        cab.addStretch(1)
        g.addLayout(cab, 0, col)
    for k, (nombre, teo, exp, nota) in enumerate(filas, 1):
        g.addWidget(etiqueta(nombre, "Etiqueta"), k, 0)
        for col, (valor, color) in enumerate(((teo, C.MORADO), (exp, C.VERDE)), 1):
            v = etiqueta(valor, "Mono")
            v.setStyleSheet(f"color: {C.TEXTO_TENUE if valor in (NO_DISPONIBLE, 'No aplica') else color};"
                            " font-weight: 700;")
            g.addWidget(v, k, col)
        g.addWidget(etiqueta(nota, "Ayuda", ajustar=True), k, 3)
    g.setColumnStretch(3, 1)
    return w


class DialogoInspector(QDialog):
    """Inspector organizado por etapas A–E con valores teóricos y de simulación separados."""

    comparar_pedido = Signal(str, float)

    def __init__(self, m: MensajeDual, parent=None):
        super().__init__(parent)
        r = m.resultado
        par = r.parametros
        self.setWindowTitle(f"Inspector de transmisión — mensaje #{m.numero}")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setSizeGripEnabled(True)
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1240, int(pantalla.width() * 0.94)), min(900, int(pantalla.height() * 0.92)))
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # ---- Cabecera fija + navegador de etapas ----------------------------
        barra = QFrame()
        barra.setObjectName("CabeceraInspector")
        barra.setStyleSheet(f"QFrame#CabeceraInspector {{ background: {C.FONDO_VENTANA};"
                            f" border-bottom: 1px solid {C.BORDE}; }}")
        bc = QVBoxLayout(barra)
        bc.setContentsMargins(20, 14, 20, 12)
        bc.setSpacing(10)
        cab = QHBoxLayout()
        cab.setSpacing(12)
        cab.addWidget(_Avatar(m.emisor, 34))
        cab.addWidget(icono_label("flecha_derecha", C.TEXTO_SECUNDARIO, 18))
        cab.addWidget(_Avatar(m.receptor, 34))
        tit = QVBoxLayout()
        tit.setSpacing(0)
        tit.addWidget(etiqueta(f"Mensaje #{m.numero}: {NOMBRES[m.emisor]} → {NOMBRES[m.receptor]}",
                               "TituloTarjeta"))
        tit.addWidget(etiqueta(f"{m.fecha:%d/%m/%Y %H:%M:%S} · código de repetición n = {r.n} · "
                               f"canal BSC p = {formato_p(r.p)}", "EtiquetaSecundaria"))
        cab.addLayout(tit, 1)
        cab.addWidget(IndicadorEstado(m.estado, propio=False))
        bc.addLayout(cab)
        nav = QHBoxLayout()
        nav.setSpacing(6)
        self._botones_etapa: list[tuple[QPushButton, str]] = []
        for clave, texto in (("A", "A · Mensaje original"), ("B", "B · Codificación"), ("C", "C · Canal BSC"),
                             ("D", "D · Decodificación"), ("V", "Bloques"), ("E", "E · Fundamento teórico")):
            b = QPushButton(texto)
            b.setObjectName("BotonDetalles")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            nav.addWidget(b)
            self._botones_etapa.append((b, clave))
        nav.addStretch(1)
        bc.addLayout(nav)
        raiz.addWidget(barra)

        self.area = AreaDesplazable(margenes=(20, 16, 20, 18), espaciado=14)
        raiz.addWidget(self.area, 1)
        lay = self.area.layout_interno
        etapas: dict[str, QWidget] = {}

        # ---- A. Mensaje original ---------------------------------------------
        a = _Seccion("A", "Mensaje original", "texto", COLOR_ORIGINAL)
        a.fila("Emisor", NOMBRES[m.emisor], "dato", COLORES[m.emisor][1])
        a.fila("Receptor", NOMBRES[m.receptor], "dato", COLORES[m.receptor][1])
        a.fila_ancha("Mensaje original", texto_ajustable(m.texto_original), "dato", COLOR_ORIGINAL)
        a.fila("Caracteres", str(m.caracteres), "dato")
        a.fila("Bytes UTF‑8", str(m.bytes_utf8), "dato",
               ayuda="Las tildes ocupan 2 bytes y los emojis 4 en UTF‑8")
        a.fila("Bits originales", f"{len(r.bits_originales)}  (= {m.bytes_utf8} × 8)", "dato")
        a.bits("Representación binaria UTF‑8 (un grupo por byte)",
               _html_bits(r.bits_originales, color=COLOR_ORIGINAL, bloque=8), r.bits_originales, 5)
        lay.addWidget(a)
        etapas["A"] = a

        # ---- B. Codificación ---------------------------------------------------
        b = _Seccion("B", "Codificación por repetición", "capas", COLOR_CODIFICADO)
        b.fila("Código", f"Repetición binario ({par['n']}, {par['k']})", "codigo")
        b.fila("Longitud n", str(par["n"]), "codigo")
        b.fila("Dimensión k", f"{par['k']}  (por palabra de código)", "codigo",
               ayuda="k cuenta los bits de información de CADA palabra, no la longitud del mensaje")
        b.fila("Palabras de código M", f"{par['M']}  (= 2^k)", "codigo")
        b.fila("Distancia mínima d_min", str(par["distancia_minima"]), "codigo")
        b.fila("Capacidad correctora t", f"{par['errores_corregibles']}  (= floor((n − 1)/2))", "codigo")
        b.fila("Tasa R = k/n", f"{par['tasa']:.4f}", "codigo", C.AZUL)
        b.fila("Bits transmitidos", f"{len(r.codificado)}  (= {len(r.bits_originales)} × {r.n})", "dato")
        b.fila("Redundancia", f"{par['n'] - par['k']} por palabra · {len(r.codificado) - len(r.bits_originales)}"
               " en total", "dato", ayuda="n − k bits repetidos por palabra de código")
        b.bits(f"Bits codificados (cada bit se repite {r.n} veces)",
               _html_bits(r.codificado, color=COLOR_CODIFICADO, bloque=r.n), r.codificado, 6)
        b.texto(f"El mensaje tiene {len(r.bits_originales)} bits: se codifica como "
                f"{len(r.bits_originales)} palabras independientes de k = {par['k']} bit y n = {r.n} bits.",
                C.TEXTO_TENUE)
        lay.addWidget(b)
        etapas["B"] = b

        # ---- C. Canal BSC ------------------------------------------------------
        c = _Seccion("C", "Canal binario simétrico", "antena", COLOR_RUIDO)
        c.fila("Probabilidad p", formato_p(r.p), "canal",
               ayuda="Probabilidad de que el canal invierta cada bit, de forma independiente")
        c.fila("Bits invertidos", f"{r.errores_canal} de {len(r.codificado)}", "medido",
               COLOR_RUIDO if r.errores_canal else C.TEXTO)
        c.fila("BER del canal", formato_ber(r.ber_canal), "medido", COLOR_RUIDO,
               "Bits invertidos / bits transmitidos (antes de decodificar)")
        c.fila_ancha(f"Posiciones de los errores ({r.errores_canal})", _posiciones(m.posiciones_error),
                     "medido", COLOR_RUIDO, "Posición (desde 1) dentro de la secuencia codificada")
        c.bits("Antes del canal (secuencia codificada)",
               _html_bits(r.codificado, color=COLOR_CODIFICADO, bloque=r.n), r.codificado, 3)
        c.bits("Después del canal (rojo = bit invertido)",
               _html_bits(r.recibido, r.codificado, COLOR_CODIFICADO, bloque=r.n), r.recibido, 3)
        lay.addWidget(c)
        etapas["C"] = c

        # ---- D. Decodificación -------------------------------------------------
        d = _Seccion("D", "Decodificación por mayoría", "escudo", COLOR_RECUPERADO)
        d.fila("Errores residuales", str(r.errores_residuales), "medido",
               COLOR_RESIDUAL if r.errores_residuales else COLOR_RECUPERADO,
               "Bits de información decididos incorrectamente (excluye empates)")
        d.fila("Empates", f"{r.empates}" + ("  (imposibles con n impar)" if r.n % 2 else ""), "medido",
               COLOR_RESIDUAL if r.empates else C.TEXTO)
        if r.ber_con_codigo is None:
            d.fila("BER después de decodificar", NO_DISPONIBLE, "medido", C.TEXTO_TENUE,
                   "Ningún bit tuvo decisión: no hay denominador")
        else:
            d.fila("BER después de decodificar", formato_ber(r.ber_con_codigo), "medido",
                   COLOR_RESIDUAL if r.ber_con_codigo else COLOR_RECUPERADO,
                   f"{r.errores_residuales} errores / {r.bits_decididos} bits decididos (core.simulador)")
        d.fila_ancha("Posiciones de los errores residuales", _posiciones(m.posiciones_residuales),
                     "medido", COLOR_RESIDUAL if r.errores_residuales else C.TEXTO,
                     "Posición (desde 1) dentro de los bits originales")
        rec = m.texto_recuperado_visual
        if rec is None:
            d.fila_ancha("Texto recuperado", f"No disponible: {r.empates} bit(s) empatados («?») impiden "
                         "reconstruir los bytes", "medido", C.MORADO)
        else:
            d.fila_ancha("Texto recuperado" + ("" if r.utf8_valido else " (visualización segura)"),
                         texto_ajustable(rec), "medido",
                         COLOR_RECUPERADO if r.exito else (COLOR_RESIDUAL if r.utf8_valido else C.ERROR),
                         "" if r.utf8_valido else "«�» = byte no decodificable como UTF‑8")
        estado = ESTADOS_DUAL[m.estado]
        d.fila("Estado final", estado[0], "medido", estado[2], estado[4])
        d.texto(f"Proceso: cada bloque de n = {r.n} bits recibidos se reduce a un bit, el que más se "
                f"repite. Si un bloque tiene como máximo t = {r.t} inversiones la decisión es correcta; "
                f"con {r.t + 1} o más, la mayoría queda del lado equivocado.", C.TEXTO_TENUE)
        d.bits("Bits recuperados (verde = correcto, ámbar = error residual)",
               _html_bits(r.recuperado, r.bits_originales, C.TEXTO, COLOR_RESIDUAL, "#3D2E12",
                          COLOR_RECUPERADO, 8), r.recuperado, 4)
        cab_hex = QHBoxLayout()
        cab_hex.addWidget(etiqueta("Bytes recuperados (hexadecimal)", "TituloPaso"), 1)
        cab_hex.addWidget(boton_copiar(lambda: m.bytes_recuperados_hex, "Copiar los bytes"))
        d.derecha.addLayout(cab_hex)
        hexa = etiqueta(m.bytes_recuperados_hex[:1500] + (" …" if len(m.bytes_recuperados_hex) > 1500 else ""),
                        "Mono", ajustar=True)
        hexa.setStyleSheet(f"color: {C.TEXTO_SECUNDARIO}; font-size: 12px;")
        hexa.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        d.derecha.addWidget(hexa)
        lay.addWidget(d)
        etapas["D"] = d

        # ---- Inspector de bloques ---------------------------------------------
        v = _Seccion("▣", "Votación por mayoría, bloque a bloque", "binario", COLOR_ORIGINAL, columnas=False)
        v.texto("Original → Codificado → Recibido → Recuperado. Haz clic en un bloque o usa las flechas; "
                "los datos son los de esta transmisión (no se vuelve a simular).", C.TEXTO_TENUE, derecha=False)
        v.caja.addWidget(VisualizacionTransmision(m))
        lay.addWidget(v)
        etapas["V"] = v

        # ---- E. Fundamento teórico --------------------------------------------
        e = _Seccion("E", "Fundamento teórico frente a la simulación", "sigma", C.MORADO, columnas=False)
        e.caja.addWidget(_tabla_teoria(r))
        relacion = ("R ≤ C: el teorema de Shannon garantiza que existen códigos con error tan pequeño como "
                    "se quiera a esta tasa; la repetición no los alcanza, solo reduce el error a cambio de "
                    "redundancia." if par["tasa"] <= r.capacidad else
                    "R > C: a esta tasa ningún código puede lograr un error arbitrariamente pequeño.")
        e.texto(f"R = {par['tasa']:.3f} es una propiedad del código; C = {r.capacidad:.3f} lo es del canal. "
                + relacion, C.TEXTO_SECUNDARIO, derecha=False)
        e.texto("Una sola transmisión es una muestra aleatoria: su BER puede diferir de Pₑ sin contradecir "
                "la teoría. Para estimaciones estadísticas usa Análisis con muchos bits.", C.TEXTO_TENUE,
                derecha=False)
        lay.addWidget(e)
        etapas["E"] = e

        for boton_etapa, clave in self._botones_etapa:
            destino = etapas[clave]
            boton_etapa.clicked.connect(
                lambda _c=False, w=destino: self.area.verticalScrollBar().setValue(w.y() - 8))

        # ---- Pie ------------------------------------------------------------
        pie_marco = QFrame()
        pie_marco.setObjectName("PieInspector")
        pie_marco.setStyleSheet(f"QFrame#PieInspector {{ background: {C.FONDO_VENTANA};"
                                f" border-top: 1px solid {C.BORDE}; }}")
        pie = QHBoxLayout(pie_marco)
        pie.setContentsMargins(20, 10, 20, 10)
        pie.addWidget(etiqueta(f"n = {r.n} y p = {formato_p(r.p)} se guardaron con este mensaje: cambiar "
                               "el canal no modifica este resultado.", "Ayuda", ajustar=True), 1)
        comparar = QPushButton("  Comparar n = 3, 5, 7")
        comparar.setIcon(icono("grafica", C.TEXTO_SECUNDARIO, 15))
        comparar.setCursor(Qt.CursorShape.PointingHandCursor)
        comparar.setToolTip("Transmitir este mismo texto con n = 3, 5 y 7 y la misma p")
        comparar.clicked.connect(lambda: DialogoComparacion(m.texto_original, r.p, self).exec())
        pie.addWidget(comparar)
        completas = QPushButton("  Secuencias completas")
        completas.setIcon(icono("expandir", C.TEXTO_SECUNDARIO, 15))
        completas.setCursor(Qt.CursorShape.PointingHandCursor)
        completas.setToolTip("Todos los bits y el mapa de bloques")
        completas.clicked.connect(lambda: DialogoDetalle(r, self).exec())
        pie.addWidget(completas)
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("BotonPrimario")
        cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        cerrar.clicked.connect(self.accept)
        pie.addWidget(cerrar)
        raiz.addWidget(pie_marco)


# ===========================================================================
# Comparación de códigos
# ===========================================================================
class DialogoComparacion(QDialog):
    """Mismo mensaje y misma p con n = 3, 5 y 7 (ruido reproducible con semilla)."""

    def __init__(self, texto: str = "", p: float = servicio_dual.P_INICIAL, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comparar códigos — Chat Dual")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setSizeGripEnabled(True)
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1120, int(pantalla.width() * 0.92)), min(840, int(pantalla.height() * 0.92)))
        self.resultados: list[servicio.ResultadoTransmision] = []
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        area = AreaDesplazable(margenes=(20, 18, 20, 18), espaciado=14)
        raiz.addWidget(area)
        lay = area.layout_interno

        cab = QHBoxLayout()
        cab.setSpacing(12)
        cab.addWidget(icono_label("grafica", C.ROJO, 30))
        tit = QVBoxLayout()
        tit.setSpacing(0)
        tit.addWidget(etiqueta("Comparar códigos de repetición", "TituloPagina"))
        tit.addWidget(etiqueta("El mismo mensaje y la misma p, transmitidos con n = 3, 5 y 7",
                               "SubtituloPagina"))
        cab.addLayout(tit, 1)
        lay.addLayout(cab)

        # ---- Entrada ----------------------------------------------------------
        ent = _Seccion("1", "Experimento", "ajustes", C.AZUL, columnas=False)
        ent.caja.addWidget(etiqueta("MENSAJE", "Seccion"))
        self.campo_texto = QPlainTextEdit(texto)
        self.campo_texto.setObjectName("EntradaMensaje")
        self.campo_texto.setFixedHeight(66)
        self.campo_texto.setPlaceholderText("Escribe el mensaje a comparar…")
        ent.caja.addWidget(self.campo_texto)
        fila = QHBoxLayout()
        fila.setSpacing(14)
        col_p = QVBoxLayout()
        col_p.addWidget(etiqueta("PROBABILIDAD p", "Seccion"))
        self.control_p = ControlProbabilidad(p)
        col_p.addWidget(self.control_p)
        fila.addLayout(col_p, 3)
        col_s = QVBoxLayout()
        col_s.addWidget(etiqueta("SEMILLA DEL RUIDO", "Seccion"))
        self.semilla = QSpinBox()
        self.semilla.setRange(0, 999_999)
        self.semilla.setValue(servicio_dual.SEMILLA_INICIAL)
        self.semilla.setToolTip("Con la misma semilla, el mismo mensaje y la misma p se obtiene "
                                "exactamente el mismo ruido (experimento reproducible)")
        col_s.addWidget(self.semilla)
        fila.addLayout(col_s, 1)
        self.boton = QPushButton("  Ejecutar comparación")
        self.boton.setObjectName("BotonPrimario")
        self.boton.setIcon(icono("play", C.TEXTO, 16))
        self.boton.setCursor(Qt.CursorShape.PointingHandCursor)
        fila.addWidget(self.boton, 0, Qt.AlignmentFlag.AlignBottom)
        ent.caja.addLayout(fila)
        self.error = etiqueta("", "Error", ajustar=True)
        self.error.hide()
        ent.caja.addWidget(self.error)
        lay.addWidget(ent)

        # ---- Resultados -------------------------------------------------------
        res = _Seccion("2", "Resultados", "actividad", C.ROJO, columnas=False)
        self.tabla = QFrame()
        self.tabla.setObjectName("PanelEtapas")
        self.rejilla = QGridLayout(self.tabla)
        self.rejilla.setContentsMargins(14, 10, 14, 10)
        self.rejilla.setHorizontalSpacing(16)
        self.rejilla.setVerticalSpacing(8)
        res.caja.addWidget(self.tabla)
        self.grafica = GraficaBarras()
        self.grafica.setMinimumHeight(280)
        res.caja.addWidget(self.grafica)
        res.texto("Cada fila es UNA transmisión aleatoria: las diferencias entre ellas ilustran la tendencia "
                  "(más repeticiones → menos errores, pero menor tasa), no son conclusiones estadísticas. "
                  "Pₑ teórico es la referencia; para estimarlo con precisión se necesitan muchos más bits "
                  "(ver Análisis).", C.TEXTO_TENUE, derecha=False)
        lay.addWidget(res)
        lay.addStretch(1)

        self.boton.clicked.connect(self.ejecutar)
        if texto.strip():
            self.ejecutar()
        else:
            self._pintar_tabla()

    def ejecutar(self) -> None:
        texto = self.campo_texto.toPlainText().strip()
        try:
            self.resultados = servicio_dual.comparar_codigos(texto, self.control_p.valor(), self.semilla.value())
        except (ValueError, TypeError) as e:
            self.error.setText(str(e))
            self.error.show()
            return
        self.error.hide()
        self._pintar_tabla()

    def _pintar_tabla(self) -> None:
        while self.rejilla.count():
            item = self.rejilla.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        columnas = ("Código", "R", "d_min", "t", "Bits transmitidos", "Bits invertidos", "BER canal",
                    "BER residual", "Pₑ teórico", "Estado del mensaje")
        for col, texto in enumerate(columnas):
            lbl = etiqueta(texto.upper(), "Seccion")
            if texto in ("Pₑ teórico",):
                lbl.setStyleSheet(f"color: {C.MORADO};")
            self.rejilla.addWidget(lbl, 0, col)
        if not self.resultados:
            self.rejilla.addWidget(etiqueta("Escribe un mensaje y pulsa «Ejecutar comparación».", "Ayuda"),
                                   1, 0, 1, len(columnas))
            self.grafica.set_datos([], [], mensaje_vacio="Sin resultados todavía")
            return
        for k, r in enumerate(self.resultados, 1):
            par = r.parametros
            pe = r.error_residual_teorico
            estado = ESTADOS_DUAL[servicio_dual.estado_dual(r)]
            valores = (f"n = {r.n}", f"{par['tasa']:.3f}", str(par["distancia_minima"]),
                       str(par["errores_corregibles"]), str(len(r.codificado)), str(r.errores_canal),
                       formato_ber(r.ber_canal),
                       formato_ber(r.ber_con_codigo) if r.ber_con_codigo is not None else NO_DISPONIBLE,
                       formato_ber(pe) if pe is not None else NO_DISPONIBLE)
            for col, valor in enumerate(valores):
                v = etiqueta(valor, "Mono")
                if col == 8:
                    v.setStyleSheet(f"color: {C.MORADO};")
                elif col == 7:
                    v.setStyleSheet(f"color: {COLOR_RESIDUAL if r.ber_con_codigo else COLOR_RECUPERADO};")
                self.rejilla.addWidget(v, k, col)
            ind = IndicadorEstado(servicio_dual.estado_dual(r), propio=False)
            ind.setToolTip(estado[4])
            self.rejilla.addWidget(ind, k, len(valores))
        grupos = [f"n = {r.n}" for r in self.resultados]
        self.grafica.set_datos(grupos, [
            ("BER del canal (simulación)", COLOR_RUIDO, [r.ber_canal for r in self.resultados]),
            ("BER residual (simulación)", COLOR_RESIDUAL,
             [r.ber_con_codigo or 0.0 for r in self.resultados]),
            ("Pₑ teórico", C.MORADO, [r.error_residual_teorico or 0.0 for r in self.resultados]),
        ])


# ===========================================================================
# Vista
# ===========================================================================
class VistaChatDual(QWidget):
    def __init__(self, parent=None, ruta: Path | None = None):
        super().__init__(parent)
        self.almacen = servicio_dual.AlmacenChatDual(ruta)
        mensajes, self.aviso_carga = self.almacen.cargar()
        self.modelo = servicio_dual.ConversacionDual(mensajes)
        self._ultimos: tuple[int, float] | None = None
        self._aviso_guardado_mostrado = False

        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        cab = EncabezadoPagina("usuarios", "Chat Dual",
                               "Comunicación bidireccional A ⇄ B a través de un canal BSC con códigos de repetición")
        self.boton_comparar = QPushButton("  Comparar códigos")
        self.boton_comparar.setIcon(icono("grafica", C.TEXTO_SECUNDARIO, 16))
        self.boton_comparar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_comparar.setToolTip("Mismo mensaje y misma p con n = 3, 5 y 7")
        cab.agregar(self.boton_comparar)
        self.boton_nueva = QPushButton("  Nueva conversación")
        self.boton_nueva.setObjectName("BotonPrimario")
        self.boton_nueva.setIcon(icono("play", C.TEXTO, 16))
        self.boton_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_nueva.setToolTip("Archiva la conversación actual y empieza una vacía")
        cab.agregar(self.boton_nueva)
        caja.addWidget(cab)

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(16, 14, 16, 16)
        cuerpo.setSpacing(12)
        self.panel_a = PanelUsuario("A")
        self.panel_b = PanelUsuario("B")
        self.control = PanelControlDual()
        cuerpo.addWidget(self.panel_a, 1)
        cuerpo.addWidget(self.panel_b, 1)
        cuerpo.addWidget(self.control)
        caja.addLayout(cuerpo, 1)

        for panel in (self.panel_a, self.panel_b):
            panel.enviar_pedido.connect(self.enviar)
            panel.detalles_pedidos.connect(self.inspeccionar)
        self.control.parametros_cambiados.connect(lambda _n, _p: self.control.actualizar_monitor(self.modelo))
        self.boton_nueva.clicked.connect(self._confirmar_nueva)
        self.boton_comparar.clicked.connect(self.comparar)

        # Conversación guardada: se muestra tal cual se transmitió
        for m in self.modelo.mensajes:
            self._mostrar(m)
        self._actualizar_contadores()
        if self.aviso_carga:
            QTimer.singleShot(400, lambda: QMessageBox.warning(self, "Chat Dual", self.aviso_carga))

    def _panel(self, usuario: str) -> PanelUsuario:
        return self.panel_a if usuario == "A" else self.panel_b

    def _mostrar(self, m: MensajeDual) -> None:
        clave = (m.resultado.n, m.resultado.p)
        if self._ultimos is not None and self._ultimos != clave:
            nota = f"Canal reconfigurado: n = {clave[0]} · p = {formato_p(clave[1])}"
            self.panel_a.agregar_nota(nota)
            self.panel_b.agregar_nota(nota)
        self._ultimos = clave
        # El mismo resultado se muestra en ambos lados, en el mismo orden cronológico.
        self.panel_a.agregar(m)
        self.panel_b.agregar(m)

    def _actualizar_contadores(self) -> None:
        for usuario in ("A", "B"):
            self._panel(usuario).set_contadores(self.modelo.enviados_por(usuario),
                                                self.modelo.recibidos_por(usuario))
        self.control.actualizar_monitor(self.modelo)

    def _guardar(self) -> None:
        try:
            self.almacen.guardar(self.modelo.mensajes)
        except OSError as e:
            if not self._aviso_guardado_mostrado:
                self._aviso_guardado_mostrado = True
                QMessageBox.warning(self, "Chat Dual",
                                    f"No se pudo guardar la conversación en\n{self.almacen.ruta}\n\n{e}")

    def enviar(self, emisor: str, texto: str) -> MensajeDual | None:
        panel = self._panel(emisor)
        if not texto.strip():
            panel.alertar_vacio()
            return None
        try:
            m = self.modelo.enviar(emisor, texto.strip(), self.control.n(), self.control.p())
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, "Chat Dual", f"No se pudo transmitir el mensaje:\n{error}")
            return None
        panel.vaciar_entrada()
        self._mostrar(m)
        self._actualizar_contadores()
        self._guardar()
        QTimer.singleShot(0, panel.entrada.setFocus)
        return m

    def inspeccionar(self, m: MensajeDual) -> None:
        DialogoInspector(m, self.window()).exec()

    def comparar(self) -> None:
        ultimo = self.modelo.mensajes[-1].texto_original if self.modelo.mensajes else "Hola, ¿cómo estás?"
        DialogoComparacion(ultimo, self.control.p(), self.window()).exec()

    def _confirmar_nueva(self) -> None:
        if self.modelo.mensajes:
            r = QMessageBox.question(
                self, "Nueva conversación",
                "¿Empezar una conversación nueva?\n\nLa conversación actual no se borra: se archiva en\n"
                f"{self.almacen.ruta.parent / servicio_dual.CARPETA_ARCHIVO}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return
        self.nueva_conversacion()

    def nueva_conversacion(self) -> Path | None:
        try:
            destino = self.almacen.archivar(self.modelo.mensajes)
        except OSError as e:
            QMessageBox.warning(self, "Chat Dual", f"No se pudo archivar la conversación:\n{e}\n\n"
                                "Se conserva la conversación actual.")
            return None
        self.modelo.limpiar()
        self._ultimos = None
        for panel in (self.panel_a, self.panel_b):
            panel.limpiar()
        self._actualizar_contadores()
        return destino

    # Compatibilidad con el nombre anterior
    limpiar = nueva_conversacion
