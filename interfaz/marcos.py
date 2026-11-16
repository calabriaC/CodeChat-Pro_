"""Marcos técnicos «Signal Lab»: paneles con esquinas biseladas y filos luminosos.

Solo presentación: estos widgets dibujan fondos y bordes; no contienen lógica.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QWidget

from interfaz.estilos import C, qcolor


def ruta_biselada(r: QRectF, chaflan: float = 14.0, radio: float = 4.0) -> QPainterPath:
    """Rectángulo con bisel en la esquina superior izquierda e inferior derecha."""
    ruta = QPainterPath()
    ruta.moveTo(r.left() + chaflan, r.top())
    ruta.lineTo(r.right() - radio, r.top())
    ruta.quadTo(r.right(), r.top(), r.right(), r.top() + radio)
    ruta.lineTo(r.right(), r.bottom() - chaflan)
    ruta.lineTo(r.right() - chaflan, r.bottom())
    ruta.lineTo(r.left() + radio, r.bottom())
    ruta.quadTo(r.left(), r.bottom(), r.left(), r.bottom() - radio)
    ruta.lineTo(r.left(), r.top() + chaflan)
    ruta.closeSubpath()
    return ruta


def _linea_luminosa(p: QPainter, a: QPointF, b: QPointF, color: str, grosor: float = 1.6) -> None:
    for ancho, alfa in ((grosor * 5, 30), (grosor * 2.6, 70), (grosor, 255)):
        p.setPen(QPen(qcolor(color, alfa), ancho, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(a, b)


def pintar_marco(p: QPainter, r: QRectF, relleno: str = C.PANEL, borde: str = C.BORDE,
                 acento_a: str | None = C.ROJO, acento_b: str | None = C.AZUL_ELECTRICO,
                 chaflan: float = 14.0, largo_acento: float = 46.0, marca: bool = True) -> None:
    """Fondo + borde biselado + filos luminosos en las esquinas biseladas."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    ruta = ruta_biselada(r, chaflan)
    fondo = QLinearGradient(r.topLeft(), r.bottomLeft())
    base = QColor(relleno)
    fondo.setColorAt(0, base.lighter(112))
    fondo.setColorAt(0.25, base)
    fondo.setColorAt(1, base.darker(108))
    p.setPen(QPen(QColor(borde), 1))
    p.setBrush(fondo)
    p.drawPath(ruta)

    if acento_a:
        # Bisel superior izquierdo + tramo del borde superior
        _linea_luminosa(p, QPointF(r.left(), r.top() + chaflan + 18), QPointF(r.left(), r.top() + chaflan), acento_a)
        _linea_luminosa(p, QPointF(r.left(), r.top() + chaflan), QPointF(r.left() + chaflan, r.top()), acento_a)
        _linea_luminosa(p, QPointF(r.left() + chaflan, r.top()),
                        QPointF(r.left() + chaflan + largo_acento, r.top()), acento_a)
    if acento_b:
        # Bisel inferior derecho + tramo del borde inferior
        _linea_luminosa(p, QPointF(r.right(), r.bottom() - chaflan - 18),
                        QPointF(r.right(), r.bottom() - chaflan), acento_b)
        _linea_luminosa(p, QPointF(r.right(), r.bottom() - chaflan), QPointF(r.right() - chaflan, r.bottom()), acento_b)
        _linea_luminosa(p, QPointF(r.right() - chaflan, r.bottom()),
                        QPointF(r.right() - chaflan - largo_acento, r.bottom()), acento_b)
    if marca and acento_a:
        # Pequeño indicador de transmisión: tres trazos diagonales en la esquina superior derecha
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            x = r.right() - 18 - i * 7
            trazo = QPainterPath()
            trazo.moveTo(x, r.top() + 4)
            trazo.lineTo(x + 4, r.top() + 4)
            trazo.lineTo(x + 1, r.top() + 9)
            trazo.lineTo(x - 3, r.top() + 9)
            trazo.closeSubpath()
            p.setBrush(qcolor(acento_a, 200 - i * 55))
            p.drawPath(trazo)


class PanelTecnico(QFrame):
    """QFrame que se dibuja como un panel técnico biselado."""

    def __init__(self, parent=None, relleno: str = C.PANEL, borde: str = C.BORDE,
                 acento_a: str | None = C.ROJO, acento_b: str | None = C.AZUL_ELECTRICO,
                 chaflan: float = 14.0, marca: bool = True, margen_pintura=(0, 0, 0, 0)):
        super().__init__(parent)
        self.relleno, self.borde = relleno, borde
        self.acento_a, self.acento_b = acento_a, acento_b
        self.chaflan, self.marca = chaflan, marca
        self.margen_pintura = margen_pintura

    def paintEvent(self, _event):
        p = QPainter(self)
        izq, arr, der, aba = self.margen_pintura
        r = QRectF(self.rect()).adjusted(izq + 1.5, arr + 1.5, -der - 1.5, -aba - 1.5)
        pintar_marco(p, r, self.relleno, self.borde, self.acento_a, self.acento_b,
                     self.chaflan, marca=self.marca)
        p.end()


def pintar_ondas(p: QPainter, r: QRectF, base_y: float, cantidad: int = 16,
                 color_a: str = C.ROJO, color_b: str = C.AZUL_ELECTRICO, alfa_max: int = 70,
                 pendiente: float = -0.22, invertir: bool = False) -> None:
    """Ondas vectoriales finas que degradan de rojo a azul (decoración de fondo)."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for k in range(cantidad):
        ruta = QPainterPath()
        fase = k * 0.16
        amplitud = 22 + k * 2.2
        paso = 6
        for i in range(0, int(r.width()) + paso, paso):
            x = r.left() + i
            t = i / max(1.0, r.width())
            y = base_y + i * pendiente + math.sin(i / 52 + fase) * amplitud * (0.35 + t)
            if invertir:
                y = base_y - (y - base_y)
            if i == 0:
                ruta.moveTo(QPointF(x, y))
            else:
                ruta.lineTo(QPointF(x, y))
        grad = QLinearGradient(r.topLeft(), r.topRight())
        alfa = int(alfa_max * (0.25 + 0.75 * k / max(1, cantidad - 1)))
        grad.setColorAt(0, qcolor(color_a, alfa))
        grad.setColorAt(1, qcolor(color_b, alfa))
        p.setPen(QPen(grad, 1.0))
        p.drawPath(ruta)


class FondoOndas(QWidget):
    """Widget de fondo con ondas en las esquinas (se coloca detrás del contenido)."""

    def paintEvent(self, _event):
        p = QPainter(self)
        r = QRectF(self.rect())
        p.fillRect(r, QColor(C.FONDO))
        esquina = QRectF(r.right() - 520, r.bottom() - 220, 520, 220)
        pintar_ondas(p, esquina, esquina.bottom() - 30, 12, C.AZUL_ELECTRICO, C.ROJO, 55, pendiente=-0.18)
        p.end()


class TrazosDiagonales(QWidget):
    """Trazos diagonales rojos (detalle de marca «Signal Lab»)."""

    def __init__(self, cantidad: int = 4, color: str = C.ROJO, parent=None):
        super().__init__(parent)
        self._cantidad, self._color = cantidad, color
        self.setFixedSize(8 + cantidad * 10, 14)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(self._cantidad):
            x = 4 + i * 10
            trazo = QPainterPath()
            trazo.moveTo(x + 5, 1)
            trazo.lineTo(x + 11, 1)
            trazo.lineTo(x + 6, 13)
            trazo.lineTo(x, 13)
            trazo.closeSubpath()
            p.setBrush(qcolor(self._color, 255 - i * 45))
            p.drawPath(trazo)
        p.end()
