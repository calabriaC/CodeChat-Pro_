"""Aplica el diseño de `interfaz/marcos.py` a toda la aplicación con tres niveles.

  · Nivel 1 — marcos principales (encabezados, paneles grandes, Monitor del Canal):
    el estilo por defecto de `marcos.pintar_marco` (esquinas recortadas, acentos cian/rojo).
    Lo dibujan las propias clases (`Tarjeta`, `EncabezadoPagina`, `PanelTecnico`).
  · Nivel 2 — paneles secundarios (tarjetas, métricas, secciones, burbujas, filas):
    estilo «minimal» de `marcos.py` (ligeramente redondeado, borde fino) con un acento
    de color pequeño y sin resplandor. Se aplica aquí, por objectName.
  · Nivel 3 — controles pequeños (campos, botones, chips, selectores): conservan su
    borde sencillo redondeado de la hoja de estilos; este módulo no los toca.

Funcionamiento: el estilo de la aplicación (`EstiloMarcos`) recibe cada widget cuando
Qt lo prepara («polish»); si su objectName es de nivel 2, se instala un filtro que
pinta el marco antes que el widget y se anula su fondo/borde de QSS.

Un widget puede declarar su color propio con `widget.setProperty("acento", "#RRGGBB")`.
Solo presentación: no contiene lógica matemática.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QProxyStyle, QWidget

from interfaz import marcos
from interfaz.estilos import C, qcolor

MARCA = "/* marco-signal-lab */"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def mezclar(color: str, fondo: str, t: float) -> str:
    """Color hexadecimal opaco: `t` de `color` sobre `fondo` (0 = fondo, 1 = color)."""
    a, b = QColor(color), QColor(fondo)
    return QColor(round(b.red() + (a.red() - b.red()) * t),
                  round(b.green() + (a.green() - b.green()) * t),
                  round(b.blue() + (a.blue() - b.blue()) * t)).name()


def _acento(w: QWidget, defecto: str | None = None) -> str | None:
    valor = w.property("acento")
    return str(valor) if valor else defecto


def pintar_nivel2(p: QPainter, r: QRectF, relleno: str = C.PANEL, borde: str = C.BORDE,
                  acento: str | None = None, acento_fin: str | None = None, realce: float = 0.0) -> None:
    """Tarjeta «Signal Lab premium»: esquinas redondeadas, degradado oscuro, borde fino que
    se ilumina en azul hacia abajo y un brillo inferior suave. `realce` (0–1) intensifica el
    borde, p. ej. al pasar el cursor."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    radio = max(4.0, min(12.0, r.height() / 4, r.width() / 6))
    ruta = QPainterPath()
    ruta.addRoundedRect(r, radio, radio)
    base = QColor(relleno)
    fondo = QLinearGradient(r.topLeft(), r.bottomLeft())
    fondo.setColorAt(0, base.lighter(118))
    fondo.setColorAt(0.45, base)
    fondo.setColorAt(1, base.darker(122))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fondo)
    p.drawPath(ruta)
    filo = QLinearGradient(r.topLeft(), r.bottomLeft())
    filo.setColorAt(0, qcolor(borde, 230))
    filo.setColorAt(0.55, qcolor(borde, 230))
    filo.setColorAt(1, qcolor(C.AZUL_ELECTRICO, int(120 + 110 * realce)))
    p.setPen(QPen(QBrush(filo), 1.1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(ruta)
    if r.height() > 44 and r.width() > 90:
        brillo = QLinearGradient(QPointF(r.left(), 0), QPointF(r.right(), 0))
        brillo.setColorAt(0, qcolor(C.AZUL_ELECTRICO, 0))
        brillo.setColorAt(0.5, qcolor(C.AZUL_ELECTRICO, int(55 + 80 * realce)))
        brillo.setColorAt(1, qcolor(C.AZUL_ELECTRICO, 0))
        p.setPen(QPen(QBrush(brillo), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(r.left() + radio, r.bottom() - 0.5), QPointF(r.right() - radio, r.bottom() - 0.5))
    largo = min(30.0, r.width() / 4)
    if acento:
        p.setPen(QPen(qcolor(acento, 230), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(r.left() + 10, r.top() + 0.5), QPointF(r.left() + 10 + largo, r.top() + 0.5))
    if acento_fin:
        p.setPen(QPen(qcolor(acento_fin, 200), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(r.right() - 10 - largo, r.bottom() - 0.5), QPointF(r.right() - 10, r.bottom() - 0.5))


class PanelSecundario(marcos.PanelTecnico):
    """PanelTecnico de nivel 2 (misma interfaz: relleno, borde, acento_a, acento_b…)."""

    def paintEvent(self, _event):
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        pintar_nivel2(p, r, self.relleno, self.borde, self.acento_a, self.acento_b)
        p.end()


# ---------------------------------------------------------------------------
# Nivel 2 por objectName: (relleno, borde, acento, acento_fin)
# ---------------------------------------------------------------------------
def _n2(relleno: str, borde: str = C.BORDE_SUAVE, acento: str | None = None,
        acento_fin: str | None = None) -> dict:
    return dict(relleno=relleno, borde=borde, acento=acento, acento_fin=acento_fin)


def _tintado(w: QWidget) -> dict:
    color = _acento(w, C.AZUL)
    return _n2(mezclar(color, C.PANEL, 0.09), mezclar(color, C.PANEL, 0.38), color)


def _barra_entrada(w: QWidget) -> dict:
    color = _acento(w, C.ROJO)
    if w.property("alerta"):
        borde = C.AMBAR if w.property("acento") else C.ERROR
    else:
        borde = mezclar(color, C.PANEL, 0.70 if w.property("foco") else 0.42)
    return _n2(C.PANEL, borde, color)


def _burbuja_dual(w: QWidget) -> dict:
    color = _acento(w, C.AZUL)
    if w.property("propio"):
        return _n2(mezclar(color, "#0A1A33", 0.55), mezclar(color, C.PANEL, 0.75))
    return _n2(C.SUPERFICIE, mezclar(color, C.SUPERFICIE, 0.45), color)


POR_NOMBRE = {
    # Tarjetas de información y secciones internas
    "Tarjeta": lambda w: _n2(C.PANEL, C.BORDE, _acento(w, C.ROJO)),
    "TarjetaTransmision": lambda w: _n2("#0F1E36", mezclar(C.AZUL_ELECTRICO, C.PANEL, 0.45), C.AZUL),
    "TarjetaInterna": lambda w: _n2(C.CAMPO_OSCURO, C.BORDE_SUAVE, _acento(w)),
    "SubTarjeta": lambda w: _n2(C.SUPERFICIE, C.BORDE_SUAVE, _acento(w)),
    "TarjetaMetrica": lambda w: _n2(C.SUPERFICIE, C.BORDE_SUAVE, _acento(w, C.ROJO)),
    "MiniDato": lambda w: _n2(C.CAMPO_OSCURO, C.BORDE_SUAVE),
    "PanelEtapas": lambda w: _n2(C.CAMPO_OSCURO, C.BORDE),
    "PanelEstado": lambda w: _n2(C.CAMPO_OSCURO, C.BORDE),
    "FilaDato": lambda w: _n2(C.CAMPO, C.BORDE_SUAVE),
    # Avisos con color propio
    "AvisoTransmision": _tintado,
    "Banner": _tintado,
    "EtapaResaltada": lambda w: _n2(mezclar(C.ROJO, C.CAMPO_OSCURO, 0.08),
                                   mezclar(C.ROJO, C.CAMPO_OSCURO, 0.30), C.ROJO),
    # Conversación
    "BarraEntrada": _barra_entrada,
    "BurbujaEnviada": lambda w: _n2("#1452B0", mezclar(C.AZUL, "#1452B0", 0.80)),
    "BurbujaRecibida": lambda w: _n2("#0F1D33", mezclar(C.ROJO, "#0F1D33", 0.55), C.ROJO),
    "BurbujaSistema": lambda w: _n2(mezclar(C.ROJO, C.PANEL, 0.10), mezclar(C.ROJO, C.PANEL, 0.35), C.ROJO),
    "BurbujaDual": _burbuja_dual,
    # Historial
    "FilaHistorial": lambda w: _n2(C.PANEL, mezclar(C.AZUL, C.PANEL, 0.55) if w.underMouse()
                                   else C.BORDE_SUAVE, _acento(w, C.AZUL)),
}


# ---------------------------------------------------------------------------
# Instalación
# ---------------------------------------------------------------------------
_REPINTAR = (QEvent.Type.Enter, QEvent.Type.Leave, QEvent.Type.FocusIn, QEvent.Type.FocusOut,
             QEvent.Type.EnabledChange)


class _PintorMarco(QObject):
    """Filtro de eventos que pinta el marco antes que el propio widget."""

    def __init__(self, widget: QWidget, fabrica):
        super().__init__(widget)
        self._fabrica = fabrica

    def eventFilter(self, obj, evento):
        tipo = evento.type()
        if tipo == QEvent.Type.Paint:
            p = QPainter(obj)
            pintar_nivel2(p, QRectF(obj.rect()).adjusted(1.0, 1.0, -1.0, -1.0), **self._fabrica(obj))
            p.end()
        elif tipo in _REPINTAR:
            obj.update()
        return False


def _pinta_por_su_cuenta(widget: QWidget) -> bool:
    """True si la clase (de la interfaz) ya implementa su propio paintEvent."""
    for cls in type(widget).__mro__:
        if cls.__module__.startswith("interfaz") and "paintEvent" in cls.__dict__:
            return True
    return False


def _anular_qss(widget: QWidget) -> None:
    """Quita el fondo y el borde del QSS (se conservan el texto, los colores y los márgenes)."""
    clase = next(c.__name__ for c in type(widget).__mro__ if c.__module__.startswith("PySide6"))
    nombre = widget.objectName()
    base = (f"{clase}#{nombre}", f"#{nombre}")
    estados = ("", ":hover", '[alerta="true"]', '[foco="true"]')
    selectores = ", ".join(b + e for b in base for e in estados)
    regla = f"\n{MARCA}\n{selectores} {{ background: transparent; border: none; }}"
    widget.setStyleSheet(widget.styleSheet().split(f"\n{MARCA}")[0] + regla)


def instalar_marco(widget: QWidget) -> None:
    fabrica = POR_NOMBRE.get(widget.objectName())
    if fabrica is None or _pinta_por_su_cuenta(widget):
        return
    if not widget.property("_marco_instalado"):
        widget.setProperty("_marco_instalado", True)
        widget.installEventFilter(_PintorMarco(widget, fabrica))
    # Se (re)aplica también si el código cambia el QSS del widget más tarde.
    if MARCA not in widget.styleSheet():
        _anular_qss(widget)


class EstiloMarcos(QProxyStyle):
    """Estilo de la aplicación: instala los marcos de nivel 2 en cada widget reconocido."""

    def polish(self, *args):
        resultado = super().polish(*args)
        objetivo = args[0] if args else None
        if isinstance(objetivo, QWidget):
            instalar_marco(objetivo)
        return resultado
