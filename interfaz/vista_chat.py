"""Vista de Chat: conversación central + panel derecho de canal y métricas."""

from __future__ import annotations

import difflib
import html
from datetime import datetime

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from pathlib import Path

from interfaz import persistencia, servicio
from interfaz.componentes import (
    ESTADOS_TRANSMISION, AreaDesplazable, ControlProbabilidad, EstadoVacio, EtiquetaRecortada,
    FlujoLayout,
    SelectorN,
    TarjetaDetalleTransmision, etiqueta, formato_ber, formato_p, icono_label, pixmap_logo, repulir,
    separador, texto_ajustable,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import ANCHO_PANEL_DERECHO, C, qcolor, rgba
from interfaz.grafica import GraficaBER, GraficaTasas, Serie
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


def _bits_resumidos(bits: str, n: int, referencia: str | None = None, max_car: int = 34) -> str:
    """Primeros grupos de una secuencia (HTML), con los bits alterados en rojo y «…» si se recorta."""
    grupo = n if n > 1 else 8
    grupos = max(2, max_car // (grupo + 1))
    limite = min(len(bits), grupos * grupo)
    partes = []
    for i in range(0, limite, grupo):
        trozo = []
        for j in range(i, min(i + grupo, limite)):
            b = bits[j]
            if referencia is not None and j < len(referencia) and referencia[j] != b:
                trozo.append(f"<span style='color:{C.ERROR}; font-weight:700;'>{b}</span>")
            else:
                trozo.append(b)
        partes.append("".join(trozo))
    texto = " ".join(partes)
    return texto + (" …" if limite < len(bits) else "")


def _caja_valor(contenido: str, color: str | None = None, envolver: bool = False,
                fondo: str | None = None, borde: str | None = None) -> QLabel:
    lbl = QLabel(contenido)
    lbl.setObjectName("CajaValor")
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setWordWrap(envolver)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if not envolver:
        lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lbl.setMinimumWidth(90)
    estilo = []
    if color:
        estilo.append(f"color: {color};")
    if fondo:
        estilo.append(f"background: {fondo};")
    if borde:
        estilo.append(f"border-color: {borde};")
    if estilo:
        lbl.setStyleSheet("QLabel#CajaValor { " + " ".join(estilo) + " }")
    return lbl


def _icono_fila(nombre: str, color: str = C.TEXTO_SECUNDARIO) -> QLabel:
    lbl = QLabel()
    lbl.setFixedSize(30, 30)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setPixmap(pixmap(nombre, color, 16))
    lbl.setStyleSheet(f"background: {C.CAMPO}; border: 1px solid {C.BORDE_SUAVE}; border-radius: 8px;")
    return lbl


class _FilaDato(QFrame):
    """«Etiqueta: valor» compacto del panel de estado."""

    def __init__(self, nombre: str, valor: str, color: str = C.TEXTO, parent=None):
        super().__init__(parent)
        self.setObjectName("FilaDato")
        self.setStyleSheet(f"QFrame#FilaDato {{ background: {C.CAMPO}; border: 1px solid {C.BORDE_SUAVE};"
                           " border-radius: 7px; }")
        fila = QHBoxLayout(self)
        fila.setContentsMargins(10, 5, 10, 5)
        fila.setSpacing(8)
        n = etiqueta(nombre, "EtiquetaSecundaria")
        n.setStyleSheet("font-size: 12px;")
        fila.addWidget(n)
        fila.addStretch(1)
        v = etiqueta(valor, "Mono")
        v.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700;")
        fila.addWidget(v)


_RESULTADO = {
    "sin_errores": ("exito", C.VERDE, "Recuperación\ncorrecta"),
    "corregido": ("exito", C.VERDE, "Recuperación\ncorrecta"),
    "residual": ("fallo", C.ERROR, "Recuperación\ncon errores"),
    "ambiguo": ("alerta", C.AMBAR, "Decodificación\nambigua"),
}


class BurbujaReceptor(QFrame):
    """Tarjeta «Transmisión completada»: etapas del mensaje y estado de la recuperación."""

    detalles_alternados = Signal(bool)

    def __init__(self, r: servicio.ResultadoTransmision, parent=None):
        super().__init__(parent)
        self.resultado = r
        self.setObjectName("TarjetaTransmision")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 14, 18, 12)
        caja.setSpacing(12)

        # ---- Cabecera --------------------------------------------------
        cab = QHBoxLayout()
        cab.setSpacing(10)
        cab.addWidget(icono_label("antena", C.TEXTO_SECUNDARIO, 22))
        cab.addWidget(etiqueta("Transmisión completada", "AutorBurbuja"))
        cab.addStretch(1)
        cab.addWidget(etiqueta(_hora(), "HoraBurbuja"))
        caja.addLayout(cab)

        # ---- Cuerpo: etapas + estado -----------------------------------
        self._cuerpo = cuerpo = QHBoxLayout()
        cuerpo.setSpacing(12)
        etapas = QFrame()
        etapas.setObjectName("PanelEtapas")
        rej = QGridLayout(etapas)
        rej.setContentsMargins(14, 12, 14, 12)
        rej.setHorizontalSpacing(12)
        rej.setVerticalSpacing(9)
        rej.setColumnStretch(2, 1)

        if r.hay_empates:
            contenido_rec, hay_diferencias = "", False
        else:
            contenido_rec, hay_diferencias = html_recuperado(r.texto or "", r.texto_recuperado or "")
        estado_ic, color_estado, texto_estado = _RESULTADO[r.estado]

        filas = [
            ("texto", "Mensaje original:",
             _caja_valor(f"“{html.escape(texto_ajustable(r.texto or ''))}”", envolver=True)),
            ("codigo", f"Bits codificados (n = {r.n}, k = {r.parametros['k']}):",
             _caja_valor(_bits_resumidos(r.codificado, r.n), envolver=True)),
            ("actividad", f"Bits recibidos (BSC, p = {formato_p(r.p)}):",
             _caja_valor(_bits_resumidos(r.recibido, r.n, r.codificado), envolver=True)),
        ]
        if r.hay_empates:
            recuperado = _caja_valor(f"Ambiguo: {r.empates} bit(s) empatados — no se reconstruye el texto",
                                     C.AMBAR, True, rgba(C.AMBAR, 0.08), rgba(C.AMBAR, 0.35))
        elif r.exito:
            recuperado = _caja_valor(f"“{contenido_rec}”", C.VERDE, True, rgba(C.VERDE, 0.08),
                                     rgba(C.VERDE, 0.35))
        else:
            recuperado = _caja_valor(f"“{contenido_rec or '∅'}”", C.TEXTO, True, rgba(C.ERROR, 0.08),
                                     rgba(C.ERROR, 0.35))
        filas.append((estado_ic, "Mensaje recuperado:", recuperado))
        for i, (ic, nombre, valor) in enumerate(filas):
            rej.addWidget(_icono_fila(ic, color_estado if i == 3 else C.TEXTO_SECUNDARIO), i, 0,
                          Qt.AlignmentFlag.AlignTop)
            lbl = etiqueta(nombre, "Etiqueta", ajustar=True)
            lbl.setMinimumWidth(120)
            lbl.setMaximumWidth(210)
            rej.addWidget(lbl, i, 1, Qt.AlignmentFlag.AlignVCenter)
            rej.addWidget(valor, i, 2)
        cuerpo.addWidget(etapas, 1)

        self._panel_estado = panel = QFrame()
        panel.setObjectName("PanelEstado")
        panel.setFixedWidth(206)
        col = QVBoxLayout(panel)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(7)
        cab_estado = QHBoxLayout()
        cab_estado.setSpacing(10)
        cab_estado.addWidget(icono_label(estado_ic, color_estado, 30), 0, Qt.AlignmentFlag.AlignTop)
        titulo_estado = QLabel(texto_estado)
        titulo_estado.setStyleSheet(f"color: {color_estado}; font-size: 15px; font-weight: 700;")
        cab_estado.addWidget(titulo_estado, 1)
        col.addLayout(cab_estado)
        col.addSpacing(2)
        col.addWidget(_FilaDato("Bloques corregidos:", str(r.bloques_corregidos), C.VERDE))
        col.addWidget(_FilaDato("BER s/ decididos:" if r.hay_empates else "BER observada:",
                                formato_ber(r.ber_con_codigo)))
        col.addWidget(_FilaDato("Tasa del código (R):", f"{r.parametros['tasa']:.3f}"))
        if r.hay_empates:
            col.addWidget(_FilaDato("Empates:", str(r.empates), C.AMBAR))
        elif r.bits_erroneos:
            col.addWidget(_FilaDato("Bits erróneos:", str(r.bits_erroneos), C.ERROR))
        col.addStretch(1)
        cuerpo.addWidget(panel)
        caja.addLayout(cuerpo)

        # ---- Avisos (errores residuales, texto corrupto o empates) ---------
        if r.hay_empates:
            caja.addWidget(_aviso(
                C.AMBAR, "⚠ Decodificación ambigua: algunos bits no pudieron recuperarse",
                f"{r.empates} de {len(r.bits_originales)} bits quedaron empatados (?) "
                f"({r.tasa_empates:.1%}). Errores residuales entre los bits decididos: "
                f"{r.errores_residuales}. BER sobre bits decididos: {formato_ber(r.ber_con_codigo)}. "
                "El texto no se reconstruye; revisa los bits en «Detalles de la transmisión»."))
        elif not r.exito:
            texto_aviso = (f"La transmisión terminó con {r.bits_erroneos} bit(s) incorrecto(s) "
                           f"(BER final = {formato_ber(r.ber_con_codigo)}). "
                           "La información recuperada puede estar corrupta.")
            if not r.utf8_valido:
                texto_aviso += " Los bytes recibidos no forman UTF‑8 válido (se muestran como «�»)."
            elif hay_diferencias:
                texto_aviso += " Los fragmentos resaltados difieren del mensaje enviado."
            caja.addWidget(_aviso(C.ERROR, "⚠ Mensaje corrupto" if not r.utf8_valido else None,
                                  texto_aviso))

        # ---- Pie ---------------------------------------------------------
        pie = QHBoxLayout()
        pie.setSpacing(8)
        self.boton_detalles = QPushButton("  Detalles de la transmisión")
        self.boton_detalles.setObjectName("BotonFantasma")
        self.boton_detalles.setCheckable(True)
        self.boton_detalles.setIcon(icono("flecha_derecha", C.TEXTO_SECUNDARIO, 14))
        self.boton_detalles.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_detalles.setToolTip("Mostrar u ocultar todas las etapas de la transmisión")
        self.boton_detalles.toggled.connect(self._alternar)
        pie.addWidget(self.boton_detalles)
        pie.addStretch(1)
        exportar = QPushButton("  Exportar JSON")
        exportar.setIcon(icono("descargar", C.TEXTO, 15))
        exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        exportar.setToolTip("Guardar esta transmisión en un archivo JSON")
        exportar.clicked.connect(self._exportar)
        pie.addWidget(exportar)
        caja.addLayout(pie)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Con poco ancho, el panel de estado pasa debajo de las etapas.
        estrecha = self.width() < 700
        direccion = (QHBoxLayout.Direction.TopToBottom if estrecha
                     else QHBoxLayout.Direction.LeftToRight)
        if self._cuerpo.direction() != direccion:
            self._cuerpo.setDirection(direccion)
            if estrecha:
                self._panel_estado.setMinimumWidth(0)
                self._panel_estado.setMaximumWidth(16777215)
            else:
                self._panel_estado.setFixedWidth(206)

    def _alternar(self, activo: bool) -> None:
        self.boton_detalles.setIcon(icono("flecha_abajo" if activo else "flecha_derecha",
                                          C.TEXTO_SECUNDARIO, 14))
        self.boton_detalles.setText("  Ocultar detalles" if activo else "  Detalles de la transmisión")
        self.detalles_alternados.emit(activo)

    def _exportar(self) -> None:
        """Reutiliza la exportación JSON existente con esta única transmisión."""
        r = self.resultado
        sugerido = Path.home() / f"codechat-transmision-{r.id}.json"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar transmisión", str(sugerido),
                                              "Archivos JSON (*.json)")
        if not ruta:
            return
        if not ruta.lower().endswith(".json"):
            ruta += ".json"
        try:
            persistencia.exportar(Path(ruta), [r], incluir_contenido=True)
        except OSError as e:
            QMessageBox.critical(self, "Exportar JSON", f"No se pudo guardar el archivo:\n{e}")
            return
        QMessageBox.information(self, "Exportar JSON", f"Transmisión exportada a:\n{ruta}")


def _aviso(color: str, titulo: str | None, texto: str) -> QFrame:
    aviso = QFrame()
    aviso.setObjectName("AvisoTransmision")
    aviso.setStyleSheet(f"QFrame#AvisoTransmision {{ background: {rgba(color, 0.10)};"
                        f" border: 1px solid {rgba(color, 0.38)}; border-radius: 9px; }}")
    col = QVBoxLayout(aviso)
    col.setContentsMargins(12, 9, 12, 9)
    col.setSpacing(3)
    if titulo:
        t = etiqueta(titulo, "Etiqueta", ajustar=True)
        t.setStyleSheet(f"color: {color}; font-weight: 700;")
        col.addWidget(t)
    d = etiqueta(texto, "EtiquetaSecundaria", ajustar=True)
    d.setStyleSheet(f"color: {C.TEXTO};")
    col.addWidget(d)
    return aviso


class BurbujaBienvenida(_ConTextoAjustable, QFrame):
    """Mensaje de bienvenida (no es una transmisión ni se guarda en el historial)."""

    sugerencia_elegida = Signal(str)

    def __init__(self, sugerencias: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaRecibida")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 14, 18, 10)
        caja.setSpacing(6)
        caja.addWidget(etiqueta("¡Bienvenido a CodeChat Pro!", "AutorBurbuja"))
        texto = ("Envía un mensaje y lo transmitiré usando un código de repetición a través de un "
                 "Canal Binario Simétrico (BSC), mostrando todo el proceso de codificación, "
                 "transmisión y recuperación.")
        self._texto_plano = texto
        self._lbl = etiqueta(texto, "TextoBurbuja", ajustar=True)
        self._lbl.setStyleSheet(f"color: {C.TEXTO_SECUNDARIO}; font-size: 14px;")
        caja.addWidget(self._lbl)
        pasos = QLabel(f"<span style='color:{C.AZUL};'>①</span> Escribe &nbsp;→&nbsp; "
                       f"<span style='color:{C.ROJO};'>②</span> Transmite &nbsp;→&nbsp; "
                       f"<span style='color:{C.VERDE};'>③</span> Recupera")
        pasos.setTextFormat(Qt.TextFormat.RichText)
        pasos.setStyleSheet(f"color: {C.TEXTO}; font-size: 13px; font-weight: 600;")
        caja.addWidget(pasos)
        chips = FlujoLayout(espaciado=8)
        for s in sugerencias:
            b = QPushButton(s)
            b.setObjectName("Sugerencia")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, t=s: self.sugerencia_elegida.emit(t))
            chips.addWidget(b)
        caja.addLayout(chips)
        hora = etiqueta(_hora(), "HoraBurbuja")
        hora.setAlignment(Qt.AlignmentFlag.AlignRight)
        caja.addWidget(hora)


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
        self.setFixedSize(44, 44)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPixmap(pixmap_logo(26))
        self.setToolTip("Receptor CodeChat Pro")
        self.setStyleSheet(
            f"background: {rgba(C.ROJO, 0.10)}; border: 1px solid {rgba(C.ROJO, 0.40)}; border-radius: 22px;")


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

    def agregar_bloque(self, widget: QWidget) -> None:
        """Inserta un elemento decorativo a todo el ancho, sin desplazar la vista al final."""
        self._lista.insertWidget(self._lista.count() - 1, widget)
        self._aparecer(widget)
        self._seguir_final = False
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(0))

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
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(12)
        fila.addWidget(Avatar(), 0, Qt.AlignmentFlag.AlignTop)
        columna = QVBoxLayout()
        columna.setSpacing(10)
        columna.addWidget(burbuja)
        fila.addLayout(columna, 1)
        self._limitar(burbuja, 0.92)
        self._insertar(envoltura)
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
                self._limitar(tarjeta, 0.92)
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
# Panel derecho «Análisis y Experimento»
# ===========================================================================
class TarjetaMetricaIcono(QFrame):
    """Métrica con icono tintado, etiqueta y valor (estilo de la referencia)."""

    def __init__(self, nombre_icono: str, titulo: str, color: str, ayuda: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("SubTarjeta")
        if ayuda:
            self.setToolTip(ayuda)
        self.setMinimumHeight(74)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(12, 10, 12, 10)
        fila.setSpacing(12)
        ic = QLabel()
        ic.setFixedSize(40, 40)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setPixmap(pixmap(nombre_icono, color, 22))
        ic.setStyleSheet(f"background: {rgba(color, 0.14)}; border: 1px solid {rgba(color, 0.35)};"
                         " border-radius: 10px;")
        fila.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = etiqueta(titulo, "EtiquetaSecundaria")
        t.setStyleSheet(f"color: {C.TEXTO}; font-size: 13px;")
        col.addWidget(t)
        self._valor = etiqueta("—", "ValorMetrica")
        self._valor.setStyleSheet("font-size: 21px;")
        col.addWidget(self._valor)
        self._detalle = etiqueta("", "Ayuda", ajustar=True)
        self._detalle.setStyleSheet("font-size: 11px;")
        col.addWidget(self._detalle)
        fila.addLayout(col, 1)

    def set_valor(self, valor: str | None, detalle: str = "") -> None:
        self._valor.setText("—" if valor is None else valor)
        self._valor.setStyleSheet("font-size: 21px;" + (f" color: {C.TEXTO_TENUE};" if valor is None else ""))
        self._detalle.setText(detalle)
        self._detalle.setVisible(bool(detalle))


def _info(texto: str) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(pixmap("info", C.TEXTO_TENUE, 14))
    lbl.setToolTip(texto)
    return lbl


def _campo_lectura(ayuda: str) -> QLabel:
    lbl = etiqueta("—", "CampoLectura")
    lbl.setToolTip(ayuda + " (calculado por el núcleo; solo lectura)")
    lbl.setMinimumWidth(70)
    return lbl


class DialogoGrafica(QDialog):
    """Muestra ampliada una gráfica del panel con exactamente los mismos datos."""

    def __init__(self, titulo: str, origen, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(980, 660)
        self.setMinimumSize(620, 440)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 18, 18, 18)
        marco = QFrame()
        marco.setObjectName("PanelPrincipal")
        col = QVBoxLayout(marco)
        col.setContentsMargins(20, 16, 20, 16)
        col.setSpacing(10)
        cab = QHBoxLayout()
        cab.addWidget(icono_label("grafica", C.ROJO, 26))
        t = etiqueta(titulo, "TituloTarjeta")
        t.setStyleSheet("font-size: 20px; font-weight: 700;")
        cab.addWidget(t, 1)
        cerrar = QPushButton("Cerrar")
        cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        cerrar.clicked.connect(self.accept)
        cab.addWidget(cerrar)
        col.addLayout(cab)
        if isinstance(origen, GraficaBER):
            series, vertical, vacio = origen.datos()
            grafica = GraficaBER()               # versión grande, con leyenda dentro
            grafica.set_datos(series, vertical, vacio)
            nota = ("Eje vertical en escala logarítmica. Curva teórica del núcleo para el p actual y "
                    "BER medidas en el chat con el mismo p (solo n impar). La línea verde marca la "
                    "capacidad de Shannon C = 1 − H₂(p). Pasa el ratón por los puntos para ver sus valores.")
        else:
            grafica = GraficaTasas()
            grafica.set_datos(origen.datos())
            nota = ("Tasa del código R = k/n frente a la capacidad del canal C = 1 − H₂(p), "
                    "ambas calculadas por el núcleo matemático.")
        col.addWidget(grafica, 1)
        n = etiqueta(nota, "Ayuda", ajustar=True)
        n.setStyleSheet("font-size: 12px;")
        col.addWidget(n)
        caja.addWidget(marco)


class PanelCanal(AreaDesplazable):
    """Configuración del canal, métricas y gráficas del último resultado."""

    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(margenes=(0, 0, 0, 0), espaciado=0, parent=parent)
        self.estado = estado
        self.setMinimumWidth(ANCHO_PANEL_DERECHO - 70)
        self.setMaximumWidth(ANCHO_PANEL_DERECHO + 40)

        marco = QFrame()
        marco.setObjectName("PanelPrincipal")
        caja = QVBoxLayout(marco)
        caja.setContentsMargins(16, 16, 16, 16)
        caja.setSpacing(14)
        self.layout_interno.addWidget(marco)

        cab = QHBoxLayout()
        cab.setSpacing(12)
        cab.addWidget(icono_label("analisis", C.ROJO, 28))
        titulo = etiqueta("Análisis y Experimento", "TituloTarjeta")
        titulo.setStyleSheet("font-size: 20px; font-weight: 700;")
        cab.addWidget(titulo, 1)
        caja.addLayout(cab)

        # ---- Parámetros ---------------------------------------------------
        param = QFrame()
        param.setObjectName("SubTarjeta")
        cp = QVBoxLayout(param)
        cp.setContentsMargins(14, 12, 14, 14)
        cp.setSpacing(10)
        t = etiqueta("Parámetros del experimento", "Etiqueta")
        t.setStyleSheet("font-size: 15px; font-weight: 650;")
        cp.addWidget(t)
        rej = QGridLayout()
        rej.setHorizontalSpacing(8)
        rej.setVerticalSpacing(8)
        self.selector_n = SelectorN(estado.n)
        self.selector_n.setMinimumWidth(80)
        self.campo_t = _campo_lectura("Errores corregibles t = ⌊(n − 1)/2⌋")
        self.campo_dmin = _campo_lectura("Distancia mínima d_min = n")
        self.campo_k = _campo_lectura("Dimensión k")
        celdas = [
            (0, 0, "n:", "Longitud del código de repetición (1–21). Con n par puede haber empates (?).",
             self.selector_n),
            (0, 1, "t:", "Errores corregibles por bloque", self.campo_t),
            (1, 0, "d<sub>min</sub>:", "Distancia mínima del código", self.campo_dmin),
            (1, 1, "k:", "Bits de información por palabra código", self.campo_k),
        ]
        for fila, col, nombre, ayuda, widget in celdas:
            lbl = QLabel(nombre)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setStyleSheet("font-size: 14px;")
            rej.addWidget(lbl, fila, col * 4)
            rej.addWidget(_info(ayuda), fila, col * 4 + 1)
            rej.addWidget(widget, fila, col * 4 + 2)
            if col == 0:
                rej.setColumnMinimumWidth(3, 14)
        rej.setColumnStretch(2, 1)
        rej.setColumnStretch(6, 1)
        cp.addLayout(rej)
        fila_p = QHBoxLayout()
        fila_p.setSpacing(8)
        lbl_p = QLabel("p:")
        lbl_p.setStyleSheet("font-size: 14px;")
        fila_p.addWidget(lbl_p)
        fila_p.addWidget(_info("Probabilidad de que el canal BSC invierta cada bit (0 – 0.5)"))
        self.control_p = ControlProbabilidad(estado.p)
        fila_p.addWidget(self.control_p, 1)
        cp.addLayout(fila_p)
        self.boton_transmitir = QPushButton("  Ejecutar transmisión")
        self.boton_transmitir.setObjectName("BotonPrimario")
        self.boton_transmitir.setIcon(icono("play", C.TEXTO, 18))
        self.boton_transmitir.setIconSize(QSize(18, 18))
        self.boton_transmitir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_transmitir.setToolTip("Transmite el texto escrito en el campo de mensaje")
        cp.addWidget(self.boton_transmitir)
        caja.addWidget(param)

        # ---- Métricas -----------------------------------------------------
        t = etiqueta("Métricas del resultado", "Etiqueta")
        t.setStyleSheet("font-size: 15px; font-weight: 650;")
        caja.addWidget(t)
        metricas = QGridLayout()
        metricas.setSpacing(10)
        self.m_r = TarjetaMetricaIcono("capas", "Tasa R", C.AZUL, "R = k / n")
        self.m_ber = TarjetaMetricaIcono("actividad", "BER", C.AMBAR,
                                         "Tasa de error de bits medida en la última transmisión del chat.")
        self.m_cap = TarjetaMetricaIcono("escudo", "Capacidad de Shannon", C.VERDE, "C = 1 − H₂(p)")
        self.m_pe = TarjetaMetricaIcono("grafica", "Pₑ teórico", C.MORADO,
                                        "Probabilidad residual teórica del núcleo (solo n impar)")
        for i, m in enumerate((self.m_r, self.m_ber, self.m_cap, self.m_pe)):
            metricas.addWidget(m, i // 2, i % 2)
        metricas.setColumnStretch(0, 1)
        metricas.setColumnStretch(1, 1)
        caja.addLayout(metricas)

        # ---- Gráficas -----------------------------------------------------
        graficas = QHBoxLayout()
        graficas.setSpacing(10)
        g1 = QFrame()
        g1.setObjectName("SubTarjeta")
        c1 = QVBoxLayout(g1)
        c1.setContentsMargins(10, 10, 10, 8)
        c1.setSpacing(4)
        t1 = etiqueta("BER vs. Tasa (R)  ⤢", "Etiqueta")
        t1.setToolTip("Haz clic en la gráfica para ampliarla")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.setStyleSheet("font-size: 14px; font-weight: 650;")
        c1.addWidget(t1)
        self.grafica = GraficaBER(leyenda=False, compacta=True)
        self.grafica.set_ampliable()
        self.grafica.clic.connect(lambda: DialogoGrafica("BER vs. Tasa (R)", self.grafica, self.window()).exec())
        c1.addWidget(self.grafica, 1)
        self.leyenda = QLabel()
        self.leyenda.setTextFormat(Qt.TextFormat.RichText)
        self.leyenda.setWordWrap(True)
        self.leyenda.setStyleSheet(f"color: {C.TEXTO_SECUNDARIO}; font-size: 10px;")
        c1.addWidget(self.leyenda)
        g2 = QFrame()
        g2.setObjectName("SubTarjeta")
        c2 = QVBoxLayout(g2)
        c2.setContentsMargins(10, 10, 10, 8)
        c2.setSpacing(4)
        t2 = etiqueta("Comparativa de Tasas  ⤢", "Etiqueta")
        t2.setToolTip("Haz clic en la gráfica para ampliarla")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t2.setStyleSheet("font-size: 14px; font-weight: 650;")
        c2.addWidget(t2)
        self.grafica_tasas = GraficaTasas()
        self.grafica_tasas.set_ampliable()
        self.grafica_tasas.clic.connect(
            lambda: DialogoGrafica("Comparativa de Tasas", self.grafica_tasas, self.window()).exec())
        c2.addWidget(self.grafica_tasas, 1)
        nota = etiqueta("Tasa del código R frente a la capacidad C del canal", "Ayuda", ajustar=True)
        nota.setStyleSheet("font-size: 10px;")
        c2.addWidget(nota)
        graficas.addWidget(g1, 1)
        graficas.addWidget(g2, 1)
        caja.addLayout(graficas)
        caja.addStretch(1)

        # ---- Señales ------------------------------------------------------
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
        self.campo_t.setText(str(par["errores_corregibles"]))
        self.campo_dmin.setText(str(par["distancia_minima"]))
        self.campo_k.setText(str(par["k"]))
        cap = servicio.capacidad(p)
        self.m_r.set_valor(f"{par['tasa']:.4f}", f"k = {par['k']}, n = {par['n']}")
        self.m_cap.set_valor(f"C = {cap:.4f}", f"p = {formato_p(p)}")
        try:
            self.m_pe.set_valor(formato_ber(servicio.error_residual(n, p)), f"n = {n}, p = {formato_p(p)}")
        except ValueError:
            self.m_pe.set_valor("N/D", "la fórmula del núcleo requiere n impar")

        chat = [r for r in self.estado.historial if r.origen == "chat"]
        if chat:
            u = chat[-1]
            detalle = (f"s/ bits decididos · {u.empates} empate(s)" if u.hay_empates
                       else f"sin código: {formato_ber(u.ber_sin_codigo)}")
            self.m_ber.set_valor(formato_ber(u.ber_con_codigo), detalle)
            self.m_ber.setToolTip(f"Última transmisión del chat (n = {u.n}, p = {formato_p(u.p)}).")
        else:
            self.m_ber.set_valor(None, "Envía un mensaje para medirla")

        # Solo n impar: la curva teórica es para n impar y, con empates, la BER no es total.
        medidos = [r for r in chat if abs(r.p - p) < 1e-9 and r.n % 2 == 1
                   and r.ber_con_codigo is not None]
        por_n: dict[int, list[float]] = {}
        for r in medidos:
            por_n.setdefault(r.n, []).append(r.ber_con_codigo)
        exp_con = sorted((1 / k, sum(v) / len(v)) for k, v in por_n.items())
        etiquetas = [f"n={round(1 / x)}" for x, _ in exp_con]
        series = [Serie("Teórico con código", C.ROJO, servicio.curva_teorica(p))]
        if exp_con:
            series.append(Serie("Medido con código", C.AMBAR, exp_con, tipo="puntos", etiquetas=etiquetas))
            sin = [r.ber_sin_codigo for r in medidos]
            series.append(Serie("Medido sin código", C.AZUL, [(1.0, sum(sin) / len(sin))], tipo="puntos"))
        self.grafica.set_datos(series, vertical=(cap, "C"))
        self.leyenda.setText(self.grafica.leyenda_html())
        self.grafica_tasas.set_datos([(f"R", par["tasa"], C.ROJO), ("C", cap, C.VERDE)])


# ===========================================================================
# Vista completa
# ===========================================================================
SUGERENCIAS = ["Hola, CodeChat Pro 👋", "Teoría de códigos", "¡Perfecto! 🚀"]


class VistaChat(QWidget):
    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        self._ocupado = False
        self._hay_mensajes = False

        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 14, 16, 16)
        fila.setSpacing(16)

        # ---- Panel central del chat ---------------------------------------
        centro = QFrame()
        centro.setObjectName("PanelPrincipal")
        col = QVBoxLayout(centro)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        cab = QHBoxLayout()
        cab.setContentsMargins(22, 16, 18, 14)
        cab.setSpacing(16)
        cab.addWidget(icono_label("chat", C.ROJO, 40), 0, Qt.AlignmentFlag.AlignVCenter)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(etiqueta("Chat", "TituloPagina"))
        sub = EtiquetaRecortada("Transmisión de mensajes con codificación y corrección de errores",
                                "SubtituloPagina")
        textos.addWidget(sub)
        cab.addLayout(textos, 1)
        self.boton_limpiar = QPushButton("  Nueva transmisión")
        self.boton_limpiar.setObjectName("BotonPrimario")
        self.boton_limpiar.setIcon(icono("mas", C.TEXTO, 18))
        self.boton_limpiar.setIconSize(QSize(18, 18))
        self.boton_limpiar.setToolTip("Empieza una conversación nueva (el historial se conserva)")
        self.boton_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        cab.addWidget(self.boton_limpiar, 0, Qt.AlignmentFlag.AlignVCenter)
        col.addLayout(cab)
        col.addWidget(separador())

        self.conversacion = Conversacion()
        col.addWidget(self.conversacion, 1)

        self.barra = QFrame()
        self.barra.setObjectName("BarraEntrada")
        fila_barra = QHBoxLayout(self.barra)
        fila_barra.setContentsMargins(12, 10, 10, 10)
        fila_barra.setSpacing(10)
        self.entrada = EntradaMensaje()
        self.entrada.setToolTip("Enter para enviar · Shift + Enter para nueva línea")
        fila_barra.addWidget(self.entrada, 1, Qt.AlignmentFlag.AlignVCenter)
        self.contador = etiqueta(f"0/{LONGITUD_MAXIMA}", "EtiquetaTenue")
        self.contador.setMinimumWidth(52)
        self.contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fila_barra.addWidget(self.contador, 0, Qt.AlignmentFlag.AlignVCenter)
        self.boton_enviar = QPushButton("  Enviar")
        self.boton_enviar.setObjectName("BotonEnviar")
        self.boton_enviar.setIcon(icono("enviar", C.TEXTO, 20))
        self.boton_enviar.setIconSize(QSize(20, 20))
        self.boton_enviar.setFixedHeight(44)
        self.boton_enviar.setMinimumWidth(116)
        self.boton_enviar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_enviar.setToolTip("Transmitir (Enter)")
        fila_barra.addWidget(self.boton_enviar, 0, Qt.AlignmentFlag.AlignBottom)
        envoltura_barra = QWidget()
        eb = QVBoxLayout(envoltura_barra)
        eb.setContentsMargins(14, 8, 14, 14)
        eb.addWidget(self.barra)
        col.addWidget(envoltura_barra)
        fila.addWidget(centro, 1)

        # ---- Panel derecho -------------------------------------------------
        self.panel = PanelCanal(estado)
        fila.addWidget(self.panel)

        # ---- Señales -------------------------------------------------------
        self.entrada.enviar_pedido.connect(self.enviar)
        self.entrada.textChanged.connect(self._al_escribir)
        self.entrada.foco_cambiado.connect(self._al_cambiar_foco)
        self.boton_enviar.clicked.connect(self.enviar)
        self.panel.boton_transmitir.clicked.connect(self.enviar)
        self.boton_limpiar.clicked.connect(self.limpiar)
        self._agregar_bienvenida()

    # ---- bienvenida ---------------------------------------------------------
    def _agregar_bienvenida(self) -> None:
        self.vacio = BurbujaBienvenida(SUGERENCIAS)
        self.vacio.sugerencia_elegida.connect(self._usar_sugerencia)
        self.conversacion.agregar_izquierda(self.vacio)
        # Ilustración central mientras la conversación está vacía.
        self._ilustracion = EstadoVacio(
            "chat", "Sin mensajes todavía",
            "Escribe un mensaje abajo o elige una sugerencia para ver cada etapa: "
            "codificación, ruido del canal y decodificación por mayoría.")
        self._ilustracion.setMinimumHeight(320)
        self.conversacion.agregar_bloque(self._ilustracion)

    # ---- interacción --------------------------------------------------------
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
            if self._ilustracion is not None:
                self.conversacion.quitar(self._ilustracion)
                self._ilustracion = None
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
        self._ilustracion = None
        self._hay_mensajes = False
        self._agregar_bienvenida()
