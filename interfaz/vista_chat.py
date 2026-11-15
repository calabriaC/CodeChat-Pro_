"""Vista de Chat: conversación central + panel derecho de canal y métricas."""

from __future__ import annotations

import difflib
import html
from datetime import datetime

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from interfaz import servicio
from interfaz.componentes import (
    ESTADOS_TRANSMISION, AreaDesplazable, Chip, ChipEstado, ControlProbabilidad,
    EncabezadoPagina, EstadoVacio, SelectorN, Tarjeta, TarjetaDetalleTransmision,
    TarjetaMetrica, etiqueta, formato_ber, formato_p, icono_label, repulir, texto_ajustable,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import ANCHO_PANEL_DERECHO, C, qcolor, rgba
from interfaz.grafica import GraficaBER, Serie
from interfaz.iconos import icono, pixmap

LONGITUD_MAXIMA = 500
LINEAS_MAXIMAS_ENTRADA = 5


def _hora() -> str:
    return datetime.now().strftime("%H:%M")


def html_recuperado(original: str, recuperado: str) -> tuple[str, bool]:
    """HTML del texto recuperado con los fragmentos que difieren del original en rojo.

    Solo compara las dos cadenas para presentarlas; no interviene en la decodificación.
    Devuelve (html, hay_diferencias).
    """
    def seguro(fragmento: str) -> str:
        return html.escape(texto_ajustable(fragmento)).replace("\n", "<br>")

    partes, hay = [], False
    comparador = difflib.SequenceMatcher(None, original, recuperado, autojunk=False)
    for op, _i1, _i2, j1, j2 in comparador.get_opcodes():
        trozo = recuperado[j1:j2]
        if not trozo:
            hay = hay or op == "delete"
            continue
        if op == "equal":
            partes.append(seguro(trozo))
        else:
            hay = True
            partes.append(f'<span style="color:{C.ERROR}; background-color:#4A1222;'
                          f' font-weight:600;">{seguro(trozo)}</span>')
    return "".join(partes), hay


# ===========================================================================
# Entrada de mensajes
# ===========================================================================
class EntradaMensaje(QPlainTextEdit):
    """Campo multilínea: Enter envía, Shift+Enter inserta salto de línea; crece hasta 5 líneas."""

    enviar_pedido = Signal()
    foco_cambiado = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EntradaMensaje")
        self.setPlaceholderText("Escribe un mensaje…")
        self.setTabChangesFocus(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.document().setDocumentMargin(2)
        self.textChanged.connect(self._al_cambiar)
        QTimer.singleShot(0, self._ajustar_alto)

    def texto(self) -> str:
        return self.toPlainText()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.enviar_pedido.emit()
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.foco_cambiado.emit(True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.foco_cambiado.emit(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ajustar_alto()

    def _al_cambiar(self) -> None:
        texto = self.toPlainText()
        if len(texto) > LONGITUD_MAXIMA:
            cursor = self.textCursor()
            posicion = min(cursor.position(), LONGITUD_MAXIMA)
            self.blockSignals(True)
            self.setPlainText(texto[:LONGITUD_MAXIMA])
            self.blockSignals(False)
            cursor = self.textCursor()
            cursor.setPosition(posicion)
            self.setTextCursor(cursor)
        self._ajustar_alto()

    def _ajustar_alto(self) -> None:
        self.ensurePolished()
        lineas = int(self.document().documentLayout().documentSize().height()) or 1
        lineas = max(1, min(lineas, LINEAS_MAXIMAS_ENTRADA))
        alto = lineas * self.fontMetrics().lineSpacing() + 2 * 2 + 12 + 2
        self.setFixedHeight(alto)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded if lineas >= LINEAS_MAXIMAS_ENTRADA
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


# ===========================================================================
# Elementos de la conversación
# ===========================================================================
class _ConTextoAjustable:
    """Mezcla: da a la etiqueta principal su anchura natural sin superar el máximo."""

    _lbl: QLabel
    _texto_plano: str = ""
    _relleno = 36

    def ajustar_ancho(self, ancho_max: int) -> None:
        self._lbl.ensurePolished()
        fm = self._lbl.fontMetrics()
        texto = self._texto_plano or self._lbl.text()
        natural = max(fm.horizontalAdvance(linea) for linea in texto.split("\n")) + 6
        self._lbl.setMinimumWidth(max(60, min(natural, ancho_max - self._relleno)))


_TICKS = {
    "sin_errores": (C.VERDE, "Transmitido y recibido sin errores"),
    "corregido": (C.AZUL, "Transmitido: el receptor corrigió los errores del canal"),
    "residual": (C.ERROR, "Transmitido: el mensaje llegó con errores residuales"),
    "ambiguo": (C.AMBAR, "Transmitido: decodificación ambigua"),
}


class BurbujaEnviada(_ConTextoAjustable, QFrame):
    """Mensaje del emisor, alineado a la derecha, con parámetros, hora y estado."""

    def __init__(self, texto: str, n: int, p: float, parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaEnviada")
        self._texto_plano = texto
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 11, 14, 8)
        caja.setSpacing(5)
        self._lbl = lbl = etiqueta(texto_ajustable(texto), "TextoBurbuja", ajustar=True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(lbl)
        pie = QHBoxLayout()
        pie.setSpacing(6)
        pie.addStretch(1)
        parametros = etiqueta(f"n = {n} · p = {formato_p(p)}", "HoraBurbuja")
        parametros.setToolTip("Configuración del canal usada en este envío")
        pie.addWidget(parametros)
        pie.addWidget(etiqueta("·", "HoraBurbuja"))
        pie.addWidget(etiqueta(_hora(), "HoraBurbuja"))
        self._estado = QLabel()
        self._estado.setFixedSize(17, 17)
        pie.addWidget(self._estado)
        caja.addLayout(pie)
        self.set_estado("enviando")

    def set_estado(self, estado: str, estado_transmision: str | None = None) -> None:
        if estado == "enviando":
            nombre, color, ayuda = "reloj", C.TEXTO_SECUNDARIO, "Transmitiendo por el canal BSC…"
        elif estado == "error":
            nombre, color, ayuda = "alerta", C.AMBAR, "No se pudo transmitir"
        else:
            nombre = "doble_check"
            color, ayuda = _TICKS.get(estado_transmision, (C.TEXTO, "Transmitido"))
        self._estado.setPixmap(pixmap(nombre, color, 16, 2.4))
        self._estado.setToolTip(ayuda)


class BurbujaReceptor(_ConTextoAjustable, QFrame):
    """Mensaje recuperado por el receptor, alineado a la izquierda."""

    detalles_alternados = Signal(bool)

    def __init__(self, r: servicio.ResultadoTransmision, parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaRecibida")
        self._texto_plano = r.texto_recuperado or ""
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 11, 14, 9)
        caja.setSpacing(6)

        cab = QHBoxLayout()
        cab.setSpacing(10)
        cab.addWidget(etiqueta("Receptor · mensaje recuperado", "AutorBurbuja"))
        cab.addStretch(1)
        cab.addWidget(ChipEstado(r.estado))
        caja.addLayout(cab)

        contenido, hay_diferencias = html_recuperado(r.texto or "", r.texto_recuperado or "")
        self._lbl = lbl = QLabel(contenido or "∅")
        lbl.setObjectName("TextoBurbuja")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(lbl)
        if hay_diferencias:
            nota = etiqueta("Los fragmentos resaltados no coinciden con el mensaje enviado.",
                            "EtiquetaTenue", ajustar=True)
            caja.addWidget(nota)

        pie = QHBoxLayout()
        pie.setSpacing(8)
        self.boton_detalles = QPushButton("  Detalles de transmisión")
        self.boton_detalles.setObjectName("BotonDetalles")
        self.boton_detalles.setCheckable(True)
        self.boton_detalles.setIcon(icono("antena", C.TEXTO_SECUNDARIO, 14))
        self.boton_detalles.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_detalles.setToolTip("Mostrar u ocultar todas las etapas de la transmisión")
        self.boton_detalles.toggled.connect(self._alternar)
        pie.addWidget(self.boton_detalles)
        pie.addStretch(1)
        pie.addWidget(etiqueta(_hora(), "HoraBurbuja"))
        caja.addLayout(pie)

    def _alternar(self, activo: bool) -> None:
        self.boton_detalles.setText("  Ocultar detalles" if activo else "  Detalles de transmisión")
        self.detalles_alternados.emit(activo)


class BurbujaSistema(_ConTextoAjustable, QFrame):
    """Aviso del sistema (p. ej. error de validación del núcleo)."""

    def __init__(self, texto: str, parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaSistema")
        self._texto_plano = texto
        caja = QHBoxLayout(self)
        caja.setContentsMargins(14, 10, 14, 10)
        caja.setSpacing(10)
        caja.addWidget(icono_label("alerta", C.AMBAR, 18), 0, Qt.AlignmentFlag.AlignTop)
        self._lbl = lbl = etiqueta(texto, "TextoBurbuja", ajustar=True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(lbl, 1)


class Avatar(QLabel):
    def __init__(self, nombre_icono: str = "bot", parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPixmap(pixmap(nombre_icono, C.TEXTO, 20))
        self.setToolTip("Receptor CodeChat Pro")
        self.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {C.ROJO_SECUNDARIO}, stop:1 #3A0E1C);"
            f" border: 1px solid {rgba(C.ROJO, 0.55)}; border-radius: 20px;")


class IndicadorEscritura(QFrame):
    """Tres puntos animados mientras el mensaje atraviesa el canal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaRecibida")
        self.setFixedSize(QSize(196, 44))
        self._fase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._avanzar)
        self._timer.start(160)

    def _avanzar(self):
        self._fase = (self._fase + 1) % 6
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(3):
            activo = (self._fase // 2) == i
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor(C.ROJO if activo else C.TEXTO_SECUNDARIO, 255 if activo else 110))
            p.drawEllipse(QRectF(18 + i * 13, 18 - (2 if activo else 0), 8, 8))
        p.setPen(QColor(C.TEXTO_SECUNDARIO))
        p.setFont(self.font())
        p.drawText(QRectF(64, 0, 130, self.height()), Qt.AlignmentFlag.AlignVCenter,
                   "Atravesando el canal…")
        p.end()


class Conversacion(QScrollArea):
    """Lista desplazable de mensajes con anchura máxima adaptable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido = QWidget()
        contenido.setObjectName("Pagina")
        self._lista = QVBoxLayout(contenido)
        self._lista.setContentsMargins(28, 20, 28, 20)
        self._lista.setSpacing(14)
        self._lista.addStretch(1)
        self.setWidget(contenido)
        self._limitados: list[tuple[QWidget, float]] = []
        self._seguir_final = False
        self._animaciones: list[QPropertyAnimation] = []
        barra = self.verticalScrollBar()
        barra.rangeChanged.connect(self._al_cambiar_rango)
        barra.valueChanged.connect(lambda _v: self._actualizar_boton_bajar())

        # Botón flotante «ir al último mensaje»
        self.boton_bajar = QPushButton(self)
        self.boton_bajar.setObjectName("BotonFlotante")
        self.boton_bajar.setIcon(icono("flecha_abajo", C.TEXTO, 18))
        self.boton_bajar.setFixedSize(40, 40)
        self.boton_bajar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_bajar.setToolTip("Ir al último mensaje")
        self.boton_bajar.setStyleSheet(
            f"QPushButton#BotonFlotante {{ background: {C.SUPERFICIE_ALTA}; border: 1px solid {C.BORDE};"
            f" border-radius: 20px; padding: 0; }}"
            f"QPushButton#BotonFlotante:hover {{ border-color: {C.ROJO}; }}")
        self.boton_bajar.clicked.connect(self.ir_al_final)
        self.boton_bajar.hide()

    # ---- añadir elementos ---------------------------------------------
    def _insertar(self, widget: QWidget) -> None:
        self._lista.insertWidget(self._lista.count() - 1, widget)
        self._aparecer(widget)
        self._seguir_hasta_estable()

    def _seguir_hasta_estable(self) -> None:
        self._seguir_final = True
        QTimer.singleShot(450, self._dejar_de_seguir)

    def _dejar_de_seguir(self) -> None:
        self._seguir_final = False

    def _aparecer(self, widget: QWidget) -> None:
        efecto = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(efecto)
        anim = QPropertyAnimation(efecto, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def terminar():
            widget.setGraphicsEffect(None)
            if anim in self._animaciones:
                self._animaciones.remove(anim)

        anim.finished.connect(terminar)
        self._animaciones.append(anim)
        anim.start()

    def _limitar(self, widget: QWidget, proporcion: float) -> None:
        self._limitados.append((widget, proporcion))
        self._aplicar_limite(widget, proporcion, self.viewport().width())

    @staticmethod
    def _aplicar_limite(widget: QWidget, proporcion: float, ancho: int) -> None:
        maximo = max(280, int(ancho * proporcion))
        widget.setMaximumWidth(maximo)
        if isinstance(widget, _ConTextoAjustable):
            widget.ajustar_ancho(maximo)

    def agregar_separador(self, texto: str) -> None:
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(0, 4, 0, 4)
        fila.addStretch(1)
        fila.addWidget(etiqueta(texto, "SeparadorFecha"))
        fila.addStretch(1)
        self._insertar(envoltura)

    def agregar_enviado(self, texto: str, n: int, p: float) -> BurbujaEnviada:
        burbuja = BurbujaEnviada(texto, n, p)
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(80, 0, 0, 0)
        fila.addStretch(1)
        fila.addWidget(burbuja)
        self._limitar(burbuja, 0.62)
        self._insertar(envoltura)
        return burbuja

    def agregar_izquierda(self, widget: QWidget, avatar: bool = True) -> tuple[QWidget, QVBoxLayout]:
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(0, 0, 40, 0)
        fila.setSpacing(12)
        if avatar:
            fila.addWidget(Avatar(), 0, Qt.AlignmentFlag.AlignTop)
        columna = QVBoxLayout()
        columna.setSpacing(10)
        linea = QHBoxLayout()
        linea.setContentsMargins(0, 0, 0, 0)
        linea.addWidget(widget)
        linea.addStretch(1)
        columna.addLayout(linea)
        self._limitar(widget, 0.66)
        fila.addLayout(columna, 1)
        self._insertar(envoltura)
        return envoltura, columna

    def agregar_recepcion(self, r: servicio.ResultadoTransmision) -> BurbujaReceptor:
        burbuja = BurbujaReceptor(r)
        _envoltura, columna = self.agregar_izquierda(burbuja)
        estado = {"tarjeta": None}

        def alternar(activo: bool) -> None:
            tarjeta = estado["tarjeta"]
            if tarjeta is None:
                if not activo:
                    return
                # Se construye solo al abrirla: evita renderizar miles de bits de antemano.
                tarjeta = TarjetaDetalleTransmision(r, compacta=True)
                estado["tarjeta"] = tarjeta
                columna.addWidget(tarjeta)
                self._limitar(tarjeta, 0.80)
                self._aparecer(tarjeta)
            tarjeta.setVisible(activo)
            if activo:
                QTimer.singleShot(60, lambda: self.ensureWidgetVisible(burbuja, 0, 12))

        burbuja.detalles_alternados.connect(alternar)
        return burbuja

    def quitar(self, widget: QWidget) -> None:
        self._limitados = [(w, prop) for w, prop in self._limitados if w is not widget
                           and not widget.isAncestorOf(w)]
        self._lista.removeWidget(widget)
        widget.deleteLater()

    def limpiar(self) -> None:
        while self._lista.count() > 1:
            item = self._lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._limitados.clear()

    # ---- desplazamiento ------------------------------------------------
    def ir_al_final(self) -> None:
        barra = self.verticalScrollBar()
        barra.setValue(barra.maximum())

    def _al_cambiar_rango(self, _min, maximo):
        if self._seguir_final:
            self.verticalScrollBar().setValue(maximo)
        self._actualizar_boton_bajar()

    def _actualizar_boton_bajar(self) -> None:
        barra = self.verticalScrollBar()
        self.boton_bajar.setVisible(barra.maximum() - barra.value() > 160)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        ancho = self.viewport().width()
        for w, proporcion in self._limitados:
            self._aplicar_limite(w, proporcion, ancho)
        self.boton_bajar.move(self.viewport().width() - 56, self.viewport().height() - 54)
        self.boton_bajar.raise_()


# ===========================================================================
# Panel derecho
# ===========================================================================
class PanelCanal(AreaDesplazable):
    """Configuración del canal, métricas y gráfica BER frente a la tasa."""

    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(margenes=(0, 18, 14, 18), espaciado=14, parent=parent)
        self.estado = estado
        self.setMinimumWidth(ANCHO_PANEL_DERECHO - 64)
        self.setMaximumWidth(ANCHO_PANEL_DERECHO + 30)
        caja = self.layout_interno

        # ---- Configuración --------------------------------------------
        config = Tarjeta("Configuración del canal", "ajustes", "Canal binario simétrico (BSC)")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(12)
        rejilla.setVerticalSpacing(4)
        rejilla.addWidget(etiqueta("Código de repetición (n)", "Etiqueta"), 0, 0)
        self.selector_n = SelectorN(estado.n)
        rejilla.addWidget(self.selector_n, 0, 1)
        rejilla.addWidget(etiqueta("Cada bit se envía n veces · solo n impar", "Ayuda"), 1, 0, 1, 2)
        rejilla.setRowMinimumHeight(2, 10)
        fila_p = QHBoxLayout()
        fila_p.addWidget(etiqueta("Probabilidad de error (p)", "Etiqueta"), 1)
        rejilla.addLayout(fila_p, 3, 0, 1, 2)
        self.control_p = ControlProbabilidad(estado.p)
        rejilla.addWidget(self.control_p, 4, 0, 1, 2)
        rejilla.addWidget(etiqueta("Probabilidad de que el canal invierta cada bit (0 – 0.5)",
                                   "Ayuda", ajustar=True), 5, 0, 1, 2)
        rejilla.setColumnStretch(0, 1)
        config.cuerpo.addLayout(rejilla)
        self.boton_transmitir = QPushButton("  Transmitir mensaje")
        self.boton_transmitir.setObjectName("BotonPrimario")
        self.boton_transmitir.setIcon(icono("play", C.TEXTO, 18))
        self.boton_transmitir.setIconSize(QSize(18, 18))
        self.boton_transmitir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_transmitir.setToolTip("Transmite el texto escrito en el campo de mensaje")
        config.cuerpo.addWidget(self.boton_transmitir)
        caja.addWidget(config)

        # ---- Métricas --------------------------------------------------
        metricas = Tarjeta("Métricas del código", "analisis", "Valores calculados por el núcleo")
        rej = QGridLayout()
        rej.setSpacing(10)
        self.m_n = TarjetaMetrica("Longitud n", C.ROJO, "Bits enviados por cada bit de información.")
        self.m_dmin = TarjetaMetrica("Distancia mínima d_min", C.MORADO,
                                     "d_min = n para un código de repetición.")
        self.m_t = TarjetaMetrica("Errores corregibles t", C.ROJO, "t = ⌊(d_min − 1) / 2⌋")
        self.m_r = TarjetaMetrica("Tasa R = k/n", C.AZUL, "Fracción de bits útiles transmitidos.")
        self.m_ber = TarjetaMetrica("BER (último envío)", C.AMBAR,
                                    "Tasa de error de bits medida en la última transmisión del chat.")
        self.m_cap = TarjetaMetrica("Capacidad de Shannon", C.VERDE, "C = 1 − H₂(p)")
        for i, m in enumerate((self.m_n, self.m_dmin, self.m_t, self.m_r, self.m_ber, self.m_cap)):
            rej.addWidget(m, i // 2, i % 2)
        rej.setColumnStretch(0, 1)
        rej.setColumnStretch(1, 1)
        metricas.cuerpo.addLayout(rej)
        caja.addWidget(metricas)

        # ---- Gráfica ---------------------------------------------------
        tarjeta_grafica = Tarjeta("BER frente a la tasa", "grafica",
                                  "Curva teórica para el p actual y BER medida en el chat")
        self.grafica = GraficaBER()
        self.grafica.setMinimumHeight(280)
        tarjeta_grafica.cuerpo.addWidget(self.grafica)
        caja.addWidget(tarjeta_grafica)
        caja.addStretch(1)

        # ---- Señales ---------------------------------------------------
        self.selector_n.n_cambiado.connect(estado.establecer_n)
        self.control_p.valor_cambiado.connect(estado.establecer_p)
        estado.configuracion_cambiada.connect(self._al_configurar)
        estado.transmision_registrada.connect(lambda _r: self._refrescar())
        estado.historial_limpiado.connect(self._refrescar)
        self._refrescar()

    def _al_configurar(self, n: int, p: float) -> None:
        self.selector_n.set_n(n)
        if abs(self.control_p.valor() - p) > 1e-9:
            self.control_p.set_valor(p)
        self._refrescar()

    def _refrescar(self) -> None:
        n, p = self.estado.n, self.estado.p
        par = servicio.parametros(n)
        self.m_n.set_valor(str(par["n"]), f"k = {par['k']}, M = {par['M']}")
        self.m_dmin.set_valor(str(par["distancia_minima"]), f"detecta {par['errores_detectables']} errores")
        self.m_t.set_valor(str(par["errores_corregibles"]), "por bloque de n bits")
        self.m_r.set_valor(f"{par['tasa']:.3f}", "bits útiles por bit enviado")
        cap = servicio.capacidad(p)
        self.m_cap.set_valor(f"{cap:.3f}", f"bits/uso con p = {formato_p(p)}")

        chat = [r for r in self.estado.historial if r.origen == "chat"]
        if chat:
            u = chat[-1]
            self.m_ber.set_valor(formato_ber(u.ber_con_codigo),
                                 f"sin código: {formato_ber(u.ber_sin_codigo)}")
            self.m_ber.setToolTip(f"Última transmisión del chat (n = {u.n}, p = {formato_p(u.p)}).")
        else:
            self.m_ber.set_valor(None, "Envía un mensaje para medirla")

        # Gráfica: curva teórica (core) + BER medidas en el chat con el mismo p
        medidos = [r for r in chat if abs(r.p - p) < 1e-9]
        por_n: dict[int, list[float]] = {}
        for r in medidos:
            por_n.setdefault(r.n, []).append(r.ber_con_codigo)
        exp_con = sorted((1 / k, sum(v) / len(v)) for k, v in por_n.items())
        etiquetas = [f"n={round(1 / x)}" for x, _ in exp_con]
        series = [Serie("Teórico con código", C.AZUL, servicio.curva_teorica(p))]
        if exp_con:
            series.append(Serie("Medido con código", C.AMBAR, exp_con, tipo="puntos", etiquetas=etiquetas))
            sin = [r.ber_sin_codigo for r in medidos]
            series.append(Serie("Medido sin código", C.ROJO, [(1.0, sum(sin) / len(sin))], tipo="puntos"))
        self.grafica.set_datos(series, vertical=(cap, "C"))


# ===========================================================================
# Vista completa
# ===========================================================================
def _pasos_bienvenida() -> QWidget:
    w = QWidget()
    fila = QHBoxLayout(w)
    fila.setContentsMargins(0, 0, 0, 0)
    fila.setSpacing(10)
    fila.addStretch(1)
    for nombre_ic, titulo, texto in (("texto", "1 · Escribe", "Tu texto se convierte a bits UTF‑8"),
                                     ("antena", "2 · Transmite", "Se repite n veces y cruza el BSC"),
                                     ("escudo", "3 · Recupera", "La mayoría corrige los errores")):
        tarjeta = QFrame()
        tarjeta.setObjectName("TarjetaInterna")
        tarjeta.setFixedWidth(178)
        caja = QVBoxLayout(tarjeta)
        caja.setContentsMargins(14, 12, 14, 12)
        caja.setSpacing(4)
        caja.addWidget(icono_label(nombre_ic, C.ROJO, 20))
        caja.addWidget(etiqueta(titulo, "Etiqueta"))
        caja.addWidget(etiqueta(texto, "EtiquetaTenue", ajustar=True))
        caja.addStretch(1)
        fila.addWidget(tarjeta)
    fila.addStretch(1)
    return w


class VistaChat(QWidget):
    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        self._ocupado = False
        self._hay_mensajes = False

        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(16)

        # ---- Columna central ------------------------------------------
        centro = QFrame()
        centro.setObjectName("Pagina")
        col = QVBoxLayout(centro)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        cabecera = EncabezadoPagina(
            "chat", "Chat",
            "Mensajería protegida con códigos de repetición sobre un canal BSC")
        self.chip_canal = Chip("", "info")
        cabecera.agregar(self.chip_canal)
        self.boton_limpiar = QPushButton()
        self.boton_limpiar.setObjectName("BotonFantasma")
        self.boton_limpiar.setIcon(icono("papelera", C.TEXTO_SECUNDARIO, 18))
        self.boton_limpiar.setToolTip("Vaciar la conversación (el historial se conserva)")
        self.boton_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        cabecera.agregar(self.boton_limpiar)
        col.addWidget(cabecera)

        self.pila = QStackedWidget()
        self.vacio = EstadoVacio(
            "chat", "Tu conversación empieza aquí",
            "Envía un mensaje y observa cómo se codifica, cómo el canal introduce errores "
            "y cómo el receptor los corrige.",
            ["Hola, CodeChat Pro 👋", "Teoría de códigos", "¡Perfecto! 🚀"],
            extra=_pasos_bienvenida())
        self.conversacion = Conversacion()
        self.pila.addWidget(self.vacio)
        self.pila.addWidget(self.conversacion)
        col.addWidget(self.pila, 1)

        self.barra = QFrame()
        self.barra.setObjectName("BarraEntrada")
        fila_barra = QHBoxLayout(self.barra)
        fila_barra.setContentsMargins(16, 8, 8, 8)
        fila_barra.setSpacing(10)
        fila_barra.addWidget(icono_label("binario", C.TEXTO_TENUE, 20), 0, Qt.AlignmentFlag.AlignVCenter)
        self.entrada = EntradaMensaje()
        fila_barra.addWidget(self.entrada, 1, Qt.AlignmentFlag.AlignVCenter)
        self.boton_enviar = QPushButton()
        self.boton_enviar.setObjectName("BotonEnviar")
        self.boton_enviar.setIcon(icono("enviar", C.TEXTO, 22))
        self.boton_enviar.setIconSize(QSize(22, 22))
        self.boton_enviar.setFixedSize(50, 46)
        self.boton_enviar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_enviar.setToolTip("Transmitir (Enter)")
        fila_barra.addWidget(self.boton_enviar, 0, Qt.AlignmentFlag.AlignBottom)

        envoltura_barra = QWidget()
        eb = QVBoxLayout(envoltura_barra)
        eb.setContentsMargins(18, 8, 0, 12)
        eb.setSpacing(6)
        eb.addWidget(self.barra)
        pie = QHBoxLayout()
        pie.setContentsMargins(8, 0, 8, 0)
        pie.addWidget(etiqueta("Enter para enviar · Shift + Enter para nueva línea", "EtiquetaTenue"))
        pie.addStretch(1)
        self.contador = etiqueta(f"0/{LONGITUD_MAXIMA}", "EtiquetaTenue")
        pie.addWidget(self.contador)
        eb.addLayout(pie)
        col.addWidget(envoltura_barra)
        fila.addWidget(centro, 1)

        # ---- Panel derecho --------------------------------------------
        self.panel = PanelCanal(estado)
        fila.addWidget(self.panel)

        # ---- Señales --------------------------------------------------
        self.entrada.enviar_pedido.connect(self.enviar)
        self.entrada.textChanged.connect(self._al_escribir)
        self.entrada.foco_cambiado.connect(self._al_cambiar_foco)
        self.boton_enviar.clicked.connect(self.enviar)
        self.panel.boton_transmitir.clicked.connect(self.enviar)
        self.boton_limpiar.clicked.connect(self.limpiar)
        self.vacio.sugerencia_elegida.connect(self._usar_sugerencia)
        estado.configuracion_cambiada.connect(lambda _n, _p: self._actualizar_chip())
        self._actualizar_chip()

    # ---- interacción ------------------------------------------------------
    def _actualizar_chip(self) -> None:
        self.chip_canal.setText(f"Canal BSC · n = {self.estado.n} · p = {formato_p(self.estado.p)}")

    def _al_escribir(self) -> None:
        self.contador.setText(f"{len(self.entrada.texto())}/{LONGITUD_MAXIMA}")
        if self.barra.property("alerta"):
            self.barra.setProperty("alerta", False)
            repulir(self.barra)

    def _al_cambiar_foco(self, foco: bool) -> None:
        self.barra.setProperty("foco", foco)
        repulir(self.barra)

    def _usar_sugerencia(self, texto: str) -> None:
        self.entrada.setPlainText(texto)
        self.entrada.moveCursor(self.entrada.textCursor().MoveOperation.End)
        self.entrada.setFocus()

    def _alertar_vacio(self) -> None:
        self.barra.setProperty("alerta", True)
        repulir(self.barra)
        self.entrada.setPlaceholderText("Escribe un mensaje para transmitirlo…")
        self.entrada.setFocus()

    def enviar(self) -> None:
        texto = self.entrada.texto().strip()
        if self._ocupado:
            return
        if not texto:
            self._alertar_vacio()
            return
        self._ocupado = True
        self.boton_enviar.setEnabled(False)
        self.panel.boton_transmitir.setEnabled(False)
        self.entrada.clear()
        self.entrada.setPlaceholderText("Escribe un mensaje…")

        if not self._hay_mensajes:
            self._hay_mensajes = True
            self.pila.setCurrentWidget(self.conversacion)
            self.conversacion.agregar_separador("Hoy")

        n, p = self.estado.n, self.estado.p
        burbuja = self.conversacion.agregar_enviado(texto, n, p)
        indicador, _col = self.conversacion.agregar_izquierda(IndicadorEscritura())
        QTimer.singleShot(650, lambda: self._completar(texto, n, p, burbuja, indicador))

    def _completar(self, texto, n, p, burbuja: BurbujaEnviada, indicador: QWidget) -> None:
        self.conversacion.quitar(indicador)
        try:
            r = servicio.transmitir_texto(texto, n, p)
        except (ValueError, TypeError) as error:
            burbuja.set_estado("error")
            self.conversacion.agregar_izquierda(
                BurbujaSistema(f"No se pudo transmitir el mensaje: {error}"))
        else:
            burbuja.set_estado("entregado", r.estado)
            self.estado.registrar(r)
            self.conversacion.agregar_recepcion(r)
        self._ocupado = False
        self.boton_enviar.setEnabled(True)
        self.panel.boton_transmitir.setEnabled(True)
        self.entrada.setFocus()

    def limpiar(self) -> None:
        if self._ocupado:
            return
        self.conversacion.limpiar()
        self._hay_mensajes = False
        self.pila.setCurrentWidget(self.vacio)


# Exportado para otras vistas que quieran describir estados.
__all__ = ["VistaChat", "ESTADOS_TRANSMISION"]
