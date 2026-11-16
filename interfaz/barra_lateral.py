"""Barra lateral «Signal Lab»: logotipo, navegación, integrantes y estado del sistema."""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from interfaz import servicio
from interfaz.componentes import BotonNavegacion, Logo, etiqueta, formato_p, icono_label
from interfaz.estilos import ANCHO_BARRA_LATERAL, C, qcolor, rgba
from interfaz.marcos import TrazosDiagonales, pintar_ondas
from interfaz.marcos_globales import PanelSecundario


# ---------------------------------------------------------------------------
# INTEGRANTES DEL EQUIPO
# Escribe aquí los nombres, uno por línea, entre comillas y con una coma al final.
# ---------------------------------------------------------------------------
INTEGRANTES = [
    "Alberto Aponte",
    "Ethan Barreneche",
    "Carlos Calabria",
    "Angel Fontalvo",
]

SECCIONES = [
    ("Chat", "chat"),
    ("Chat Dual", "usuarios"),
    ("Laboratorio BSC", "laboratorio"),
    ("Análisis", "analisis"),
    ("Teoría", "teoria"),
    ("Historial", "historial"),
]


class _SeparadorLuminoso(QWidget):
    """Línea roja con brillo que se desvanece hacia la derecha."""

    def __init__(self, color: str = C.ROJO, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(6)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.height() / 2
        for ancho, alfa in ((5, 30), (2.5, 80), (1.4, 255)):
            grad = QLinearGradient(QPointF(0, y), QPointF(self.width(), y))
            grad.setColorAt(0, qcolor(self._color, 0))
            grad.setColorAt(0.25, qcolor(self._color, alfa))
            grad.setColorAt(0.85, qcolor(self._color, alfa))
            grad.setColorAt(1, qcolor(self._color, 0))
            p.setPen(QPen(grad, ancho))
            p.drawLine(QPointF(8, y), QPointF(self.width() - 8, y))
        p.end()


class _PuntoEstado(QWidget):
    """Punto verde con halo que indica que el sistema está listo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(8, 8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor(C.VERDE, 50))
        p.drawEllipse(c, 7.5, 7.5)
        p.setBrush(qcolor(C.VERDE))
        p.drawEllipse(c, 4.5, 4.5)
        p.end()


class TarjetaIntegrantes(QFrame):
    """Sección discreta con los integrantes del equipo."""

    def __init__(self, nombres: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("SeccionIntegrantes")
        self.setStyleSheet(f"""
            QFrame#SeccionIntegrantes {{ background: transparent; border: none; }}
            QFrame#FilaIntegrante {{ background: transparent; border: none;
                                     border-bottom: 1px solid {C.BORDE_SUAVE}; }}""")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(6, 4, 6, 4)
        caja.setSpacing(0)
        cab = QHBoxLayout()
        cab.setSpacing(10)
        cab.addWidget(icono_label("usuarios", C.TEXTO_SECUNDARIO, 18))
        titulo = etiqueta("INTEGRANTES", "Seccion")
        titulo.setStyleSheet(f"color: {C.TEXTO_SECUNDARIO}; font-size: 12px;")
        cab.addWidget(titulo, 1)
        caja.addLayout(cab)
        caja.addSpacing(6)
        for nombre in nombres:
            fila = QFrame()
            fila.setObjectName("FilaIntegrante")
            f = QHBoxLayout(fila)
            f.setContentsMargins(4, 5, 4, 5)
            f.setSpacing(12)
            f.addWidget(icono_label("usuario", C.ROJO, 18))
            lbl = etiqueta(nombre, "Etiqueta", ajustar=True)
            lbl.setStyleSheet(f"color: {C.TEXTO}; font-size: 14px;")
            f.addWidget(lbl, 1)
            caja.addWidget(fila)


class TarjetaCodigoActual(PanelSecundario):
    """Indicador inferior «Sistema listo» con los parámetros activos del canal."""

    def __init__(self, parent=None):
        super().__init__(parent, relleno=C.PANEL, borde="#1D4F8E",
                         acento_a=None, acento_b=C.AZUL_ELECTRICO, chaflan=10, marca=False)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 14, 12, 14)
        fila.setSpacing(12)
        fila.addWidget(_PuntoEstado(), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        titulo = etiqueta("Sistema listo", "Etiqueta")
        titulo.setStyleSheet("font-size: 15px; font-weight: 700;")
        col.addWidget(titulo)
        self._valores = QLabel()
        self._valores.setTextFormat(Qt.TextFormat.RichText)
        self._valores.setWordWrap(True)
        self._valores.setObjectName("EtiquetaSecundaria")
        col.addWidget(self._valores)
        fila.addLayout(col, 1)

    def actualizar(self, n: int, p: float | None = None) -> None:
        par = servicio.parametros(n)
        separador = f"<span style='color:{C.TEXTO_TENUE};'>&nbsp;|&nbsp;</span>"
        linea1 = f"BSC activo{separador}n = {par['n']} · t = {par['errores_corregibles']}"
        linea2 = f"R = {par['tasa']:.2f}"
        if p is not None:
            linea2 += f"{separador}p = {formato_p(p)}"
        self._valores.setText(f"<span style='color:{C.TEXTO_SECUNDARIO};'>{linea1}<br>{linea2}</span>")


class BarraLateral(QFrame):
    seccion_elegida = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(ANCHO_BARRA_LATERAL)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 22, 16, 16)
        caja.setSpacing(6)

        # ---- Marca ---------------------------------------------------------
        marca = QHBoxLayout()
        marca.setSpacing(10)
        self._logo = Logo(64, 64)
        marca.addWidget(self._logo, 0, Qt.AlignmentFlag.AlignVCenter)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        nombre = QLabel(f"CodeChat <span style='color:{C.ROJO};'>Pro</span>")
        nombre.setTextFormat(Qt.TextFormat.RichText)
        nombre.setStyleSheet("font-size: 25px; font-weight: 800; letter-spacing: -0.4px;")
        textos.addWidget(nombre)
        fila_sub = QHBoxLayout()
        fila_sub.setSpacing(10)
        sub = QLabel("Signal Lab")
        sub.setStyleSheet(f"font-size: 18px; color: {C.TEXTO_SECUNDARIO}; font-weight: 500;")
        fila_sub.addWidget(sub)
        fila_sub.addWidget(TrazosDiagonales(4), 0, Qt.AlignmentFlag.AlignVCenter)
        fila_sub.addStretch(1)
        textos.addLayout(fila_sub)
        marca.addLayout(textos, 1)
        caja.addLayout(marca)
        caja.addSpacing(16)

        # ---- Navegación ----------------------------------------------------
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self.botones: list[BotonNavegacion] = []
        nav = QVBoxLayout()
        nav.setSpacing(4)
        for i, (texto, nombre_icono) in enumerate(SECCIONES):
            b = BotonNavegacion(texto, nombre_icono)
            b.setFixedHeight(46)   # seis secciones caben también en pantallas de 768 px
            b.setToolTip(f"{texto}  (Ctrl+{i + 1})")
            self._grupo.addButton(b, i)
            self.botones.append(b)
            nav.addWidget(b)
        caja.addLayout(nav)
        self.botones[0].setChecked(True)
        self._grupo.idClicked.connect(self.seccion_elegida.emit)

        caja.addSpacing(6)
        caja.addWidget(_SeparadorLuminoso())
        caja.addSpacing(6)

        # ---- Integrantes ---------------------------------------------------
        if INTEGRANTES:
            caja.addWidget(TarjetaIntegrantes(INTEGRANTES))
        caja.addStretch(1)

        # ---- Estado --------------------------------------------------------
        self.tarjeta_codigo = TarjetaCodigoActual()
        caja.addWidget(self.tarjeta_codigo)

    def seleccionar(self, indice: int) -> None:
        self.botones[indice].setChecked(True)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        fondo = QLinearGradient(r.topLeft(), r.bottomLeft())
        fondo.setColorAt(0, qcolor(C.FONDO_LATERAL))
        fondo.setColorAt(1, qcolor("#050913"))
        p.fillRect(r, fondo)

        # Halo detrás del logotipo
        centro = QPointF(self._logo.geometry().center())
        halo = QRadialGradient(centro, 100)
        halo.setColorAt(0, qcolor(C.ROJO, 36))
        halo.setColorAt(0.6, qcolor(C.AZUL_ELECTRICO, 10))
        halo.setColorAt(1, qcolor(C.AZUL_ELECTRICO, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(centro, 100, 100)

        # Ondas: rojo → azul en la parte superior derecha y en la inferior
        pintar_ondas(p, QRectF(r.left(), 0, r.width(), 160), 120, 10, C.ROJO, C.AZUL_ELECTRICO,
                     38, pendiente=-0.25)
        pintar_ondas(p, QRectF(r.left(), r.bottom() - 240, r.width(), 240), r.bottom() - 70, 16,
                     C.ROJO, C.AZUL_ELECTRICO, 60, pendiente=-0.22)

        p.setPen(QPen(qcolor(C.BORDE_SUAVE), 1))
        p.drawLine(QPointF(r.right() - 0.5, 0), QPointF(r.right() - 0.5, r.bottom()))
        p.end()
