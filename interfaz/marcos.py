
"""CodeChat Pro — Signal Lab
Estilo: Signal Messenger / Neon Clean

Marcos cian y rojo de baja intensidad.
Compatible con PanelTecnico, FondoOndas y TrazosDiagonales.

No contiene lógica de codificación ni simulación BSC.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QFrame, QWidget

from interfaz.estilos import C, qcolor


CIAN = "#00C8F8"
AZUL = "#168BFF"
ROJO = "#F2384B"
BORDE_SUAVE = "#24435D"


# ------------------------------------------------------------
# GEOMETRÍA
# ------------------------------------------------------------

def ruta_biselada(
    r: QRectF,
    chaflan: float = 14.0,
    radio: float = 4.0,
) -> QPainterPath:
    """Mantiene la geometría biselada compatible con la original."""

    c = min(
        max(chaflan, 0),
        r.width() / 4,
        r.height() / 4,
    )

    radio = min(max(radio, 0), c)

    path = QPainterPath()
    path.moveTo(r.left() + c, r.top())
    path.lineTo(r.right() - radio, r.top())
    path.quadTo(
        r.right(), r.top(),
        r.right(), r.top() + radio
    )
    path.lineTo(r.right(), r.bottom() - c)
    path.lineTo(r.right() - c, r.bottom())
    path.lineTo(r.left() + radio, r.bottom())
    path.quadTo(
        r.left(), r.bottom(),
        r.left(), r.bottom() - radio
    )
    path.lineTo(r.left(), r.top() + c)
    path.closeSubpath()

    return path


def ruta_signal(
    r: QRectF,
    chaflan: float = 14.0,
) -> QPainterPath:
    """Marco con esquinas recortadas y bordes continuos."""

    x = r.left()
    y = r.top()
    w = r.width()
    h = r.height()

    c = min(
        max(chaflan, 5),
        w / 5,
        h / 5,
    )

    path = QPainterPath()
    path.moveTo(x + c, y)
    path.lineTo(x + w - c, y)
    path.lineTo(x + w, y + c)
    path.lineTo(x + w, y + h - c)
    path.lineTo(x + w - c, y + h)
    path.lineTo(x + c, y + h)
    path.lineTo(x, y + h - c)
    path.lineTo(x, y + c)
    path.closeSubpath()

    return path


def _linea(
    painter: QPainter,
    a: QPointF,
    b: QPointF,
    color: str,
    grosor: float = 2.0,
    brillo: bool = True,
):
    """Línea de acento con resplandor sutil."""

    if brillo:
        painter.setPen(
            QPen(
                qcolor(color, 32),
                grosor * 3,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.drawLine(a, b)

    painter.setPen(
        QPen(
            QColor(color),
            grosor,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    painter.drawLine(a, b)


# ------------------------------------------------------------
# PINTURA DEL MARCO
# ------------------------------------------------------------

def pintar_marco(
    p: QPainter,
    r: QRectF,
    relleno: str = C.PANEL,
    borde: str = C.BORDE,
    acento_a: str | None = C.ROJO,
    acento_b: str | None = C.AZUL_ELECTRICO,
    chaflan: float = 14.0,
    largo_acento: float = 46.0,
    marca: bool = True,
    estilo: str = "signal",
) -> None:
    """Dibuja el marco Signal Messenger."""

    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if r.width() <= 3 or r.height() <= 3:
        return

    if estilo not in ("signal", "minimal"):
        raise ValueError(
            f"Estilo desconocido: {estilo}"
        )

    # Fondo del panel.
    fondo = QLinearGradient(
        r.topLeft(),
        r.bottomLeft(),
    )

    base = QColor(relleno)
    fondo.setColorAt(0, base.lighter(108))
    fondo.setColorAt(0.45, base)
    fondo.setColorAt(1, base.darker(106))

    if estilo == "minimal":
        path = QPainterPath()
        radio = min(8.0, r.width() / 4, r.height() / 4)
        path.addRoundedRect(r, radio, radio)

        p.setPen(QPen(QColor(borde), 1))
        p.setBrush(fondo)
        p.drawPath(path)
        return

    path = ruta_signal(r, chaflan)

    p.setPen(
        QPen(QColor(BORDE_SUAVE), 1.1)
    )
    p.setBrush(fondo)
    p.drawPath(path)

    x, y = r.left(), r.top()
    w, h = r.width(), r.height()
    c = min(max(chaflan, 5), w / 5, h / 5)

    # Colores principales del marco.
    azul = acento_b or CIAN
    rojo = acento_a or ROJO

    # Azul cian en el lateral izquierdo.
    izquierda = [
        QPointF(x + c, y),
        QPointF(x, y + c),
        QPointF(x, y + h - c),
        QPointF(x + c, y + h),
    ]

    for a, b in zip(izquierda, izquierda[1:]):
        _linea(
            p, a, b,
            azul,
            grosor=1.8,
        )

    # Línea superior parcial cian.
    _linea(
        p,
        QPointF(x + c, y),
        QPointF(
            min(x + w - c, x + c + largo_acento),
            y,
        ),
        azul,
        grosor=2.4,
    )

    # Línea inferior parcial roja.
    _linea(
        p,
        QPointF(
            max(x + c, x + w - c - largo_acento),
            y + h,
        ),
        QPointF(x + w - c, y + h),
        rojo,
        grosor=2.3,
    )

    # Detalle rojo superior derecho.
    _linea(
        p,
        QPointF(
            max(x + c, x + w - c - 20),
            y,
        ),
        QPointF(x + w - c, y),
        rojo,
        grosor=2.1,
    )

    # Detalle rojo en la esquina inferior derecha.
    _linea(
        p,
        QPointF(x + w, y + h - c - 10),
        QPointF(x + w, y + h - c),
        rojo,
        grosor=2.0,
    )

    _linea(
        p,
        QPointF(x + w, y + h - c),
        QPointF(x + w - c, y + h),
        rojo,
        grosor=2.0,
    )

    # Indicadores discretos de la parte superior.
    if marca and w > 240 and h > 85:
        p.setPen(Qt.PenStyle.NoPen)

        for i in range(3):
            px = x + w - c - 68 + i * 10

            p.setBrush(
                qcolor(rojo, max(50, 210 - i * 55))
            )

            p.drawRoundedRect(
                QRectF(px, y + 7, 7, 3),
                1,
                1,
            )


# ------------------------------------------------------------
# PANEL TÉCNICO
# ------------------------------------------------------------

class PanelTecnico(QFrame):
    """Panel visual compatible con el resto de CodeChat Pro."""

    def __init__(
        self,
        parent=None,
        relleno: str = C.PANEL,
        borde: str = C.BORDE,
        acento_a: str | None = C.ROJO,
        acento_b: str | None = C.AZUL_ELECTRICO,
        chaflan: float = 14.0,
        marca: bool = True,
        margen_pintura=(0, 0, 0, 0),
        estilo: str = "signal",
    ):
        super().__init__(parent)

        self.relleno = relleno
        self.borde = borde
        self.acento_a = acento_a
        self.acento_b = acento_b
        self.chaflan = chaflan
        self.marca = marca
        self.margen_pintura = margen_pintura
        self.estilo = estilo

        self.setFrameShape(QFrame.Shape.NoFrame)

    def cambiar_estilo(self, estilo: str):
        if estilo not in ("signal", "minimal"):
            raise ValueError(
                f"Estilo no reconocido: {estilo}"
            )

        self.estilo = estilo
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)

        izq, arr, der, aba = self.margen_pintura

        r = QRectF(self.rect()).adjusted(
            izq + 3,
            arr + 3,
            -der - 3,
            -aba - 3,
        )

        pintar_marco(
            p,
            r,
            relleno=self.relleno,
            borde=self.borde,
            acento_a=self.acento_a,
            acento_b=self.acento_b,
            chaflan=self.chaflan,
            marca=self.marca,
            estilo=self.estilo,
        )

        p.end()


# ------------------------------------------------------------
# ONDAS DECORATIVAS
# ------------------------------------------------------------

def pintar_ondas(
    p: QPainter,
    r: QRectF,
    base_y: float,
    cantidad: int = 16,
    color_a: str = C.ROJO,
    color_b: str = C.AZUL_ELECTRICO,
    alfa_max: int = 70,
    pendiente: float = -0.22,
    invertir: bool = False,
) -> None:

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

            y = (
                base_y
                + i * pendiente
                + math.sin(i / 52 + fase)
                * amplitud
                * (0.35 + t)
            )

            if invertir:
                y = base_y - (y - base_y)

            if i == 0:
                ruta.moveTo(QPointF(x, y))
            else:
                ruta.lineTo(QPointF(x, y))

        grad = QLinearGradient(
            r.topLeft(),
            r.topRight(),
        )

        alfa = int(
            alfa_max
            * (0.25 + 0.75 * k / max(1, cantidad - 1))
        )

        grad.setColorAt(0, qcolor(color_a, alfa))
        grad.setColorAt(1, qcolor(color_b, alfa))

        p.setPen(QPen(grad, 1.0))
        p.drawPath(ruta)


class FondoOndas(QWidget):
    """Fondo decorativo con ondas de señal."""

    def paintEvent(self, event):
        p = QPainter(self)

        r = QRectF(self.rect())
        p.fillRect(r, QColor(C.FONDO))

        esquina = QRectF(
            r.right() - 520,
            r.bottom() - 220,
            520,
            220,
        )

        pintar_ondas(
            p,
            esquina,
            esquina.bottom() - 30,
            cantidad=12,
            color_a=C.AZUL_ELECTRICO,
            color_b=C.ROJO,
            alfa_max=45,
            pendiente=-0.18,
        )

        p.end()


# ------------------------------------------------------------
# MARCA SIGNAL LAB
# ------------------------------------------------------------

class TrazosDiagonales(QWidget):
    """Pequeños trazos rojos de identidad visual."""

    def __init__(
        self,
        cantidad: int = 4,
        color: str = C.ROJO,
        parent=None,
    ):
        super().__init__(parent)

        self._cantidad = cantidad
        self._color = color

        self.setFixedSize(
            8 + cantidad * 10,
            14,
        )

    def paintEvent(self, event):
        p = QPainter(self)

        p.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )
        p.setPen(Qt.PenStyle.NoPen)

        for i in range(self._cantidad):
            x = 4 + i * 10

            path = QPainterPath()
            path.moveTo(x + 5, 1)
            path.lineTo(x + 11, 1)
            path.lineTo(x + 6, 13)
            path.lineTo(x, 13)
            path.closeSubpath()

            p.setBrush(
                qcolor(
                    self._color,
                    max(40, 255 - i * 45),
                )
            )

            p.drawPath(path)

        p.end()
