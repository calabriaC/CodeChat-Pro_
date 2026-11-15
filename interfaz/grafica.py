"""Gráficas nativas (QPainter) con la identidad visual de CodeChat Pro.

No calculan nada: dibujan los puntos que reciben.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from interfaz.estilos import C, fuente, qcolor

_SUPER = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
PISO_LOG = -6  # 10⁻⁶: los valores 0 se dibujan en el borde inferior


@dataclass
class Serie:
    nombre: str
    color: str
    puntos: list[tuple[float, float]]
    tipo: str = "linea"          # "linea" | "puntos"
    discontinua: bool = False
    etiquetas: list[str] = field(default_factory=list)


class _LienzoLog(QWidget):
    """Base con eje Y logarítmico, rejilla, leyenda y tooltip."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._mensaje_vacio = "Sin datos"
        self._titulo_y = "BER"
        self._titulo_x = ""
        self._ymin, self._ymax = -4, 0
        self._hover: tuple | None = None   # (QPointF, texto)
        self._objetivos: list[tuple[QPointF, str]] = []
        self._leyenda_abajo = False

    # ---- utilidades de escala ------------------------------------------
    def _rango_y(self, valores: list[float]) -> None:
        positivos = [v for v in valores if v > 0]
        if positivos:
            self._ymin = max(PISO_LOG, math.floor(math.log10(min(positivos))))
            self._ymax = max(self._ymin + 1, min(0, math.ceil(math.log10(max(positivos)))))
        else:
            self._ymin, self._ymax = -4, 0
        if self._ymax - self._ymin < 2:
            self._ymin = max(PISO_LOG, self._ymax - 2)

    def _area(self) -> QRectF:
        return QRectF(62, 18, max(10, self.width() - 62 - 18), max(10, self.height() - 18 - 52))

    def _y(self, valor: float, area: QRectF) -> float:
        log = self._ymin if valor <= 0 else max(self._ymin, min(self._ymax, math.log10(valor)))
        return area.bottom() - (log - self._ymin) / (self._ymax - self._ymin) * area.height()

    def _pintar_ejes_y(self, p: QPainter, area: QRectF) -> None:
        p.setFont(fuente(8.5))
        for d in range(self._ymin, self._ymax + 1):
            y = self._y(10 ** d, area)
            p.setPen(QPen(qcolor(C.BORDE, 160), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            p.setPen(QColor(C.TEXTO_SECUNDARIO))
            p.drawText(QRectF(0, y - 9, area.left() - 10, 18),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"10{str(d).translate(_SUPER)}")
        p.setPen(QPen(QColor(C.BORDE), 1.2))
        p.drawLine(area.bottomLeft(), area.bottomRight())
        p.drawLine(area.bottomLeft(), area.topLeft())
        # títulos
        p.setFont(fuente(9, QFont.Weight.DemiBold))
        p.setPen(QColor(C.TEXTO_SECUNDARIO))
        p.save()
        p.translate(14, area.center().y())
        p.rotate(-90)
        p.drawText(QRectF(-60, -9, 120, 18), Qt.AlignmentFlag.AlignCenter, self._titulo_y)
        p.restore()
        if self._titulo_x:
            p.drawText(QRectF(area.left(), self.height() - 22, area.width(), 18),
                       Qt.AlignmentFlag.AlignCenter, self._titulo_x)

    def _pintar_leyenda(self, p: QPainter, area: QRectF, items: list[tuple[str, str, str]]) -> None:
        """items: (nombre, color, forma) con forma 'linea' | 'puntos' | 'barra' | 'vertical'."""
        if not items:
            return
        p.setFont(fuente(8.5))
        fm = p.fontMetrics()
        ancho = max(fm.horizontalAdvance(n) for n, _, _ in items) + 44
        alto = len(items) * 20 + 10
        if self._leyenda_abajo:
            caja = QRectF(area.right() - ancho - 6, area.bottom() - alto - 6, ancho, alto)
        else:
            caja = QRectF(area.right() - ancho - 6, area.top() + 6, ancho, alto)
        p.setPen(QPen(QColor(C.BORDE), 1))
        p.setBrush(qcolor(C.PANEL, 225))
        p.drawRoundedRect(caja, 8, 8)
        for i, (nombre, color, forma) in enumerate(items):
            y = caja.top() + 15 + i * 20
            x = caja.left() + 10
            if forma == "barra":
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(color))
                p.drawRoundedRect(QRectF(x + 2, y - 5, 14, 10), 2, 2)
            elif forma == "vertical":
                p.setPen(QPen(QColor(color), 1.6, Qt.PenStyle.DotLine))
                p.drawLine(QPointF(x + 9, y - 7), QPointF(x + 9, y + 7))
            else:
                if forma == "linea":
                    p.setPen(QPen(QColor(color), 2))
                    p.drawLine(QPointF(x, y), QPointF(x + 18, y))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(color))
                p.drawEllipse(QPointF(x + 9, y), 3.5, 3.5)
            p.setPen(QColor(C.TEXTO))
            p.drawText(QRectF(x + 26, y - 9, ancho, 18), Qt.AlignmentFlag.AlignVCenter, nombre)

    def _pintar_hover(self, p: QPainter) -> None:
        if not self._hover:
            return
        punto, texto = self._hover
        p.setFont(fuente(8.5))
        fm = p.fontMetrics()
        lineas = texto.split("\n")
        ancho = max(fm.horizontalAdvance(l) for l in lineas) + 18
        alto = len(lineas) * (fm.height() + 1) + 12
        x = min(punto.x() + 12, self.width() - ancho - 4)
        y = max(4, punto.y() - alto - 8)
        caja = QRectF(x, y, ancho, alto)
        p.setPen(QPen(QColor(C.BORDE), 1))
        p.setBrush(qcolor(C.SUPERFICIE_ALTA, 245))
        p.drawRoundedRect(caja, 6, 6)
        p.setPen(QColor(C.TEXTO))
        p.drawText(caja.adjusted(9, 6, -9, -6), Qt.AlignmentFlag.AlignLeft, texto)

    def _pintar_vacio(self, p: QPainter) -> None:
        p.setFont(fuente(10))
        p.setPen(QColor(C.TEXTO_TENUE))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._mensaje_vacio)

    def mouseMoveEvent(self, event):
        pos = event.position()
        cercano = None
        mejor = 14.0 ** 2
        for punto, texto in self._objetivos:
            d = (punto.x() - pos.x()) ** 2 + (punto.y() - pos.y()) ** 2
            if d < mejor:
                mejor, cercano = d, (punto, texto)
        if cercano != self._hover:
            self._hover = cercano
            self.update()

    def leaveEvent(self, event):
        self._hover = None
        self.update()
        super().leaveEvent(event)


class GraficaBER(_LienzoLog):
    """BER frente a la tasa R ∈ [0, 1] con escala logarítmica en Y."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: list[Serie] = []
        self._vertical: tuple[float, str] | None = None
        self._titulo_x = "R (tasa del código)"
        # La BER crece con R, así que la esquina inferior derecha queda libre.
        self._leyenda_abajo = True

    def set_datos(self, series: list[Serie], vertical: tuple[float, str] | None = None,
                  mensaje_vacio: str = "Sin datos") -> None:
        self._series = [s for s in series if s.puntos]
        self._vertical = vertical
        self._mensaje_vacio = mensaje_vacio
        self._rango_y([y for s in self._series for _, y in s.puntos])
        self._hover = None
        self.update()

    def _x(self, valor: float, area: QRectF) -> float:
        return area.left() + valor / 1.05 * area.width()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._objetivos = []
        if not self._series:
            self._pintar_vacio(p)
            p.end()
            return
        area = self._area()
        self._pintar_ejes_y(p, area)

        p.setFont(fuente(8.5))
        for i in range(0, 6):
            v = i * 0.2
            x = self._x(v, area)
            p.setPen(QPen(qcolor(C.BORDE, 90), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
            p.setPen(QColor(C.TEXTO_SECUNDARIO))
            p.drawText(QRectF(x - 20, area.bottom() + 6, 40, 16), Qt.AlignmentFlag.AlignCenter, f"{v:.1f}")

        if self._vertical:
            xv, nombre = self._vertical
            x = self._x(xv, area)
            p.setPen(QPen(QColor(C.VERDE), 1.6, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
            p.setFont(fuente(8, QFont.Weight.DemiBold))
            p.setPen(QColor(C.VERDE))
            ancho_txt = p.fontMetrics().horizontalAdvance(nombre) + 8
            izquierda = x + 4 if x + ancho_txt < area.right() else x - ancho_txt
            p.drawText(QRectF(izquierda, area.bottom() - 20, ancho_txt, 16),
                       Qt.AlignmentFlag.AlignLeft, nombre)

        for s in self._series:
            color = QColor(s.color)
            pts = [QPointF(self._x(x, area), self._y(y, area)) for x, y in s.puntos]
            if s.tipo == "linea" and len(pts) > 1:
                ruta = QPainterPath(pts[0])
                for q in pts[1:]:
                    ruta.lineTo(q)
                p.setPen(QPen(color, 2.2, Qt.PenStyle.DashLine if s.discontinua else Qt.PenStyle.SolidLine,
                              Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(ruta)
            for i, (q, (x, y)) in enumerate(zip(pts, s.puntos)):
                radio = 4.5 if s.tipo == "puntos" else 3.6
                if y <= 0:
                    p.setPen(QPen(color, 1.6))
                    p.setBrush(QColor(C.PANEL))
                else:
                    p.setPen(QPen(QColor(C.PANEL), 1.5))
                    p.setBrush(color)
                p.drawEllipse(q, radio, radio)
                etiqueta = s.etiquetas[i] if i < len(s.etiquetas) else ""
                if etiqueta and s.tipo == "puntos":
                    p.setFont(fuente(7.5))
                    p.setPen(QColor(C.TEXTO_SECUNDARIO))
                    p.drawText(QPointF(q.x() + 6, q.y() - 6), etiqueta)
                texto_y = "0 (sin errores)" if y <= 0 else f"{y:.3e}" if y < 1e-3 else f"{y:.4f}"
                self._objetivos.append(
                    (q, f"{s.nombre}{' · ' + etiqueta if etiqueta else ''}\nR = {x:.3f}\nBER = {texto_y}"))

        items = [(s.nombre, s.color, "linea" if s.tipo == "linea" else "puntos") for s in self._series]
        if self._vertical:
            items.append((f"Capacidad C = {self._vertical[0]:.3f}", C.VERDE, "vertical"))
        self._pintar_leyenda(p, area, items)
        self._pintar_hover(p)
        p.end()


class GraficaBarras(_LienzoLog):
    """Barras agrupadas (log Y) para comparar códigos n = 3, 5, 7."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grupos: list[str] = []
        self._series: list[tuple[str, str, list[float]]] = []

    def set_datos(self, grupos: list[str], series: list[tuple[str, str, list[float]]],
                  mensaje_vacio: str = "Sin datos") -> None:
        self._grupos = grupos
        self._series = series
        self._mensaje_vacio = mensaje_vacio
        self._rango_y([v for _, _, vals in series for v in vals])
        self._hover = None
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._objetivos = []
        if not self._grupos or not self._series:
            self._pintar_vacio(p)
            p.end()
            return
        area = self._area()
        self._pintar_ejes_y(p, area)

        ancho_grupo = area.width() / len(self._grupos)
        ancho_barra = min(34.0, ancho_grupo * 0.7 / len(self._series))
        for g, nombre_grupo in enumerate(self._grupos):
            centro = area.left() + ancho_grupo * (g + 0.5)
            inicio = centro - ancho_barra * len(self._series) / 2
            for s, (nombre, color, valores) in enumerate(self._series):
                valor = valores[g]
                x = inicio + s * ancho_barra
                y = self._y(valor, area)
                rect = QRectF(x + 2, y, ancho_barra - 4, max(2.0, area.bottom() - y))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(color))
                p.drawRoundedRect(rect, 3, 3)
                texto = "0" if valor <= 0 else f"{valor:.3e}" if valor < 1e-3 else f"{valor:.4f}"
                self._objetivos.append((QPointF(rect.center().x(), rect.top()),
                                        f"{nombre_grupo} · {nombre}\nBER = {texto}"))
            p.setFont(fuente(9, QFont.Weight.DemiBold))
            p.setPen(QColor(C.TEXTO_SECUNDARIO))
            p.drawText(QRectF(centro - 50, area.bottom() + 6, 100, 16),
                       Qt.AlignmentFlag.AlignCenter, nombre_grupo)

        self._pintar_leyenda(p, area, [(n, c, "barra") for n, c, _ in self._series])
        self._pintar_hover(p)
        p.end()
