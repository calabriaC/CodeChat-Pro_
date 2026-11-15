"""Componentes visuales reutilizables de CodeChat Pro."""

from __future__ import annotations

import html
import math

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen,
    QPixmap, QRadialGradient, QTextOption,
)
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QButtonGroup, QComboBox, QDialog, QDoubleSpinBox, QFrame,
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


def formato_ber(valor: float | None) -> str:
    if valor is None:
        return "N/D"
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
        self._detalle = etiqueta("Sin datos aún", "Ayuda", ajustar=True)
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
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(220, 56)

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
            # Resplandor discreto alrededor del elemento activo
            for extra, alfa in ((4, 14), (2, 26)):
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor(C.ROJO, alfa))
                p.drawRoundedRect(r.adjusted(-extra, -extra + 1, extra, extra - 1), 12 + extra, 12 + extra)
            grad = QLinearGradient(r.topLeft(), r.topRight())
            grad.setColorAt(0, qcolor(C.ROJO, 235))
            grad.setColorAt(0.6, qcolor(C.ROJO_SECUNDARIO, 200))
            grad.setColorAt(1, qcolor(C.ROJO_OSCURO, 140))
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
        p.drawPixmap(QPointF(r.left() + 22, r.center().y() - 12), pixmap(self._icono, color, 24))

        f = fuente(12, QFont.Weight.DemiBold if activo else QFont.Weight.Medium)
        p.setFont(f)
        p.setPen(QColor(C.TEXTO if activo else color))
        p.drawText(QRectF(r.left() + 64, r.top(), r.width() - 100, r.height()),
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


def _hexagono(c: QPointF, radio: float) -> list[QPointF]:
    """Vértices de un hexágono con un vértice arriba (vista isométrica de un cubo)."""
    return [QPointF(c.x() + radio * math.cos(math.radians(a)), c.y() + radio * math.sin(math.radians(a)))
            for a in (-90, -30, 30, 90, 150, 210)]


def _caras_cubo(c: QPointF, radio: float) -> tuple[QPainterPath, QPainterPath, QPainterPath]:
    v = _hexagono(c, radio)
    caras = []
    for puntos in ((v[0], v[1], c, v[5]), (v[5], c, v[3], v[4]), (c, v[1], v[2], v[3])):
        ruta = QPainterPath(puntos[0])
        for q in puntos[1:]:
            ruta.lineTo(q)
        ruta.closeSubpath()
        caras.append(ruta)
    return caras[0], caras[1], caras[2]   # superior, izquierda, derecha


def pintar_logo(p: QPainter, r: QRectF, con_texto: bool = False) -> None:
    """Logotipo geométrico: cubo isométrico rojo con un núcleo hueco."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    lado = min(r.width(), r.height())
    c = r.center()
    radio = lado * 0.46

    # Resplandor discreto
    halo = QRadialGradient(c, radio * 1.35)
    halo.setColorAt(0, qcolor(C.ROJO, 70))
    halo.setColorAt(1, qcolor(C.ROJO, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(halo)
    p.drawEllipse(c, radio * 1.35, radio * 1.35)

    superior, izquierda, derecha = _caras_cubo(c, radio)
    for ruta, claro, oscuro in ((superior, "#FF6B78", C.ROJO), (izquierda, C.ROJO, "#C3283A"),
                                (derecha, "#B32234", "#7E1424")):
        grad = QLinearGradient(ruta.boundingRect().topLeft(), ruta.boundingRect().bottomRight())
        grad.setColorAt(0, QColor(claro))
        grad.setColorAt(1, QColor(oscuro))
        p.setBrush(grad)
        p.setPen(QPen(qcolor("#2A0A10", 160), max(1.0, lado * 0.012)))
        p.drawPath(ruta)

    # Núcleo hueco: un cubo interior oscuro con aristas claras
    interior = radio * 0.42
    sup_i, izq_i, der_i = _caras_cubo(c, interior)
    for ruta, color in ((sup_i, "#3A0E16"), (izq_i, "#26080E"), (der_i, "#1A050A")):
        p.setBrush(QColor(color))
        p.setPen(QPen(qcolor("#FFB3BB", 150), max(1.0, lado * 0.018)))
        p.drawPath(ruta)


def pixmap_logo(lado: int = 64) -> QPixmap:
    img = QPixmap(lado * 2, lado * 2)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    pintar_logo(p, QRectF(0, 0, lado * 2, lado * 2))
    p.end()
    img.setDevicePixelRatio(2)
    return img


class Logo(QWidget):
    def __init__(self, ancho: int = 72, alto: int = 72, parent=None):
        super().__init__(parent)
        self.setFixedSize(ancho, alto)

    def paintEvent(self, _event):
        p = QPainter(self)
        pintar_logo(p, QRectF(self.rect()))
        p.end()


# ===========================================================================
# Controles de entrada
# ===========================================================================
class SelectorN(QComboBox):
    """Selector de longitud del código de repetición (n = 1 … 21)."""

    n_cambiado = Signal(int)

    def __init__(self, n: int = servicio.N_POR_DEFECTO, parent=None):
        super().__init__(parent)
        for valor in servicio.VALORES_N:
            self.addItem(str(valor), valor)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(120)
        self.setToolTip("Longitud del código de repetición (1 a 21).\n"
                        "Con n par puede haber empates: el bit queda como «?».")
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
                 max_bits: int = 4096, color_iguales: str | None = None) -> None:
        """Si se da `referencia`, los bits distintos se pintan en rojo y, si se indica
        `color_iguales`, los coincidentes en ese color (p. ej. verde)."""
        mostrados = bits[:max_bits]
        partes: list[str] = []
        tramo: list[str] = []
        estado_tramo = False
        grupo = [0]   # índice del bloque actual: alterna el tono para leer por grupos

        def volcar():
            if not tramo:
                return
            texto = "".join(tramo)
            atenuado = bloque and grupo[0] % 2 == 1
            if estado_tramo == "empate":
                partes.append(
                    f'<span style="color:{C.AMBAR}; background-color:#3D2E12; '
                    f'font-weight:700;">{texto}</span>')
            elif estado_tramo:
                partes.append(
                    f'<span style="color:{C.ERROR}; background-color:#4A1222; '
                    f'font-weight:700;">{texto}</span>')
            elif color_iguales and referencia is not None:
                tono = "#12A57A" if atenuado else color_iguales
                partes.append(f'<span style="color:{tono};">{texto}</span>')
            elif atenuado:
                partes.append(f'<span style="color:#8D98B3;">{texto}</span>')
            else:
                partes.append(texto)
            tramo.clear()

        for i, bit in enumerate(mostrados):
            if bloque and i and i % bloque == 0:
                volcar()
                grupo[0] += 1
                partes.append(" ")
            if bit == "?":
                distinto = "empate"
            else:
                distinto = referencia is not None and i < len(referencia) and referencia[i] != bit
            if distinto != estado_tramo:
                volcar()
                estado_tramo = distinto
            tramo.append(bit)
        volcar()

        if len(bits) > max_bits:
            partes.append(f' <span style="color:{C.TEXTO_TENUE};">… +{len(bits) - max_bits} bits</span>')
        self.setHtml(f'<div style="color:#E2E7F3;">{"".join(partes)}</div>')


class MapaBloques(QWidget):
    """Cuadrícula de bloques: neutro (sin errores), azul (corregido), rojo (fallido).

    Un clic sobre un bloque emite `bloque_elegido(indice)` para inspeccionarlo.
    """

    MAX_BLOQUES = 2400
    bloque_elegido = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._errores: list[int] = []
        self._correcto: list[bool] = []
        self._ambiguo: list[bool] = []
        self._seleccion = -1
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._celda, self._hueco = 11, 3
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(30)

    def set_datos(self, errores: list[int], correcto: list[bool],
                  ambiguo: list[bool] | None = None) -> None:
        self._errores = errores[: self.MAX_BLOQUES]
        self._correcto = correcto[: self.MAX_BLOQUES]
        self._ambiguo = (ambiguo or [False] * len(correcto))[: self.MAX_BLOQUES]
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
            if i < len(self._ambiguo) and self._ambiguo[i]:
                color = qcolor(C.AMBAR)
            elif not ok:
                color = qcolor(C.ROJO)
            elif e:
                color = qcolor(C.AZUL, 210)
            else:
                color = qcolor(C.SUPERFICIE_ALTA)
            p.setBrush(color)
            celda = QRectF((i % por_fila) * paso, (i // por_fila) * paso, self._celda, self._celda)
            p.drawRoundedRect(celda, 3, 3)
            if i == self._seleccion:
                p.setPen(QPen(QColor(C.TEXTO), 1.6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(celda.adjusted(-1.5, -1.5, 1.5, 1.5), 3, 3)
                p.setPen(Qt.PenStyle.NoPen)
        p.end()

    def _indice_en(self, pos) -> int:
        paso = self._celda + self._hueco
        col, fila = int(pos.x() // paso), int(pos.y() // paso)
        i = fila * self._por_fila() + col
        return i if 0 <= col < self._por_fila() and 0 <= i < len(self._errores) else -1

    def seleccionar(self, i: int) -> None:
        self._seleccion = i
        self.update()

    def mousePressEvent(self, event):
        i = self._indice_en(event.position())
        if i >= 0:
            self.seleccionar(i)
            self.bloque_elegido.emit(i)

    def mouseMoveEvent(self, event):
        i = self._indice_en(event.position())
        if i >= 0:
            e, ok = self._errores[i], self._correcto[i]
            if i < len(self._ambiguo) and self._ambiguo[i]:
                estado = "empate: decodificación ambigua (?)"
            else:
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
                         (C.ROJO, "Fallido"), (C.AMBAR, "Empate (ambiguo)")):
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
                 sugerencias: list[str] | None = None, extra: QWidget | None = None,
                 logo: bool = False, parent=None):
        super().__init__(parent)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(24, 24, 24, 24)
        caja.setSpacing(10)
        caja.addStretch(1)

        if logo:
            self._emblema = Logo(132, 96)
        else:
            self._emblema = QLabel()
            self._emblema.setFixedSize(80, 80)
            self._emblema.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._emblema.setPixmap(pixmap(nombre_icono, C.ROJO, 34))
            self._emblema.setStyleSheet(
                f"background: qradialgradient(cx:0.5, cy:0.5, radius:0.6, fx:0.5, fy:0.4,"
                f" stop:0 {rgba(C.ROJO, 0.24)}, stop:1 {rgba(C.ROJO, 0.04)});"
                f" border: 1px solid {rgba(C.ROJO, 0.40)}; border-radius: 40px;")
        caja.addWidget(self._emblema, 0, Qt.AlignmentFlag.AlignHCenter)
        caja.addSpacing(10)

        t = etiqueta(titulo, "TituloTarjeta")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"font-size: {26 if logo else 20}px; font-weight: 700; letter-spacing: -0.3px;")
        caja.addWidget(t)
        d = etiqueta(descripcion, "EtiquetaSecundaria", ajustar=True)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setStyleSheet("font-size: 14px;")
        d.setFixedWidth(480)
        d.ensurePolished()
        d.setMinimumHeight(d.heightForWidth(480))
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
        if extra is not None:
            caja.addSpacing(18)
            caja.addWidget(extra)
        caja.addStretch(2)

    def paintEvent(self, _event):
        """Ilustración discreta: anillos concéntricos con nodos, como una señal que se propaga."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        centro = QPointF(self._emblema.geometry().center())
        for i, radio in enumerate((70, 112, 160, 214, 274)):
            p.setPen(QPen(qcolor(C.ROJO if i < 2 else C.BORDE, 34 - i * 5), 1,
                          Qt.PenStyle.SolidLine if i % 2 == 0 else Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(centro, radio, radio)
        p.setPen(Qt.PenStyle.NoPen)
        for radio, angulo, color in ((112, -35, C.ROJO), (160, 205, C.AZUL), (214, -150, C.VERDE),
                                     (160, 20, C.TEXTO_TENUE), (274, -60, C.ROJO)):
            punto = QPointF(centro.x() + radio * math.cos(math.radians(angulo)),
                            centro.y() + radio * math.sin(math.radians(angulo)))
            p.setBrush(qcolor(color, 120))
            p.drawEllipse(punto, 3.2, 3.2)
            p.setBrush(qcolor(color, 30))
            p.drawEllipse(punto, 8, 8)
        p.end()


# ===========================================================================
# Detalles de una transmisión
# ===========================================================================
NO_DISPONIBLE = "No disponible"

# estado → (texto corto, tipo de chip, icono, color, descripción)
ESTADOS_TRANSMISION = {
    "sin_errores": ("Recibido sin errores", "exito", "exito", C.VERDE,
                    "El canal no alteró ningún bit: el mensaje llegó intacto."),
    "corregido": ("Errores corregidos", "info", "escudo", C.AZUL,
                  "El canal alteró {e} bit(s) y la decodificación por mayoría los corrigió "
                  "todos (como máximo t = {t} errores por bloque)."),
    "residual": ("Con errores residuales", "error", "fallo", C.ERROR,
                 "La transmisión terminó con {b} bit(s) incorrecto(s) (BER final = {ber}). "
                 "La información recuperada puede estar corrupta."),
    "ambiguo": ("Decodificación ambigua", "aviso", "alerta", C.AMBAR,
                "Decodificación ambigua: {emp} bit(s) no pudieron recuperarse por empate (?). "
                "Entre los {dec} bits decididos hubo {b} error(es) residual(es) "
                "(BER sobre bits decididos = {ber})."),
}


def descripcion_estado(r: servicio.ResultadoTransmision) -> str:
    return ESTADOS_TRANSMISION[r.estado][4].format(
        e=r.errores_canal, t=r.t, f=r.bloques_fallidos, b=r.bits_erroneos,
        ber=formato_ber(r.ber_con_codigo), emp=r.empates, dec=r.bits_decididos)


def resumen_transmision(r: servicio.ResultadoTransmision) -> str:
    """Resumen en lenguaje natural construido solo con los datos reales del resultado."""
    partes = [
        f"Se transmitieron {len(r.bits_originales)} bits de información repitiendo cada uno "
        f"{r.n} {'vez' if r.n == 1 else 'veces'} ({len(r.codificado)} bits por el canal, R = "
        f"{r.parametros['tasa']:.3f}).",
    ]
    if r.errores_canal == 0:
        partes.append("El canal BSC no invirtió ningún bit en esta ejecución.")
    else:
        partes.append(
            f"El canal BSC (p = {formato_p(r.p)}) invirtió {r.errores_canal} bit(s) "
            f"(BER del canal = {formato_ber(r.ber_canal)}), repartidos en {r.bloques_afectados} "
            f"de {r.total_bloques} bloques.")
        if r.hay_empates:
            partes.append(
                f"{r.empates} bloque(s) quedaron empatados ({r.tasa_empates:.1%} de los bits) y su "
                f"bit se marca como «?». Entre los {r.bits_decididos} bits decididos hubo "
                f"{r.errores_residuales} error(es) residual(es) (BER sobre bits decididos = "
                f"{formato_ber(r.ber_con_codigo)}).")
        elif r.bloques_fallidos == 0:
            partes.append(f"Todos los bloques afectados tenían como máximo t = {r.t} errores, "
                          "así que la mayoría recuperó cada bit.")
        else:
            partes.append(
                f"{r.bloques_corregidos} bloque(s) afectado(s) se corrigieron y {r.bloques_fallidos} "
                f"superaron t = {r.t}, dejando {r.bits_erroneos} bit(s) incorrecto(s) "
                f"(BER final = {formato_ber(r.ber_con_codigo)}).")
    teorico = r.error_residual_teorico
    if teorico is not None:
        partes.append(f"Como referencia, la probabilidad teórica de error por bit tras decodificar "
                      f"es Pₑ = {formato_ber(teorico)}; una ejecución concreta puede diferir de ese valor.")
    if r.texto is not None and r.hay_empates:
        partes.append("Decodificación ambigua: algunos bits no pudieron recuperarse, así que el texto "
                      "no se reconstruye.")
    elif r.texto is not None and not r.utf8_valido:
        partes.append("Los bytes recuperados no forman UTF‑8 válido: el texto mostrado es corrupto.")
    return " ".join(partes)


class ChipEstado(QFrame):
    """Chip con icono para el estado de recuperación de una transmisión."""

    def __init__(self, estado: str, parent=None):
        super().__init__(parent)
        texto, _tipo, nombre_ic, color, _desc = ESTADOS_TRANSMISION[estado]
        self.setObjectName("ChipEstado")
        self.setStyleSheet(
            f"QFrame#ChipEstado {{ background: {rgba(color, 0.13)}; border: 1px solid {rgba(color, 0.45)};"
            f" border-radius: 9px; }}")
        fila = QHBoxLayout(self)
        fila.setContentsMargins(8, 3, 10, 3)
        fila.setSpacing(5)
        fila.addWidget(icono_label(nombre_ic, color, 14))
        lbl = etiqueta(texto)
        lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        fila.addWidget(lbl)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)


class MiniDato(QFrame):
    """Pequeña ficha «título / valor» usada en los detalles de transmisión."""

    def __init__(self, titulo: str, valor: str, color: str = C.TEXTO, ayuda: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("MiniDato")
        if ayuda:
            self.setToolTip(ayuda)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(12, 7, 14, 8)
        caja.setSpacing(1)
        caja.addWidget(etiqueta(titulo, "MiniDatoTitulo"))
        v = etiqueta(valor, "MiniDatoValor")
        v.setStyleSheet(f"color: {color};")
        caja.addWidget(v)


def boton_copiar(obtener_texto, ayuda: str = "Copiar") -> QPushButton:
    """Botón pequeño que copia al portapapeles y confirma visualmente."""
    b = QPushButton()
    b.setObjectName("BotonFantasma")
    b.setIcon(icono("copiar", C.TEXTO_SECUNDARIO, 14))
    b.setToolTip(ayuda)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFixedSize(30, 26)

    def copiar():
        QApplication.clipboard().setText(obtener_texto())
        b.setIcon(icono("doble_check", C.VERDE, 14))
        QTimer.singleShot(1200, lambda: b.setIcon(icono("copiar", C.TEXTO_SECUNDARIO, 14)))

    b.clicked.connect(copiar)
    return b


class SecuenciaBits(QWidget):
    """Paso numerado con una secuencia binaria: copiar, expandir/contraer y resaltado."""

    def __init__(self, numero: int, titulo: str, bits: str, referencia: str | None = None,
                 bloque: int | None = None, color_iguales: str | None = None,
                 extra: QWidget | None = None, lineas: int = 3, max_bits: int = 512, parent=None):
        super().__init__(parent)
        self._args = dict(referencia=referencia, bloque=bloque, color_iguales=color_iguales)
        self._bits = bits
        self._lineas, self._max_bits = lineas, max_bits
        self._expandido = False
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(6)

        cab = QHBoxLayout()
        cab.setSpacing(8)
        cab.addWidget(_numero_paso(numero))
        cab.addWidget(etiqueta(titulo, "TituloPaso", ajustar=True), 1)
        if extra is not None:
            cab.addWidget(extra)
        cab.addWidget(etiqueta(f"{len(bits)} bits", "EtiquetaTenue"))
        cab.addWidget(boton_copiar(lambda: self._bits, "Copiar la secuencia completa"))
        self._boton_expandir = QPushButton()
        self._boton_expandir.setObjectName("BotonFantasma")
        self._boton_expandir.setFixedSize(30, 26)
        self._boton_expandir.setCursor(Qt.CursorShape.PointingHandCursor)
        self._boton_expandir.clicked.connect(self._alternar)
        cab.addWidget(self._boton_expandir)
        caja.addLayout(cab)

        self.visor = VisorBits(lineas)
        caja.addWidget(self.visor)
        self._pintar()

    def _pintar(self) -> None:
        lineas = 16 if self._expandido else self._lineas
        max_bits = 20000 if self._expandido else self._max_bits
        self.visor._lineas_maximas = lineas
        self.visor.set_bits(self._bits, max_bits=max_bits, **self._args)
        self._boton_expandir.setIcon(icono("contraer" if self._expandido else "expandir",
                                           C.TEXTO_SECUNDARIO, 14))
        self._boton_expandir.setToolTip("Contraer la secuencia" if self._expandido
                                        else "Expandir la secuencia")

    def _alternar(self) -> None:
        self._expandido = not self._expandido
        self._pintar()


def _numero_paso(numero: int) -> QLabel:
    num = QLabel(str(numero))
    num.setObjectName("NumeroPaso")
    num.setFixedSize(20, 20)
    num.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return num


def _paso(numero: int, titulo: str, widget: QWidget, extra: QWidget | None = None) -> QWidget:
    """Bloque «número + título» con su contenido debajo (se adapta a cualquier ancho)."""
    w = QWidget()
    caja = QVBoxLayout(w)
    caja.setContentsMargins(0, 0, 0, 0)
    caja.setSpacing(6)
    cab = QHBoxLayout()
    cab.setSpacing(8)
    cab.addWidget(_numero_paso(numero))
    cab.addWidget(etiqueta(titulo, "TituloPaso"), 1)
    if extra is not None:
        cab.addWidget(extra)
    caja.addLayout(cab)
    caja.addWidget(widget)
    return w


def leyenda_bits() -> QWidget:
    w = QWidget()
    fila = FlujoLayout(w, espaciado=14)
    for fondo, color, texto in (("#4A1222", C.ERROR, "Bit invertido por el canal / erróneo tras decodificar"),
                                (C.CAMPO, C.VERDE, "Bit de información recuperado correctamente"),
                                (C.CAMPO, "#D3DAEA", "Bit transmitido sin cambios"),
                                ("#3D2E12", C.AMBAR, "Bit ambiguo por empate (?)")):
        item = QWidget()
        f = QHBoxLayout(item)
        f.setContentsMargins(0, 0, 0, 0)
        f.setSpacing(6)
        muestra = QLabel("?" if color == C.AMBAR else "1")
        muestra.setAlignment(Qt.AlignmentFlag.AlignCenter)
        muestra.setFixedSize(18, 18)
        muestra.setStyleSheet(f"background:{fondo}; color:{color}; border:1px solid {C.BORDE};"
                              f" border-radius:4px; font-family:'{FUENTE_MONO_RESPALDO}';"
                              " font-size:11px; font-weight:700;")
        f.addWidget(muestra)
        f.addWidget(etiqueta(texto, "EtiquetaTenue"))
        fila.addWidget(item)
    return w


class InspectorBloque(QFrame):
    """Muestra qué ocurrió con un bloque concreto (enviado, recibido, decisión)."""

    def __init__(self, r: servicio.ResultadoTransmision, parent=None):
        super().__init__(parent)
        self.r = r
        self.setObjectName("MiniDato")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(12, 10, 12, 10)
        caja.setSpacing(4)
        self._texto = QLabel("Haz clic en un bloque del mapa para inspeccionarlo.")
        self._texto.setObjectName("EtiquetaSecundaria")
        self._texto.setTextFormat(Qt.TextFormat.RichText)
        self._texto.setWordWrap(True)
        self._texto.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(self._texto)

    def mostrar(self, i: int) -> None:
        r, n = self.r, self.r.n
        enviado = r.codificado[i * n:(i + 1) * n]
        recibido = r.recibido[i * n:(i + 1) * n]
        marcado = "".join(
            f"<span style='color:{C.ERROR}; background:#4A1222; font-weight:700;'>{b}</span>"
            if b != a else b for a, b in zip(enviado, recibido))
        unos = recibido.count("1")
        ok = r.bloque_correcto[i]
        e = r.errores_por_bloque[i]
        if r.recuperado[i] == "?":
            conclusion = f"<span style='color:{C.AMBAR};'>empate: ambiguo</span>"
            motivo = f"{e}: el bloque quedó con tantos unos como ceros y no hay mayoría"
        else:
            conclusion = (f"<span style='color:{C.VERDE};'>correcto</span>" if ok
                          else f"<span style='color:{C.ERROR};'>incorrecto</span>")
            motivo = (f"{e} ≤ t = {r.t}: la mayoría recupera el bit" if e <= r.t
                      else f"{e} &gt; t = {r.t}: la mayoría queda del lado equivocado")
        mono = f"font-family:'{FUENTE_MONO_RESPALDO}';"
        self._texto.setText(
            f"<b style='color:{C.TEXTO};'>Bloque {i + 1} de {r.total_bloques}</b><br>"
            f"Bit original: <span style='{mono}'>{r.bits_originales[i]}</span> · "
            f"Enviado: <span style='{mono}'>{enviado}</span> · "
            f"Recibido: <span style='{mono}'>{marcado}</span><br>"
            f"{unos} uno(s) y {n - unos} cero(s) → decisión "
            f"<span style='{mono}'>{r.recuperado[i]}</span> ({conclusion}). "
            f"Bits alterados: {motivo}.")


class TarjetaDetalleTransmision(QFrame):
    """Tarjeta «Detalles de transmisión» con todas las etapas, a partir de datos reales.

    `compacta=True` se usa dentro del chat (secuencias recortadas y con desplazamiento);
    `compacta=False` muestra todos los bits por defecto. `mostrar_metricas=False` omite
    las fichas de métricas cuando la vista ya las presenta (Laboratorio).
    """

    def __init__(self, r: servicio.ResultadoTransmision, compacta: bool = True,
                 mostrar_metricas: bool = True, parent=None):
        super().__init__(parent)
        self.resultado = r
        self.setObjectName("Tarjeta")
        self.setStyleSheet(f"QFrame#Tarjeta {{ background: {C.PANEL}; border: 1px solid {C.BORDE}; "
                           f"border-radius: 14px; }}")
        max_bits = 512 if compacta else 20000
        lineas = 3 if compacta else 8

        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 16, 18, 16)
        caja.setSpacing(14)

        # ---- Cabecera ---------------------------------------------------
        cab = QHBoxLayout()
        cab.setSpacing(10)
        cab.addWidget(icono_label("antena", C.ROJO, 22))
        cab.addWidget(etiqueta("Detalles de transmisión", "TituloTarjeta"))
        cab.addStretch(1)
        if not compacta:
            cab.addWidget(ChipEstado(r.estado))
        else:
            ver = QPushButton("  Vista completa")
            ver.setObjectName("BotonDetalles")
            ver.setIcon(icono("expandir", C.TEXTO_SECUNDARIO, 14))
            ver.setToolTip("Abrir todos los bits y el mapa de bloques en una ventana")
            ver.setCursor(Qt.CursorShape.PointingHandCursor)
            ver.clicked.connect(lambda: DialogoDetalle(r, self.window()).exec())
            cab.addWidget(ver)
        caja.addLayout(cab)

        # ---- Resumen textual --------------------------------------------
        resumen = etiqueta(resumen_transmision(r), "EtiquetaSecundaria", ajustar=True)
        resumen.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(resumen)

        # ---- Métricas ---------------------------------------------------
        if mostrar_metricas:
            caja.addWidget(etiqueta("PARÁMETROS DEL CÓDIGO", "Seccion"))
            param = FlujoLayout(espaciado=8)
            param.addWidget(MiniDato("Longitud n", str(r.n), ayuda="Repeticiones por bit"))
            param.addWidget(MiniDato("Probabilidad p", formato_p(r.p), ayuda="Probabilidad de inversión del BSC"))
            param.addWidget(MiniDato("Errores corregibles t", str(r.t),
                                     ayuda="t = ⌊(n − 1)/2⌋: la mayoría acierta siempre que un bloque "
                                           "tenga como máximo t bits invertidos."))
            param.addWidget(MiniDato("Tasa R", f"{r.parametros['tasa']:.3f}"))
            caja.addLayout(param)
            nota_t = etiqueta(f"t = {r.t}: cada bloque de {r.n} bits tolera hasta {r.t} inversión(es); "
                              f"con {r.t + 1} o más, la decisión por mayoría falla.",
                              "Ayuda", ajustar=True)
            caja.addWidget(nota_t)

            caja.addWidget(etiqueta("QUÉ OCURRIÓ EN EL CANAL", "Seccion"))
            canal = FlujoLayout(espaciado=8)
            canal.addWidget(MiniDato("Bits alterados", f"{r.errores_canal} / {len(r.codificado)}",
                                     C.AMBAR if r.errores_canal else C.TEXTO,
                                     "Bits codificados que el canal invirtió"))
            canal.addWidget(MiniDato("Bloques afectados", f"{r.bloques_afectados} / {r.total_bloques}",
                                     ayuda="Bloques con al menos un bit invertido"))
            canal.addWidget(MiniDato("Bloques con errores corregidos", str(r.bloques_corregidos), C.AZUL,
                                     "Bloques afectados que, aun así, se decodificaron bien"))
            canal.addWidget(MiniDato("Bloques recuperados", f"{r.bloques_recuperados} / {r.total_bloques}",
                                     C.VERDE, "Bloques decodificados correctamente (con o sin errores)"))
            canal.addWidget(MiniDato("Bloques fallidos", str(r.bloques_fallidos),
                                     C.ERROR if r.bloques_fallidos else C.TEXTO,
                                     "Bloques con más de t bits invertidos"))
            caja.addLayout(canal)

            caja.addWidget(etiqueta("TASAS DE ERROR", "Seccion"))
            tasas = FlujoLayout(espaciado=8)
            tasas.addWidget(MiniDato("BER antes de decodificar", formato_ber(r.ber_canal), C.AMBAR,
                                     "Medido: bits codificados enviados vs. recibidos"))
            if r.hay_empates:
                tasas.addWidget(MiniDato("BER sobre bits decididos", formato_ber(r.ber_con_codigo),
                                         C.AMBAR,
                                         "Errores residuales / bits decididos (excluye los empates). "
                                         "N/D si ningún bit tuvo decisión."))
                tasas.addWidget(MiniDato("Empates", f"{r.empates} / {len(r.bits_originales)}", C.AMBAR,
                                         "Bits sin decisión por empate ('?')"))
                tasas.addWidget(MiniDato("Tasa de empates", f"{r.tasa_empates:.2%}", C.AMBAR))
                tasas.addWidget(MiniDato("Errores residuales (decididos)", str(r.errores_residuales),
                                         C.ERROR if r.errores_residuales else C.TEXTO))
            else:
                tasas.addWidget(MiniDato("BER después de decodificar", formato_ber(r.ber_con_codigo),
                                         C.ERROR if r.ber_con_codigo else C.VERDE,
                                         "Medido: bits originales vs. bits decodificados"))
            tasas.addWidget(MiniDato("BER sin código (referencia)", formato_ber(r.ber_sin_codigo),
                                     ayuda="Medido: el mismo mensaje enviado sin codificar por el canal"))
            teorico = r.error_residual_teorico
            tasas.addWidget(MiniDato("Pₑ teórico", formato_ber(teorico) if teorico is not None else "N/D",
                                     C.MORADO, "Predicción teórica del núcleo, no una medición"
                                     if teorico is not None else
                                     "N/D: la fórmula teórica del núcleo solo está definida para n impar"))
            caja.addLayout(tasas)
        caja.addWidget(separador())

        # ---- Etapas -----------------------------------------------------
        caja.addWidget(etiqueta("ETAPAS DE LA TRANSMISIÓN", "Seccion"))
        if r.texto is not None:
            original = etiqueta(texto_ajustable(r.texto), "Mono", ajustar=True)
            original.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        else:
            original = etiqueta(f"{NO_DISPONIBLE} (la entrada se proporcionó directamente en bits)",
                                "NoDisponible", ajustar=True)
        caja.addWidget(_paso(1, "Mensaje original", original))
        comunes = dict(lineas=lineas, max_bits=max_bits)
        caja.addWidget(SecuenciaBits(
            2, "Representación binaria" + (" (UTF‑8)" if r.texto is not None else ""),
            r.bits_originales, bloque=8, **comunes))
        caja.addWidget(SecuenciaBits(3, f"Bits codificados (cada bit × {r.n})", r.codificado,
                                     bloque=r.n, **comunes))
        caja.addWidget(SecuenciaBits(
            4, f"Bits recibidos tras el canal BSC (p = {formato_p(r.p)})", r.recibido,
            referencia=r.codificado, bloque=r.n,
            extra=Chip(f"{r.errores_canal} alterados", "aviso" if r.errores_canal else "neutro"), **comunes))
        caja.addWidget(SecuenciaBits(
            5, "Bits decodificados por mayoría", r.recuperado, referencia=r.bits_originales,
            bloque=8, color_iguales=C.VERDE,
            extra=(Chip(f"{r.bits_erroneos} erróneos · {r.empates} empates", "aviso") if r.hay_empates
                   else Chip(f"{r.bits_erroneos} erróneos", "error" if r.bits_erroneos else "exito")),
            **comunes))

        if r.texto is not None and r.hay_empates:
            contenedor = etiqueta(
                "Decodificación ambigua: algunos bits no pudieron recuperarse. No se reconstruye el "
                "texto; la secuencia con los símbolos «?» puede inspeccionarse en el paso 5.",
                "Etiqueta", ajustar=True)
            contenedor.setStyleSheet(f"color: {C.AMBAR};")
        elif r.texto is not None:
            contenedor = QWidget()
            col_rec = QVBoxLayout(contenedor)
            col_rec.setContentsMargins(0, 0, 0, 0)
            col_rec.setSpacing(6)
            rec = Chip(texto_ajustable(r.texto_recuperado or "∅"), "exito" if r.exito else "error")
            rec.setWordWrap(True)
            rec.setStyleSheet("font-size: 13px; font-weight: 600;"
                              f" font-family: '{FUENTE_MONO}', '{FUENTE_MONO_RESPALDO}';")
            rec.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            rec.ensurePolished()
            rec.setMinimumWidth(min(rec.fontMetrics().horizontalAdvance(rec.text()) + 26, 380))
            fila_rec = QHBoxLayout()
            fila_rec.setContentsMargins(0, 0, 0, 0)
            fila_rec.addWidget(rec, 0)
            fila_rec.addStretch(1)
            col_rec.addLayout(fila_rec)
            if not r.utf8_valido:
                col_rec.addWidget(etiqueta(
                    "Mensaje corrupto: los bytes recuperados no forman UTF‑8 válido; los caracteres "
                    "irrecuperables se muestran como «�». La secuencia binaria real está en el paso 5.",
                    "Error", ajustar=True))
            elif not r.exito:
                col_rec.addWidget(etiqueta(
                    "El texto es UTF‑8 válido, pero no coincide con el mensaje original.",
                    "Error", ajustar=True))
        else:
            contenedor = etiqueta(f"{NO_DISPONIBLE} (la entrada no era texto)", "NoDisponible")
        caja.addWidget(_paso(6, "Mensaje recuperado", contenedor))
        caja.addWidget(leyenda_bits())

        # ---- Mapa de bloques e inspector --------------------------------
        caja.addWidget(separador())
        caja.addWidget(etiqueta("MAPA DE BLOQUES (CLIC PARA INSPECCIONAR)", "Seccion"))
        mapa = MapaBloques()
        mapa.set_datos(r.errores_por_bloque, r.bloque_correcto, r.bloque_ambiguo)
        caja.addWidget(mapa)
        caja.addWidget(leyenda_mapa())
        if r.total_bloques > MapaBloques.MAX_BLOQUES:
            caja.addWidget(etiqueta(f"Se muestran los primeros {MapaBloques.MAX_BLOQUES} de "
                                    f"{r.total_bloques} bloques.", "Ayuda"))
        inspector = InspectorBloque(r)
        caja.addWidget(inspector)
        mapa.bloque_elegido.connect(inspector.mostrar)
        primero = next((i for i, (e, ok) in enumerate(zip(r.errores_por_bloque, r.bloque_correcto))
                        if not ok), next((i for i, e in enumerate(r.errores_por_bloque) if e), None))
        if primero is not None and primero < MapaBloques.MAX_BLOQUES:
            mapa.seleccionar(primero)
            inspector.mostrar(primero)

        # ---- Estado final -----------------------------------------------
        _t, _tipo, nombre_ic, color, _d = ESTADOS_TRANSMISION[r.estado]
        banner = QFrame()
        banner.setObjectName("Banner")
        banner.setStyleSheet(f"QFrame#Banner {{ background: {rgba(color, 0.10)};"
                             f" border: 1px solid {rgba(color, 0.40)}; border-radius: 10px; }}")
        fila_b = QHBoxLayout(banner)
        fila_b.setContentsMargins(12, 10, 12, 10)
        fila_b.setSpacing(10)
        fila_b.addWidget(icono_label(nombre_ic, color, 20), 0, Qt.AlignmentFlag.AlignTop)
        lbl = etiqueta(descripcion_estado(r), "Etiqueta", ajustar=True)
        lbl.setStyleSheet(f"color: {color}; font-size: 13px;")
        fila_b.addWidget(lbl, 1)
        caja.addWidget(banner)


class DialogoDetalle(QDialog):
    def __init__(self, r: servicio.ResultadoTransmision, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalles de transmisión #{r.id}")
        self.resize(940, 780)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        area = AreaDesplazable()
        area.layout_interno.addWidget(TarjetaDetalleTransmision(r, compacta=False))
        area.layout_interno.addStretch(1)
        caja.addWidget(area)
