"""Componentes visuales reutilizables de CodeChat Pro."""

from __future__ import annotations

import html

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen,
    QPixmap, QTextOption,
)
from PySide6.QtWidgets import (
    QAbstractButton, QButtonGroup, QComboBox, QDialog, QDoubleSpinBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLayout, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QTextBrowser, QToolTip, QVBoxLayout, QWidget,
)

from interfaz import servicio
from interfaz.estilos import (
    C, FUENTE_MONO, FUENTE_MONO_RESPALDO, fuente, fuente_mono, qcolor, rgba,
)
from interfaz.iconos import icono, pixmap


# ===========================================================================
# Utilidades
# ===========================================================================
def etiqueta(texto: str = "", nombre: str = "Etiqueta", ajustar: bool = False,
             plano: bool = True) -> QLabel:
    lbl = QLabel(texto)
    lbl.setObjectName(nombre)
    lbl.setWordWrap(ajustar)
    if plano:
        lbl.setTextFormat(Qt.TextFormat.PlainText)
    return lbl


def icono_label(nombre: str, color: str = C.ROJO, tamano: int = 22) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(pixmap(nombre, color, tamano))
    lbl.setFixedSize(tamano + 2, tamano + 2)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class EtiquetaRecortada(QLabel):
    """QLabel de una línea que recorta con «…» y muestra el texto completo como tooltip."""

    def __init__(self, texto: str = "", nombre: str = "Etiqueta", parent=None):
        super().__init__(parent)
        self.setObjectName(nombre)
        self._completo = texto
        self.setToolTip(texto)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(40)
        super().setText(texto)

    def setText(self, texto: str) -> None:
        self._completo = texto
        self.setToolTip(texto)
        self._recortar()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recortar()

    def _recortar(self) -> None:
        super().setText(self.fontMetrics().elidedText(
            self._completo, Qt.TextElideMode.ElideRight, max(10, self.width())))


class FlujoLayout(QLayout):
    """Layout que coloca los elementos en fila y salta de línea cuando no caben."""

    def __init__(self, parent=None, espaciado: int = 8):
        super().__init__(parent)
        self._items = []
        self._esp = espaciado
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, ancho):
        return self._colocar(QRect(0, 0, ancho, 0), probar=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._colocar(rect, probar=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        tam = QSize()
        for item in self._items:
            tam = tam.expandedTo(item.minimumSize())
        return tam

    def _colocar(self, rect: QRect, probar: bool) -> int:
        x, y, alto_fila = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and alto_fila > 0:
                x = rect.x()
                y += alto_fila + self._esp
                alto_fila = 0
            if not probar:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._esp
            alto_fila = max(alto_fila, hint.height())
        return y + alto_fila - rect.y()


def separador() -> QFrame:
    linea = QFrame()
    linea.setObjectName("Separador")
    return linea


def repulir(widget: QWidget) -> None:
    """Vuelve a aplicar el QSS tras cambiar objectName o una propiedad dinámica."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def texto_ajustable(texto: str, cada: int = 26) -> str:
    """Inserta cortes invisibles en palabras muy largas para que QLabel pueda ajustarlas."""
    partes = []
    for palabra in texto.split(" "):
        if len(palabra) > cada:
            palabra = "​".join(palabra[i:i + cada] for i in range(0, len(palabra), cada))
        partes.append(palabra)
    return " ".join(partes)


def formato_p(p: float) -> str:
    return f"{p:.2f}" if round(p, 2) == round(p, 4) else f"{p:.3f}"


def formato_ber(valor: float) -> str:
    if valor == 0:
        return "0"
    if valor < 0.001:
        return f"{valor:.2e}"
    return f"{valor:.4f}"


# ===========================================================================
# Contenedores
# ===========================================================================
class Tarjeta(QFrame):
    """Panel redondeado con encabezado opcional (icono + título + extra)."""

    def __init__(self, titulo: str | None = None, nombre_icono: str | None = None,
                 subtitulo: str | None = None, extra: QWidget | None = None,
                 margen: int = 18, espaciado: int = 14, parent=None):
        super().__init__(parent)
        self.setObjectName("Tarjeta")
        self.cuerpo = QVBoxLayout(self)
        self.cuerpo.setContentsMargins(margen, margen, margen, margen)
        self.cuerpo.setSpacing(espaciado)

        if titulo:
            cabecera = QHBoxLayout()
            cabecera.setSpacing(12)
            if nombre_icono:
                cabecera.addWidget(icono_label(nombre_icono, C.ROJO, 24), 0, Qt.AlignmentFlag.AlignTop)
            textos = QVBoxLayout()
            textos.setSpacing(2)
            textos.addWidget(etiqueta(titulo, "TituloTarjeta"))
            if subtitulo:
                textos.addWidget(etiqueta(subtitulo, "SubtituloTarjeta", ajustar=True))
            cabecera.addLayout(textos, 1)
            if extra is not None:
                cabecera.addWidget(extra, 0, Qt.AlignmentFlag.AlignVCenter)
            self.cuerpo.addLayout(cabecera)


class EncabezadoPagina(QFrame):
    """Cabecera superior de cada vista."""

    def __init__(self, nombre_icono: str, titulo: str, subtitulo: str, parent=None):
        super().__init__(parent)
        self.setObjectName("EncabezadoPagina")
        self.fila = QHBoxLayout(self)
        self.fila.setContentsMargins(28, 20, 24, 20)
        self.fila.setSpacing(18)
        self.fila.addWidget(icono_label(nombre_icono, C.ROJO, 40), 0, Qt.AlignmentFlag.AlignVCenter)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(etiqueta(titulo, "TituloPagina"))
        textos.addWidget(EtiquetaRecortada(subtitulo, "SubtituloPagina"))
        self.fila.addLayout(textos, 1)

    def agregar(self, widget: QWidget) -> None:
        self.fila.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)


class AreaDesplazable(QScrollArea):
    """QScrollArea transparente con un layout vertical interno."""

    def __init__(self, margenes=(24, 24, 24, 24), espaciado: int = 18, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido = QWidget()
        contenido.setObjectName("Pagina")
        self.layout_interno = QVBoxLayout(contenido)
        self.layout_interno.setContentsMargins(*margenes)
        self.layout_interno.setSpacing(espaciado)
        self.setWidget(contenido)


# ===========================================================================
# Chips y métricas
# ===========================================================================
class Chip(QLabel):
    def __init__(self, texto: str = "", tipo: str = "neutro", parent=None):
        super().__init__(texto, parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.set_tipo(tipo)

    def set_tipo(self, tipo: str) -> None:
        self.setProperty("chip", tipo)
        repulir(self)


class TarjetaMetrica(QFrame):
    """Indicador numérico con acento de color y estado vacío."""

    def __init__(self, titulo: str, acento: str = C.ROJO, ayuda: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("TarjetaMetrica")
        self.setStyleSheet(f"""
            QFrame#TarjetaMetrica {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 {rgba(acento, 0.13)}, stop:0.55 {C.SUPERFICIE}, stop:1 {C.SUPERFICIE});
                border: 1px solid {C.BORDE_SUAVE};
                border-left: 3px solid {acento};
                border-radius: 12px;
            }}""")
        if ayuda:
            self.setToolTip(ayuda)
        self.setMinimumHeight(86)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 12, 14, 12)
        caja.setSpacing(2)
        self._titulo = etiqueta(titulo, "EtiquetaSecundaria")
        self._valor = etiqueta("—", "ValorMetricaVacio")
        self._detalle = etiqueta("Sin datos aún", "Ayuda")
        caja.addWidget(self._titulo)
        caja.addWidget(self._valor)
        caja.addWidget(self._detalle)
        caja.addStretch(1)

    def set_valor(self, valor: str | None, detalle: str = "") -> None:
        vacio = valor is None
        self._valor.setText("—" if vacio else valor)
        self._valor.setObjectName("ValorMetricaVacio" if vacio else "ValorMetrica")
        repulir(self._valor)
        self._detalle.setText(detalle if detalle else ("Sin datos aún" if vacio else ""))
        self._detalle.setVisible(bool(self._detalle.text()))


# ===========================================================================
# Navegación y marca
# ===========================================================================
class BotonNavegacion(QAbstractButton):
    """Elemento del menú lateral con estado activo degradado e indicador."""

    def __init__(self, texto: str, nombre_icono: str, parent=None):
        super().__init__(parent)
        self.setText(texto)
        self._icono = nombre_icono
        self._hover = False
        self._insignia = 0
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(220, 50)

    def set_insignia(self, valor: int) -> None:
        self._insignia = valor
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 3, -0.5, -3)
        activo = self.isChecked()

        if activo:
            grad = QLinearGradient(r.topLeft(), r.topRight())
            grad.setColorAt(0, qcolor(C.ROJO, 235))
            grad.setColorAt(1, qcolor(C.ROJO_OSCURO, 150))
            p.setPen(QPen(qcolor(C.ROJO_CLARO, 110), 1))
            p.setBrush(grad)
            p.drawRoundedRect(r, 12, 12)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor("#FFFFFF", 235))
            p.drawRoundedRect(QRectF(r.left() + 6, r.center().y() - 10, 4, 20), 2, 2)
        elif self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor(C.SUPERFICIE, 220))
            p.drawRoundedRect(r, 12, 12)

        color = C.TEXTO if (activo or self._hover) else C.TEXTO_SECUNDARIO
        p.drawPixmap(QPointF(r.left() + 22, r.center().y() - 11), pixmap(self._icono, color, 22))

        f = fuente(11.5, QFont.Weight.DemiBold if activo else QFont.Weight.Medium)
        p.setFont(f)
        p.setPen(QColor(C.TEXTO if activo else color))
        p.drawText(QRectF(r.left() + 60, r.top(), r.width() - 100, r.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

        if self._insignia:
            texto = str(self._insignia) if self._insignia < 100 else "99+"
            p.setFont(fuente(8.5, QFont.Weight.Bold))
            ancho = max(22, p.fontMetrics().horizontalAdvance(texto) + 12)
            caja = QRectF(r.right() - ancho - 12, r.center().y() - 10, ancho, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor("#FFFFFF", 50) if activo else qcolor(C.ROJO, 60))
            p.drawRoundedRect(caja, 10, 10)
            p.setPen(QColor(C.TEXTO if activo else C.ROJO_CLARO))
            p.drawText(caja, Qt.AlignmentFlag.AlignCenter, texto)
        p.end()


def _ruta_globo(r: QRectF) -> QPainterPath:
    """Silueta de globo de diálogo usada por el logotipo."""
    cuerpo = QRectF(r.left(), r.top(), r.width(), r.height() * 0.80)
    ruta = QPainterPath()
    ruta.addRoundedRect(cuerpo, r.height() * 0.22, r.height() * 0.22)
    cola = QPainterPath()
    cola.moveTo(r.left() + r.width() * 0.36, cuerpo.bottom() - 2)
    cola.lineTo(r.left() + r.width() * 0.40, r.bottom())
    cola.lineTo(r.left() + r.width() * 0.54, cuerpo.bottom() - 2)
    cola.closeSubpath()
    return ruta.united(cola)


def pintar_logo(p: QPainter, r: QRectF, con_texto: bool = True) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    trazo = max(2.0, r.height() * 0.05)
    interior = r.adjusted(trazo, trazo, -trazo, -trazo)
    ruta = _ruta_globo(interior)

    # Resplandor discreto
    for ancho, alfa in ((trazo * 5, 18), (trazo * 3, 35)):
        p.setPen(QPen(qcolor(C.ROJO, alfa), ancho, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(ruta)

    relleno = QLinearGradient(interior.topLeft(), interior.bottomRight())
    relleno.setColorAt(0, qcolor(C.ROJO, 60))
    relleno.setColorAt(1, qcolor(C.ROJO_OSCURO, 25))
    borde = QLinearGradient(interior.topLeft(), interior.bottomRight())
    borde.setColorAt(0, QColor(C.ROJO_CLARO))
    borde.setColorAt(1, QColor(C.ROJO))
    p.setPen(QPen(QBrush(borde), trazo, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(relleno)
    p.drawPath(ruta)

    if con_texto:
        f = fuente_mono(10)
        f.setBold(True)
        f.setPixelSize(max(8, int(interior.height() * 0.32)))
        p.setFont(f)
        p.setPen(QColor(C.TEXTO))
        p.drawText(QRectF(interior.left(), interior.top(), interior.width(), interior.height() * 0.80),
                   Qt.AlignmentFlag.AlignCenter, "0101")


def pixmap_logo(lado: int = 64) -> QPixmap:
    img = QPixmap(lado * 2, lado * 2)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    pintar_logo(p, QRectF(4, 10, lado * 2 - 8, lado * 2 - 20), con_texto=True)
    p.end()
    img.setDevicePixelRatio(2)
    return img


class Logo(QWidget):
    def __init__(self, ancho: int = 92, alto: int = 66, parent=None):
        super().__init__(parent)
        self.setFixedSize(ancho, alto)

    def paintEvent(self, _event):
        p = QPainter(self)
        pintar_logo(p, QRectF(self.rect()).adjusted(4, 4, -4, -2))
        p.end()


# ===========================================================================
# Controles de entrada
# ===========================================================================
class SelectorN(QComboBox):
    """Selector de longitud del código de repetición (solo n impar)."""

    n_cambiado = Signal(int)

    def __init__(self, n: int = servicio.N_POR_DEFECTO, parent=None):
        super().__init__(parent)
        for valor in servicio.VALORES_N:
            self.addItem(f"{valor}  (sin código)" if valor == 1 else str(valor), valor)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(120)
        self.setToolTip("Longitud del código de repetición. Solo valores impares:\n"
                        "la decodificación por mayoría no admite empates.")
        self.set_n(n)
        self.currentIndexChanged.connect(lambda _i: self.n_cambiado.emit(self.n()))

    def n(self) -> int:
        return int(self.currentData())

    def set_n(self, n: int) -> None:
        indice = self.findData(n)
        if indice >= 0 and indice != self.currentIndex():
            self.setCurrentIndex(indice)


class ControlProbabilidad(QWidget):
    """Slider + campo numérico sincronizados para la probabilidad p del BSC."""

    valor_cambiado = Signal(float)

    def __init__(self, p: float = servicio.P_POR_DEFECTO, parent=None):
        super().__init__(parent)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(12)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, int(servicio.P_MAXIMA * 1000))
        self._slider.setSingleStep(5)
        self._slider.setPageStep(50)
        self._slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._campo = QDoubleSpinBox()
        self._campo.setRange(0.0, servicio.P_MAXIMA)
        self._campo.setDecimals(3)
        self._campo.setSingleStep(0.01)
        self._campo.setFixedWidth(84)
        self._campo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._campo.setToolTip("Probabilidad de que el canal invierta cada bit (0 ≤ p ≤ 0.5).")
        fila.addWidget(self._slider, 1)
        fila.addWidget(self._campo)
        self.set_valor(p)
        self._slider.valueChanged.connect(self._desde_slider)
        self._campo.valueChanged.connect(self._desde_campo)

    def valor(self) -> float:
        return round(self._campo.value(), 3)

    def set_valor(self, p: float) -> None:
        for w in (self._slider, self._campo):
            w.blockSignals(True)
        self._slider.setValue(round(p * 1000))
        self._campo.setValue(p)
        for w in (self._slider, self._campo):
            w.blockSignals(False)

    def _desde_slider(self, v: int) -> None:
        self._campo.blockSignals(True)
        self._campo.setValue(v / 1000)
        self._campo.blockSignals(False)
        self.valor_cambiado.emit(self.valor())

    def _desde_campo(self, v: float) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(round(v * 1000))
        self._slider.blockSignals(False)
        self.valor_cambiado.emit(self.valor())


class ControlSegmentado(QFrame):
    """Grupo de botones exclusivos con aspecto de interruptor segmentado."""

    cambiado = Signal(int)

    def __init__(self, opciones: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("ContenedorSegmentos")
        fila = QHBoxLayout(self)
        fila.setContentsMargins(3, 3, 3, 3)
        fila.setSpacing(3)
        self._grupo = QButtonGroup(self)
        for i, texto in enumerate(opciones):
            b = QPushButton(texto)
            b.setObjectName("Segmento")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self._grupo.addButton(b, i)
            fila.addWidget(b)
        self._grupo.button(0).setChecked(True)
        self._grupo.idClicked.connect(self.cambiado.emit)

    def indice(self) -> int:
        return self._grupo.checkedId()


# ===========================================================================
# Visualización de bits
# ===========================================================================
class VisorBits(QTextBrowser):
    """Muestra secuencias binarias agrupadas, resaltando los bits que difieren."""

    def __init__(self, lineas_maximas: int = 4, parent=None):
        super().__init__(parent)
        self.setObjectName("VisorBits")
        self.setFont(fuente_mono(10.5))
        self._lineas_maximas = lineas_maximas
        self._extra = 2 * 4 + 2 * 1 + 2 * 4   # margen del documento + borde + padding QSS
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setOpenLinks(False)
        self.document().setDocumentMargin(4)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(self._ajustar_alto)
        self.setFixedHeight(40)

    def _ajustar_alto(self, tam) -> None:
        self.ensurePolished()
        linea = QFontMetrics(self.document().defaultFont()).lineSpacing()
        alto = int(tam.height()) + self._extra - 2 * 4
        maximo = self._lineas_maximas * linea + self._extra - 4
        self.setFixedHeight(max(linea + self._extra, min(alto, maximo)))

    def set_bits(self, bits: str, referencia: str | None = None, bloque: int | None = None,
                 max_bits: int = 4096) -> None:
        mostrados = bits[:max_bits]
        partes: list[str] = []
        tramo: list[str] = []
        estado_tramo = False

        def volcar():
            if not tramo:
                return
            texto = "".join(tramo)
            if estado_tramo:
                partes.append(
                    f'<span style="color:{C.ROJO_CLARO}; background-color:#4A1222; '
                    f'font-weight:700;">{texto}</span>')
            else:
                partes.append(texto)
            tramo.clear()

        for i, bit in enumerate(mostrados):
            if bloque and i and i % bloque == 0:
                volcar()
                partes.append(" ")
            distinto = referencia is not None and i < len(referencia) and referencia[i] != bit
            if distinto != estado_tramo:
                volcar()
                estado_tramo = distinto
            tramo.append(bit)
        volcar()

        if len(bits) > max_bits:
            partes.append(f' <span style="color:{C.TEXTO_TENUE};">… +{len(bits) - max_bits} bits</span>')
        self.setHtml(f'<div style="color:#D3DAEA;">{"".join(partes)}</div>')


class MapaBloques(QWidget):
    """Cuadrícula de bloques: neutro (sin errores), azul (corregido), rojo (fallido)."""

    MAX_BLOQUES = 2400

    def __init__(self, parent=None):
        super().__init__(parent)
        self._errores: list[int] = []
        self._correcto: list[bool] = []
        self._celda, self._hueco = 11, 3
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(30)

    def set_datos(self, errores: list[int], correcto: list[bool]) -> None:
        self._errores = errores[: self.MAX_BLOQUES]
        self._correcto = correcto[: self.MAX_BLOQUES]
        self._recalcular_alto()
        self.update()

    def _por_fila(self) -> int:
        return max(1, (self.width() + self._hueco) // (self._celda + self._hueco))

    def _recalcular_alto(self) -> None:
        filas = max(1, -(-len(self._errores) // self._por_fila()))
        self.setFixedHeight(filas * (self._celda + self._hueco) + 2)

    def resizeEvent(self, event):
        self._recalcular_alto()
        super().resizeEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        por_fila, paso = self._por_fila(), self._celda + self._hueco
        for i, (e, ok) in enumerate(zip(self._errores, self._correcto)):
            if not ok:
                color = qcolor(C.ROJO)
            elif e:
                color = qcolor(C.AZUL, 210)
            else:
                color = qcolor(C.SUPERFICIE_ALTA)
            p.setBrush(color)
            p.drawRoundedRect(QRectF((i % por_fila) * paso, (i // por_fila) * paso,
                                     self._celda, self._celda), 3, 3)
        p.end()

    def mouseMoveEvent(self, event):
        paso = self._celda + self._hueco
        col, fila = int(event.position().x() // paso), int(event.position().y() // paso)
        i = fila * self._por_fila() + col
        if 0 <= col < self._por_fila() and 0 <= i < len(self._errores):
            e, ok = self._errores[i], self._correcto[i]
            estado = "decodificación fallida" if not ok else ("corregido" if e else "sin errores")
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"Bloque {i + 1}: {e} bit(s) alterado(s) → {estado}", self)
        else:
            QToolTip.hideText()


def leyenda_mapa() -> QWidget:
    w = QWidget()
    fila = QHBoxLayout(w)
    fila.setContentsMargins(0, 0, 0, 0)
    fila.setSpacing(16)
    for color, texto in ((C.SUPERFICIE_ALTA, "Sin errores"), (C.AZUL, "Corregido"),
                         (C.ROJO, "Fallido")):
        cuadro = QLabel()
        cuadro.setFixedSize(11, 11)
        cuadro.setStyleSheet(f"background:{color}; border-radius:3px;")
        fila.addWidget(cuadro)
        fila.addWidget(etiqueta(texto, "EtiquetaTenue"))
    fila.addStretch(1)
    return w


# ===========================================================================
# Estados vacíos
# ===========================================================================
class EstadoVacio(QWidget):
    sugerencia_elegida = Signal(str)

    def __init__(self, nombre_icono: str, titulo: str, descripcion: str,
                 sugerencias: list[str] | None = None, parent=None):
        super().__init__(parent)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(24, 24, 24, 24)
        caja.setSpacing(10)
        caja.addStretch(1)

        circulo = QLabel()
        circulo.setFixedSize(76, 76)
        circulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circulo.setPixmap(pixmap(nombre_icono, C.ROJO, 34))
        circulo.setStyleSheet(
            f"background: qradialgradient(cx:0.5, cy:0.5, radius:0.6, fx:0.5, fy:0.4,"
            f" stop:0 {rgba(C.ROJO, 0.22)}, stop:1 {rgba(C.ROJO, 0.04)});"
            f" border: 1px solid {rgba(C.ROJO, 0.35)}; border-radius: 38px;")
        caja.addWidget(circulo, 0, Qt.AlignmentFlag.AlignHCenter)
        caja.addSpacing(6)

        t = etiqueta(titulo, "TituloTarjeta")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caja.addWidget(t)
        d = etiqueta(descripcion, "EtiquetaSecundaria", ajustar=True)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setFixedWidth(440)
        d.setMinimumHeight(d.heightForWidth(440))
        fila_d = QHBoxLayout()
        fila_d.addStretch(1)
        fila_d.addWidget(d)
        fila_d.addStretch(1)
        caja.addLayout(fila_d)

        if sugerencias:
            caja.addSpacing(8)
            fila = QHBoxLayout()
            fila.setSpacing(8)
            fila.addStretch(1)
            for s in sugerencias:
                b = QPushButton(s)
                b.setObjectName("Sugerencia")
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.clicked.connect(lambda _=False, texto=s: self.sugerencia_elegida.emit(texto))
                fila.addWidget(b)
            fila.addStretch(1)
            caja.addLayout(fila)
        caja.addStretch(2)


# ===========================================================================
# Detalle de una transmisión
# ===========================================================================
_TEXTO_ESTADO = {
    "sin_errores": ("exito", C.VERDE, "El canal no alteró ningún bit."),
    "corregido": ("exito", C.VERDE, "Errores corregidos correctamente (≤ t = {t} por bloque)"),
    "residual": ("fallo", C.ROJO_CLARO,
                 "{f} bloque(s) superaron t = {t} errores: {b} bit(s) erróneo(s) tras decodificar"),
}


class TarjetaDetalleTransmision(QFrame):
    """Tarjeta «Detalle de la transmisión» con todas las etapas del proceso."""

    def __init__(self, r: servicio.ResultadoTransmision, compacta: bool = True, parent=None):
        super().__init__(parent)
        self.resultado = r
        self.setObjectName("Tarjeta")
        self.setStyleSheet(f"QFrame#Tarjeta {{ background: {C.PANEL}; border: 1px solid {C.BORDE}; "
                           f"border-radius: 14px; }}")
        max_bits = 384 if compacta else 20000
        alto_visor = 3 if compacta else 8   # líneas visibles antes de desplazar

        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 16, 18, 16)
        caja.setSpacing(12)

        # Cabecera
        cab = QHBoxLayout()
        cab.setSpacing(10)
        cab.addWidget(icono_label("antena", C.ROJO, 22))
        cab.addWidget(etiqueta("Detalle de la transmisión", "TituloTarjeta"))
        cab.addStretch(1)
        cab.addWidget(Chip(f"n = {r.n} · p = {formato_p(r.p)}", "neutro"))
        if compacta:
            ver = QPushButton()
            ver.setObjectName("BotonFantasma")
            ver.setIcon(icono("expandir", C.TEXTO_SECUNDARIO, 16))
            ver.setToolTip("Ver detalle completo")
            ver.setCursor(Qt.CursorShape.PointingHandCursor)
            ver.clicked.connect(lambda: DialogoDetalle(r, self.window()).exec())
            cab.addWidget(ver)
        caja.addLayout(cab)

        # Filas
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(16)
        rejilla.setVerticalSpacing(8)
        rejilla.setColumnStretch(1, 1)
        fila = 0

        def agregar(nombre: str, widget: QWidget):
            nonlocal fila
            lbl = etiqueta(nombre, "EtiquetaSecundaria", ajustar=True)
            lbl.setMinimumWidth(150 if compacta else 190)
            rejilla.addWidget(lbl, fila, 0, Qt.AlignmentFlag.AlignTop)
            rejilla.addWidget(widget, fila, 1)
            fila += 1

        if r.texto is not None:
            original = etiqueta(texto_ajustable(r.texto), "Mono", ajustar=True)
            original.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            agregar("Mensaje original:", original)
            v = VisorBits(alto_visor)
            v.set_bits(r.bits_originales, bloque=8, max_bits=max_bits)
            agregar(f"Representación binaria ({len(r.bits_originales)} bits):", v)
        else:
            v = VisorBits(alto_visor)
            v.set_bits(r.bits_originales, bloque=8, max_bits=max_bits)
            agregar(f"Bits originales ({len(r.bits_originales)}):", v)

        v = VisorBits(alto_visor)
        v.set_bits(r.codificado, bloque=r.n, max_bits=max_bits)
        agregar(f"Bits codificados (n = {r.n}):", v)

        v = VisorBits(alto_visor)
        v.set_bits(r.recibido, referencia=r.codificado, bloque=r.n, max_bits=max_bits)
        agregar(f"Bits recibidos (canal BSC, p = {formato_p(r.p)}):", v)

        v = VisorBits(alto_visor)
        v.set_bits(r.recuperado, referencia=r.bits_originales, bloque=8, max_bits=max_bits)
        agregar("Bits decodificados (mayoría):", v)

        if r.texto is not None:
            rec = Chip(texto_ajustable(r.texto_recuperado or "∅"), "exito" if r.exito else "error")
            rec.setWordWrap(True)
            rec.setStyleSheet("font-size: 13px; font-weight: 600;"
                              f" font-family: '{FUENTE_MONO}', '{FUENTE_MONO_RESPALDO}';")
            rec.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            rec.ensurePolished()
            natural = rec.fontMetrics().horizontalAdvance(rec.text()) + 26
            rec.setMinimumWidth(min(natural, 380))
            contenedor = QWidget()
            fila_rec = QHBoxLayout(contenedor)
            fila_rec.setContentsMargins(0, 0, 0, 0)
            fila_rec.addWidget(rec, 0)
            fila_rec.addStretch(1)
            agregar("Mensaje recuperado:", contenedor)
        caja.addLayout(rejilla)

        if not compacta:
            caja.addWidget(separador())
            caja.addWidget(etiqueta("MAPA DE BLOQUES", "Seccion"))
            mapa = MapaBloques()
            mapa.set_datos(r.errores_por_bloque, r.bloque_correcto)
            caja.addWidget(mapa)
            caja.addWidget(leyenda_mapa())

        # Indicadores
        chips = FlujoLayout(espaciado=8)
        chips.addWidget(Chip(f"Bits alterados por el canal: {r.errores_canal}/{len(r.codificado)}",
                             "aviso" if r.errores_canal else "neutro"))
        chips.addWidget(Chip(f"Bloques corregidos: {r.bloques_corregidos}", "info"))
        chips.addWidget(Chip(f"Bloques fallidos: {r.bloques_fallidos}",
                             "error" if r.bloques_fallidos else "neutro"))
        chips.addWidget(Chip(f"BER: {formato_ber(r.ber_con_codigo)} "
                             f"(sin código: {formato_ber(r.ber_sin_codigo)})", "neutro"))
        caja.addLayout(chips)

        # Estado final
        nombre_ic, color, plantilla = _TEXTO_ESTADO[r.estado]
        est = QHBoxLayout()
        est.setSpacing(10)
        est.addWidget(icono_label(nombre_ic, color, 22))
        texto_estado = plantilla.format(t=r.t, f=r.bloques_fallidos, b=r.bits_erroneos)
        lbl = etiqueta(texto_estado, "Etiqueta", ajustar=True)
        lbl.setStyleSheet(f"color: {color}; font-size: 14px;")
        est.addWidget(lbl, 1)
        caja.addLayout(est)


class DialogoDetalle(QDialog):
    def __init__(self, r: servicio.ResultadoTransmision, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalle de la transmisión #{r.id}")
        self.resize(900, 720)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        area = AreaDesplazable()
        area.layout_interno.addWidget(TarjetaDetalleTransmision(r, compacta=False))
        area.layout_interno.addStretch(1)
        caja.addWidget(area)
