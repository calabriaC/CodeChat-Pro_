"""Ilustraciones vectoriales conceptuales de CodeChat Pro (solo presentación).

Cada ilustración se dibuja con QPainter en un lienzo lógico de 200 × 120 que se
escala al tamaño del widget, así que se ve nítida a cualquier resolución.
Lenguaje visual común: trazos uniformes, resplandor neón suave, cian/azul como
color base, rojo para errores y un color de acento por concepto.

Son ilustrativas: no calculan nada ni sustituyen a las fórmulas.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from interfaz.estilos import C, FAMILIAS_MONO, FAMILIAS_UI, qcolor

CIAN = "#00C8F8"
AZUL = C.AZUL_ELECTRICO
ROJO = C.ROJO
VERDE = C.VERDE
AMBAR = C.AMBAR
VIOLETA = "#B78AFF"
TEXTO = C.TEXTO
ANCHO, ALTO = 200.0, 120.0
GROSOR = 1.3   # trazos algo más gruesos, estilo de la referencia


# ---------------------------------------------------------------------------
# Primitivas con resplandor
# ---------------------------------------------------------------------------
def _pluma(color: str, ancho: float, alfa: int = 255, estilo=Qt.PenStyle.SolidLine) -> QPen:
    pen = QPen(qcolor(color, alfa), ancho, estilo, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    return pen


def _trazo(p: QPainter, ruta: QPainterPath, color: str, ancho: float = 2.0, brillo: bool = True) -> None:
    """Trazo con resplandor neón suave (dos halos + línea nítida)."""
    p.setBrush(Qt.BrushStyle.NoBrush)
    ancho *= GROSOR
    if brillo:
        for factor, alfa in ((4.0, 26), (2.2, 64)):
            p.setPen(_pluma(color, ancho * factor, alfa))
            p.drawPath(ruta)
    p.setPen(_pluma(color, ancho))
    p.drawPath(ruta)


def _linea(p: QPainter, a: tuple, b: tuple, color: str, ancho: float = 2.0, brillo: bool = True,
           alfa: int = 255) -> None:
    ruta = QPainterPath(QPointF(*a))
    ruta.lineTo(QPointF(*b))
    if alfa < 255:
        p.setPen(_pluma(color, ancho, alfa))
        p.drawPath(ruta)
    else:
        _trazo(p, ruta, color, ancho, brillo)


def _circulo(p: QPainter, c: tuple, r: float, color: str, relleno: int = 40, ancho: float = 2.0) -> None:
    ruta = QPainterPath()
    ruta.addEllipse(QPointF(*c), r, r)
    p.setPen(Qt.PenStyle.NoPen)
    grad = QRadialGradient(QPointF(*c), r)
    grad.setColorAt(0, qcolor(color, min(255, relleno * 2)))
    grad.setColorAt(1, qcolor(color, relleno // 2))
    p.setBrush(grad)
    p.drawPath(ruta)
    _trazo(p, ruta, color, ancho)


def _caja(p: QPainter, r: QRectF, color: str, relleno: int = 30, ancho: float = 1.6, radio: float = 4) -> None:
    ruta = QPainterPath()
    ruta.addRoundedRect(r, radio, radio)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(color, relleno))
    p.drawPath(ruta)
    _trazo(p, ruta, color, ancho)


def _texto(p: QPainter, centro: tuple, texto: str, color: str = TEXTO, tam: float = 11,
           negrita: bool = True, mono: bool = True) -> None:
    f = QFont()
    f.setFamilies(FAMILIAS_MONO if mono else FAMILIAS_UI)
    f.setPointSizeF(tam)
    f.setWeight(QFont.Weight.Bold if negrita else QFont.Weight.Medium)
    p.setFont(f)
    p.setPen(qcolor(color))
    p.drawText(QRectF(centro[0] - 70, centro[1] - 12, 140, 24), Qt.AlignmentFlag.AlignCenter, texto)


def _flecha(p: QPainter, a: tuple, b: tuple, color: str, ancho: float = 2.0, punta: float = 6) -> None:
    _linea(p, a, b, color, ancho)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    ruta = QPainterPath(QPointF(b[0] - punta * math.cos(ang - 0.5), b[1] - punta * math.sin(ang - 0.5)))
    ruta.lineTo(QPointF(*b))
    ruta.lineTo(QPointF(b[0] - punta * math.cos(ang + 0.5), b[1] - punta * math.sin(ang + 0.5)))
    _trazo(p, ruta, color, ancho)


def _puntos_fondo(p: QPainter, color: str = CIAN) -> None:
    """Retícula de puntos tenue (detalle geométrico discreto)."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(color, 28))
    for x in range(12, 200, 16):
        for y in range(10, 120, 16):
            p.drawEllipse(QPointF(x, y), 0.8, 0.8)


def _alerta(p: QPainter, c: tuple, r: float = 7) -> None:
    """Pequeño triángulo de alerta rojo."""
    ruta = QPainterPath(QPointF(c[0], c[1] - r))
    ruta.lineTo(QPointF(c[0] + r * 0.95, c[1] + r * 0.7))
    ruta.lineTo(QPointF(c[0] - r * 0.95, c[1] + r * 0.7))
    ruta.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(ROJO, 60))
    p.drawPath(ruta)
    _trazo(p, ruta, ROJO, 1.6)
    _linea(p, (c[0], c[1] - r * 0.35), (c[0], c[1] + r * 0.2), ROJO, 1.6, brillo=False)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(ROJO))
    p.drawEllipse(QPointF(c[0], c[1] + r * 0.45), 0.9, 0.9)


def _bit(p: QPainter, c: tuple, valor: str, color: str, lado: float = 18, tam: float = 9.5) -> None:
    _caja(p, QRectF(c[0] - lado / 2, c[1] - lado / 2, lado, lado), color, 40, 1.4, 3)
    _texto(p, c, valor, TEXTO if color != ROJO else "#FFD6DB", tam)


# ---------------------------------------------------------------------------
# Conceptos de Teoría
# ---------------------------------------------------------------------------
def _distancia_minima(p: QPainter) -> None:
    _puntos_fondo(p)
    a, b = (48, 66), (152, 66)
    _linea(p, (a[0] + 16, a[1]), (b[0] - 16, b[1]), CIAN, 2)
    for i in range(1, 6):                        # marcas: posiciones que difieren
        x = a[0] + 16 + i * (b[0] - a[0] - 32) / 6
        _linea(p, (x, a[1] - 5), (x, a[1] + 5), CIAN, 1.4, brillo=False)
    _flecha(p, (100, 34), (68, 34), VIOLETA, 1.6, 5)       # cota de distancia
    _flecha(p, (100, 34), (132, 34), VIOLETA, 1.6, 5)
    _linea(p, (a[0], 28), (a[0], 44), VIOLETA, 1.2, brillo=False, alfa=170)
    _linea(p, (b[0], 28), (b[0], 44), VIOLETA, 1.2, brillo=False, alfa=170)
    _texto(p, (100, 22), "d = n", VIOLETA, 9)
    _circulo(p, a, 15, AZUL, 70)
    _circulo(p, b, 15, ROJO, 70)
    _texto(p, a, "000", TEXTO, 8)
    _texto(p, b, "111", TEXTO, 8)
    _texto(p, (100, 96), "Hamming", C.TEXTO_SECUNDARIO, 8, negrita=False)


def _deteccion(p: QPainter) -> None:
    c = (92, 62)
    for r, alfa in ((16, 255), (30, 190), (44, 120)):
        ruta = QPainterPath()
        ruta.addEllipse(QPointF(*c), r, r)
        p.setPen(_pluma(CIAN, 1.3, alfa))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(ruta)
    _linea(p, (c[0] - 48, c[1]), (c[0] + 48, c[1]), CIAN, 0.8, brillo=False, alfa=90)
    _linea(p, (c[0], c[1] - 48), (c[0], c[1] + 48), CIAN, 0.8, brillo=False, alfa=90)
    # Barrido del radar
    grad = QRadialGradient(QPointF(*c), 46)
    grad.setColorAt(0, qcolor(CIAN, 110))
    grad.setColorAt(1, qcolor(CIAN, 0))
    sector = QPainterPath(QPointF(*c))
    sector.arcTo(QRectF(c[0] - 46, c[1] - 46, 92, 92), 20, 55)
    sector.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawPath(sector)
    ang = math.radians(20)
    _linea(p, c, (c[0] + 46 * math.cos(ang), c[1] - 46 * math.sin(ang)), CIAN, 1.8)
    # Eco detectado + alerta
    _circulo(p, (118, 40), 4, ROJO, 120, 1.6)
    _alerta(p, (150, 30), 9)
    _texto(p, (152, 92), "error", ROJO, 8.5)


def _correccion(p: QPainter) -> None:
    _puntos_fondo(p)
    ruta = QPainterPath(QPointF(100, 14))
    ruta.cubicTo(QPointF(116, 24), QPointF(130, 26), QPointF(140, 26))
    ruta.cubicTo(QPointF(140, 72), QPointF(124, 96), QPointF(100, 108))
    ruta.cubicTo(QPointF(76, 96), QPointF(60, 72), QPointF(60, 26))
    ruta.cubicTo(QPointF(70, 26), QPointF(84, 24), QPointF(100, 14))
    grad = QLinearGradient(QPointF(100, 14), QPointF(100, 108))
    grad.setColorAt(0, qcolor(AZUL, 90))
    grad.setColorAt(1, qcolor(AZUL, 15))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawPath(ruta)
    _trazo(p, ruta, CIAN, 2.2)
    check = QPainterPath(QPointF(84, 62))
    check.lineTo(QPointF(96, 74))
    check.lineTo(QPointF(118, 48))
    _trazo(p, check, VERDE, 3)
    _bit(p, (32, 46), "0", ROJO, 16, 8.5)
    _flecha(p, (42, 46), (56, 52), C.TEXTO_TENUE, 1.2, 4)
    _bit(p, (168, 46), "1", CIAN, 16, 8.5)
    _texto(p, (168, 72), "t", CIAN, 10)


def _tasa(p: QPainter) -> None:
    base = 98
    alturas = [(30, CIAN, 255), (62, AZUL, 150), (62, AZUL, 150), (62, AZUL, 150)]
    for i, (h, color, alfa) in enumerate(alturas):
        x = 44 + i * 26
        r = QRectF(x, base - h, 18, h)
        grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        grad.setColorAt(0, qcolor(color, alfa // 2))
        grad.setColorAt(1, qcolor(color, alfa // 6))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(r, 3, 3)
        ruta = QPainterPath()
        ruta.addRoundedRect(r, 3, 3)
        _trazo(p, ruta, color, 1.5, brillo=i == 0)
    _linea(p, (36, base + 2), (152, base + 2), C.TEXTO_TENUE, 1.2, brillo=False)
    _texto(p, (53, base + 12), "k", CIAN, 9)
    _texto(p, (110, base + 12), "n", AZUL, 9)
    _flecha(p, (142, 82), (170, 30), AMBAR, 2, 7)
    _texto(p, (170, 52), "R", AMBAR, 11)


def _bsc(p: QPainter) -> None:
    for x, lado in ((22, "x"), (152, "y")):
        _caja(p, QRectF(x, 40, 28, 40), CIAN, 25, 1.6, 5)
        _texto(p, (x + 14, 52), "0", TEXTO, 8.5)
        _texto(p, (x + 14, 68), "1", TEXTO, 8.5)
        _texto(p, (x + 14, 92), lado, C.TEXTO_SECUNDARIO, 8.5, negrita=False)
    onda = QPainterPath(QPointF(52, 60))
    for i in range(0, 97):
        x = 52 + i
        if 38 <= i <= 60:
            continue
        y = 60 + 8 * math.sin(i / 5.0)
        if i == 61:
            onda.moveTo(QPointF(x, y))
        else:
            onda.lineTo(QPointF(x, y))
    _trazo(p, onda, CIAN, 1.8)
    rayo = QPainterPath(QPointF(92, 36))
    for x, y in ((104, 54), (96, 58), (110, 84)):
        rayo.lineTo(QPointF(x, y))
    _trazo(p, rayo, ROJO, 2.4)
    _texto(p, (101, 24), "p", ROJO, 11)
    _texto(p, (101, 100), "1 − p", C.TEXTO_SECUNDARIO, 8, negrita=False)


def _mayoria(p: QPainter) -> None:
    _puntos_fondo(p)
    entradas = [((40, 32), "1", CIAN), ((40, 60), "1", CIAN), ((40, 88), "0", ROJO)]
    destino = (148, 60)
    for (x, y), _v, color in entradas:
        ruta = QPainterPath(QPointF(x + 12, y))
        ruta.cubicTo(QPointF(90, y), QPointF(100, destino[1]), QPointF(destino[0] - 18, destino[1]))
        _trazo(p, ruta, color, 1.5, brillo=color == CIAN)
    for (x, y), v, color in entradas:
        _bit(p, (x, y), v, color, 20, 10)
    _circulo(p, destino, 17, VERDE, 70, 2.2)
    _texto(p, destino, "1", TEXTO, 13)
    _texto(p, (104, 26), "2 > 1", VERDE, 8.5)


def _ber(p: QPainter) -> None:
    bits = "10110100"
    errores = {2, 5}
    for i, b in enumerate(bits):
        x = 30 + i * 20
        _bit(p, (x, 78), b if i not in errores else ("0" if b == "1" else "1"),
             ROJO if i in errores else CIAN, 16, 8.5)
    # Medidor
    c = (100, 46)
    arco = QPainterPath()
    arco.arcMoveTo(QRectF(c[0] - 28, c[1] - 28, 56, 56), 180)
    arco.arcTo(QRectF(c[0] - 28, c[1] - 28, 56, 56), 180, -180)
    _trazo(p, arco, AMBAR, 1.8)
    ang = math.radians(140)
    _linea(p, c, (c[0] + 22 * math.cos(ang), c[1] - 22 * math.sin(ang)), AMBAR, 2)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(AMBAR))
    p.drawEllipse(QPointF(*c), 2.6, 2.6)
    _texto(p, (100, 104), "2 / 8", AMBAR, 9)
    for i in errores:
        _linea(p, (30 + i * 20, 68), (30 + i * 20, 60), ROJO, 1.2, brillo=False, alfa=200)


def _probabilidad_residual(p: QPainter) -> None:
    _linea(p, (34, 98), (176, 98), C.TEXTO_TENUE, 1.2, brillo=False)
    _linea(p, (34, 98), (34, 18), C.TEXTO_TENUE, 1.2, brillo=False)
    curva = QPainterPath(QPointF(34, 92))
    for i in range(0, 141):
        x = 34 + i
        y = 96 - 70 * math.exp(-((i - 42) / 26.0) ** 2)
        curva.lineTo(QPointF(x, y))
    cola = QPainterPath(QPointF(110, 98))
    for i in range(76, 141):
        cola.lineTo(QPointF(34 + i, 96 - 70 * math.exp(-((i - 42) / 26.0) ** 2)))
    cola.lineTo(QPointF(174, 98))
    cola.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(ROJO, 70))
    p.drawPath(cola)
    _trazo(p, curva, VIOLETA, 2)
    _linea(p, (110, 98), (110, 40), ROJO, 1.4, brillo=False, alfa=220)
    _texto(p, (110, 106), "t+1", ROJO, 7.5)
    _texto(p, (150, 30), "Σ", VIOLETA, 20)
    _alerta(p, (140, 74), 7)


def _entropia(p: QPainter) -> None:
    c = (100, 60)
    nodos = []
    for i in range(6):
        ang = math.radians(90 + i * 60)
        nodos.append((c[0] + 52 * math.cos(ang), c[1] - 40 * math.sin(ang), "0" if i % 2 else "1"))
    for (x, y, v) in nodos:
        _linea(p, c, (x, y), CIAN if v == "1" else ROJO, 1.2, brillo=False, alfa=160)
    for i in range(6):
        a, b = nodos[i], nodos[(i + 1) % 6]
        _linea(p, (a[0], a[1]), (b[0], b[1]), VIOLETA, 1, brillo=False, alfa=90)
    hexa = QPainterPath()
    for i in range(6):
        ang = math.radians(30 + i * 60)
        q = QPointF(c[0] + 18 * math.cos(ang), c[1] + 18 * math.sin(ang))
        hexa.moveTo(q) if i == 0 else hexa.lineTo(q)
    hexa.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(VIOLETA, 60))
    p.drawPath(hexa)
    _trazo(p, hexa, VIOLETA, 2)
    _texto(p, c, "?", TEXTO, 14)
    for (x, y, v) in nodos:
        _circulo(p, (x, y), 9, CIAN if v == "1" else ROJO, 60, 1.5)
        _texto(p, (x, y), v, TEXTO, 8)


def _longitud(p: QPainter) -> None:
    _puntos_fondo(p)
    _bit(p, (30, 60), "1", CIAN, 22, 11)
    _flecha(p, (46, 60), (64, 60), C.TEXTO_TENUE, 1.4, 5)
    for i in range(5):
        _bit(p, (82 + i * 22, 60), "1", AZUL, 18, 9)
    llave = QPainterPath(QPointF(72, 42))
    llave.lineTo(QPointF(72, 36))
    llave.lineTo(QPointF(178, 36))
    llave.lineTo(QPointF(178, 42))
    _trazo(p, llave, ROJO, 1.6)
    _texto(p, (125, 24), "n", ROJO, 12)
    _texto(p, (125, 90), "repeticiones", C.TEXTO_SECUNDARIO, 8, negrita=False)


def _dimension(p: QPainter) -> None:
    marco = QRectF(36, 40, 128, 40)
    _caja(p, marco, AZUL, 18, 1.4, 6)
    for i in range(5):
        x = 50 + i * 25
        if i == 0:
            _bit(p, (x, 60), "1", CIAN, 20, 10)
        else:
            _caja(p, QRectF(x - 9, 51, 18, 18), C.TEXTO_TENUE, 20, 1.0, 3)
    _linea(p, (50, 30), (50, 24), CIAN, 1.4, brillo=False)
    _texto(p, (50, 16), "k = 1", CIAN, 9)
    _texto(p, (126, 96), "redundancia", C.TEXTO_SECUNDARIO, 8, negrita=False)
    _linea(p, (72, 86), (164, 86), C.TEXTO_TENUE, 1, brillo=False, alfa=180)


def _palabras(p: QPainter) -> None:
    _puntos_fondo(p)
    for j, (texto, color) in enumerate((("0 0 0 0 0", AZUL), ("1 1 1 1 1", ROJO))):
        r = QRectF(44, 22 + j * 44, 112, 30)
        _caja(p, r, color, 30, 1.6, 6)
        _texto(p, (100, r.center().y()), texto, TEXTO, 10)
    _linea(p, (164, 37), (164, 81), VIOLETA, 1.4)
    _linea(p, (160, 37), (164, 37), VIOLETA, 1.4, brillo=False)
    _linea(p, (160, 81), (164, 81), VIOLETA, 1.4, brillo=False)
    _texto(p, (184, 59), "M", VIOLETA, 11)
    _texto(p, (100, 108), "M = 2 palabras", C.TEXTO_SECUNDARIO, 8, negrita=False)


def _capacidad(p: QPainter) -> None:
    c = (100, 78)
    arco = QPainterPath()
    arco.arcMoveTo(QRectF(c[0] - 46, c[1] - 46, 92, 92), 180)
    arco.arcTo(QRectF(c[0] - 46, c[1] - 46, 92, 92), 180, -180)
    p.setPen(_pluma(C.TEXTO_TENUE, 6, 90))
    p.drawPath(arco)
    lleno = QPainterPath()
    lleno.arcMoveTo(QRectF(c[0] - 46, c[1] - 46, 92, 92), 180)
    lleno.arcTo(QRectF(c[0] - 46, c[1] - 46, 92, 92), 180, -118)
    _trazo(p, lleno, VERDE, 4)
    ang = math.radians(62)
    _linea(p, c, (c[0] + 36 * math.cos(ang), c[1] - 36 * math.sin(ang)), TEXTO, 2)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(VERDE))
    p.drawEllipse(QPointF(*c), 3.4, 3.4)
    _texto(p, (100, 100), "C = 1 − H₂", VERDE, 8.5)
    for i in range(3):
        _flecha(p, (18, 40 + i * 14), (38, 40 + i * 14), CIAN, 1.2, 4)


# ---------------------------------------------------------------------------
# Emblemas de las secciones
# ---------------------------------------------------------------------------
def _emb_chat(p: QPainter) -> None:
    _caja(p, QRectF(30, 22, 92, 46), CIAN, 30, 2, 10)
    cola = QPainterPath(QPointF(48, 68))
    cola.lineTo(QPointF(42, 82))
    cola.lineTo(QPointF(62, 68))
    _trazo(p, cola, CIAN, 2)
    _texto(p, (76, 45), "1011", TEXTO, 11)
    _caja(p, QRectF(98, 56, 76, 38), ROJO, 30, 2, 10)
    onda = QPainterPath(QPointF(108, 75))
    for i in range(0, 57):
        onda.lineTo(QPointF(108 + i, 75 + 6 * math.sin(i / 4.0)))
    _trazo(p, onda, ROJO, 1.6)


def _emb_dual(p: QPainter) -> None:
    for x, color, letra in ((40, AZUL, "A"), (160, ROJO, "B")):
        _circulo(p, (x, 60), 20, color, 60, 2)
        _texto(p, (x, 60), letra, TEXTO, 14)
    _flecha(p, (66, 50), (134, 50), CIAN, 1.8, 6)
    _flecha(p, (134, 70), (66, 70), ROJO, 1.8, 6)
    _texto(p, (100, 36), "BSC", C.TEXTO_SECUNDARIO, 8)


def _emb_laboratorio(p: QPainter) -> None:
    matraz = QPainterPath(QPointF(86, 16))
    matraz.lineTo(QPointF(86, 46))
    matraz.lineTo(QPointF(58, 98))
    matraz.quadTo(QPointF(56, 106), QPointF(66, 106))
    matraz.lineTo(QPointF(134, 106))
    matraz.quadTo(QPointF(144, 106), QPointF(142, 98))
    matraz.lineTo(QPointF(114, 46))
    matraz.lineTo(QPointF(114, 16))
    _trazo(p, matraz, CIAN, 2.2)
    _linea(p, (80, 16), (120, 16), CIAN, 2.2)
    liquido = QPainterPath(QPointF(70, 80))
    for i in range(0, 61):
        liquido.lineTo(QPointF(70 + i, 80 + 3 * math.sin(i / 5.0)))
    liquido.lineTo(QPointF(140, 102))
    liquido.lineTo(QPointF(60, 102))
    liquido.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(qcolor(ROJO, 70))
    p.drawPath(liquido)
    _texto(p, (100, 92), "01", TEXTO, 10)
    for x, y in ((150, 30), (162, 46), (146, 58)):
        _circulo(p, (x, y), 3.5, CIAN, 80, 1.2)


def _emb_analisis(p: QPainter) -> None:
    for i, h in enumerate((30, 50, 70)):
        _caja(p, QRectF(40 + i * 30, 98 - h, 20, h), AZUL, 40, 1.6, 3)
    curva = QPainterPath(QPointF(36, 30))
    curva.cubicTo(QPointF(80, 40), QPointF(120, 80), QPointF(172, 92))
    _trazo(p, curva, ROJO, 2)
    _linea(p, (32, 100), (176, 100), C.TEXTO_TENUE, 1.2, brillo=False)
    _texto(p, (160, 34), "BER", AMBAR, 9)


def _emb_teoria(p: QPainter) -> None:
    for ang in (0, 60, 120):
        p.save()
        p.translate(100, 60)
        p.rotate(ang)
        orbita = QPainterPath()
        orbita.addEllipse(QPointF(0, 0), 52, 18)
        _trazo(p, orbita, CIAN if ang != 60 else ROJO, 1.4)
        p.restore()
    _circulo(p, (100, 60), 13, VIOLETA, 80, 2)
    _texto(p, (100, 60), "Σ", TEXTO, 12)


def _emb_historial(p: QPainter) -> None:
    _circulo(p, (64, 60), 34, CIAN, 25, 2)
    _linea(p, (64, 60), (64, 38), TEXTO, 2)
    _linea(p, (64, 60), (80, 68), ROJO, 2)
    for i in range(4):
        y = 34 + i * 16
        _linea(p, (114, y), (176 - i * 10, y), AZUL if i % 2 == 0 else C.TEXTO_TENUE, 2.4, brillo=i == 0)


DIBUJOS = {
    # Teoría
    "dmin": (_distancia_minima, VIOLETA),
    "det": (_deteccion, AMBAR),
    "t": (_correccion, AZUL),
    "R": (_tasa, CIAN),
    "p": (_bsc, ROJO),
    "maj": (_mayoria, VERDE),
    "BER": (_ber, AMBAR),
    "Pe": (_probabilidad_residual, VIOLETA),
    "H2": (_entropia, VIOLETA),
    "n": (_longitud, ROJO),
    "k": (_dimension, CIAN),
    "M": (_palabras, VIOLETA),
    "C": (_capacidad, VERDE),
    # Secciones (emblemas de los encabezados)
    "chat": (_emb_chat, CIAN),
    "usuarios": (_emb_dual, AZUL),
    "laboratorio": (_emb_laboratorio, ROJO),
    "analisis": (_emb_analisis, AZUL),
    "teoria": (_emb_teoria, VIOLETA),
    "historial": (_emb_historial, CIAN),
}


def tiene_ilustracion(clave: str) -> bool:
    return clave in DIBUJOS


def pintar_ilustracion(p: QPainter, rect: QRectF, clave: str, halo: bool = True) -> None:
    """Dibuja la ilustración `clave` centrada en `rect` (conserva la proporción 200 × 120)."""
    dibujo, color = DIBUJOS[clave]
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    escala = min(rect.width() / ANCHO, rect.height() / ALTO)
    if halo:
        grad = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.55)
        grad.setColorAt(0, qcolor(color, 38))
        grad.setColorAt(1, qcolor(color, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(rect.center(), rect.width() * 0.5, rect.height() * 0.6)
    p.translate(rect.center().x() - ANCHO * escala / 2, rect.center().y() - ALTO * escala / 2)
    p.scale(escala, escala)
    dibujo(p)
    p.restore()


class Ilustracion(QWidget):
    """Widget que muestra una ilustración conceptual escalable."""

    def __init__(self, clave: str, alto: int = 110, ancho_min: int = 150, halo: bool = True, parent=None):
        super().__init__(parent)
        self.clave, self._halo = clave, halo
        self.setMinimumSize(ancho_min, alto)
        self.setFixedHeight(alto)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event):
        p = QPainter(self)
        pintar_ilustracion(p, QRectF(self.rect()).adjusted(4, 4, -4, -4), self.clave, self._halo)
        p.end()


class Emblema(Ilustracion):
    """Ilustración compacta de tamaño fijo para los encabezados de sección."""

    def __init__(self, clave: str, ancho: int = 106, alto: int = 64, parent=None):
        super().__init__(clave, alto, ancho, halo=True, parent=parent)
        self.setFixedSize(ancho, alto)
