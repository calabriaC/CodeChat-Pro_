"""Barra lateral: logotipo, navegación e indicador de estado del sistema."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from interfaz import servicio
from interfaz.componentes import BotonNavegacion, Logo, etiqueta, formato_p, pintar_logo
from interfaz.estilos import ANCHO_BARRA_LATERAL, C, qcolor, rgba


INTEGRANTES = [
    "Alberto Aponte",
    "Ethan Barreneche",
    "Carlos Calabria",
    "Angel Fontalvo",
]

SECCIONES = [
    ("Chat", "chat"),
    ("Laboratorio BSC", "laboratorio"),
    ("Análisis", "analisis"),
    ("Teoría", "teoria"),
    ("Historial", "historial"),
]


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


class _ViñetaLogo(QWidget):
    """Viñeta con el cubo del logotipo de CodeChat Pro."""

    def __init__(self, lado: int = 20, parent=None):
        super().__init__(parent)
        self.setFixedSize(lado, lado)

    def paintEvent(self, _event):
        p = QPainter(self)
        pintar_logo(p, QRectF(self.rect()))
        p.end()


class TarjetaIntegrantes(QFrame):
    """Tarjeta del equipo: cabecera con contador y un nombre por fila con el logotipo como viñeta."""

    def __init__(self, nombres: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("TarjetaIntegrantes")
        self.setStyleSheet(f"""
            QFrame#TarjetaIntegrantes {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {rgba(C.PANEL, 0.88)}, stop:1 {rgba(C.FONDO_LATERAL, 0.80)});
                border: 1px solid {C.BORDE};
                border-top: 2px solid {rgba(C.ROJO, 0.75)};
                border-radius: 14px;
            }}
            QFrame#FilaIntegrante {{ background: transparent; border: none;
                                     border-top: 1px solid {C.BORDE_SUAVE}; border-radius: 0; }}""")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(14, 12, 14, 8)
        caja.setSpacing(0)

        cab = QHBoxLayout()
        cab.setSpacing(8)
        titulo = etiqueta("INTEGRANTES", "Seccion")
        titulo.setStyleSheet(f"color: {C.TEXTO_SECUNDARIO};")
        cab.addWidget(titulo)
        cab.addStretch(1)
        contador = QLabel(str(len(nombres)))
        contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contador.setFixedSize(24, 20)
        contador.setStyleSheet(f"background: {rgba(C.ROJO, 0.16)}; color: {C.ROJO_CLARO};"
                               f" border: 1px solid {rgba(C.ROJO, 0.40)}; border-radius: 10px;"
                               " font-size: 11px; font-weight: 700;")
        cab.addWidget(contador)
        caja.addLayout(cab)
        caja.addSpacing(8)

        for i, nombre in enumerate(nombres):
            fila = QFrame()
            fila.setObjectName("FilaIntegrante" if i else "")
            f = QHBoxLayout(fila)
            f.setContentsMargins(2, 7, 2, 7)
            f.setSpacing(11)
            f.addWidget(_ViñetaLogo(20), 0, Qt.AlignmentFlag.AlignVCenter)
            lbl = etiqueta(nombre, "Etiqueta", ajustar=True)
            lbl.setStyleSheet(f"color: {C.TEXTO}; font-size: 14px; font-weight: 500;")
            f.addWidget(lbl, 1)
            caja.addWidget(fila)


class TarjetaCodigoActual(QFrame):
    """Indicador inferior «Sistema listo» con los parámetros activos del canal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EstadoSistema")
        self.setStyleSheet(f"QFrame#EstadoSistema {{ background: transparent; border: none;"
                           f" border-top: 1px solid {C.BORDE_SUAVE}; }}")
        fila = QHBoxLayout(self)
        fila.setContentsMargins(8, 16, 4, 4)
        fila.setSpacing(12)
        fila.addWidget(_PuntoEstado(), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        titulo = etiqueta("Sistema listo", "Etiqueta")
        titulo.setStyleSheet("font-size: 15px; font-weight: 600;")
        col.addWidget(titulo)
        self._valores = QLabel()
        self._valores.setTextFormat(Qt.TextFormat.RichText)
        self._valores.setWordWrap(True)
        self._valores.setObjectName("EtiquetaSecundaria")
        col.addWidget(self._valores)
        fila.addLayout(col, 1)

    def actualizar(self, n: int, p: float | None = None) -> None:
        par = servicio.parametros(n)
        detalle = (f"BSC activo &nbsp;·&nbsp; n = {par['n']}, t = {par['errores_corregibles']}, "
                   f"R = {par['tasa']:.2f}")
        if p is not None:
            detalle += f" &nbsp;·&nbsp; p = {formato_p(p)}"
        self._valores.setText(f"<span style='color:{C.TEXTO_SECUNDARIO};'>{detalle}</span>")


class BarraLateral(QFrame):
    seccion_elegida = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(ANCHO_BARRA_LATERAL)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 24, 16, 18)
        caja.setSpacing(6)

        # ---- Marca ---------------------------------------------------------
        marca = QHBoxLayout()
        marca.setSpacing(12)
        self._logo = Logo(70, 70)
        marca.addWidget(self._logo, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        nombre = QLabel(f"CodeChat <span style='color:{C.ROJO};'>Pro</span>")
        nombre.setTextFormat(Qt.TextFormat.RichText)
        nombre.setStyleSheet("font-size: 25px; font-weight: 800; letter-spacing: -0.4px;")
        textos.addWidget(nombre)
        sub = QLabel("Mensajería con<br>Teoría de Códigos")
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"font-size: 15px; color: {C.TEXTO_SECUNDARIO};")
        textos.addWidget(sub)
        textos.addStretch(1)
        marca.addLayout(textos, 1)
        caja.addLayout(marca)
        caja.addSpacing(26)

        # ---- Navegación ----------------------------------------------------
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self.botones: list[BotonNavegacion] = []
        for i, (texto, nombre_icono) in enumerate(SECCIONES):
            b = BotonNavegacion(texto, nombre_icono)
            b.setToolTip(f"{texto}  (Ctrl+{i + 1})")
            self._grupo.addButton(b, i)
            self.botones.append(b)
            caja.addWidget(b)
            caja.addSpacing(2)
        self.botones[0].setChecked(True)
        self._grupo.idClicked.connect(self.seccion_elegida.emit)

        caja.addStretch(1)
        if INTEGRANTES:
            caja.addWidget(TarjetaIntegrantes(INTEGRANTES))
            # Espacio flexible: la tarjeta queda centrada entre el menú y «Sistema listo».
            caja.addStretch(1)
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
        fondo.setColorAt(1, qcolor("#0B0F1A"))
        p.fillRect(r, fondo)

        # Halo suave detrás del logotipo
        centro = QPointF(self._logo.geometry().center())
        halo = QRadialGradient(centro, 110)
        halo.setColorAt(0, qcolor(C.ROJO, 40))
        halo.setColorAt(0.55, qcolor(C.ROJO, 10))
        halo.setColorAt(1, qcolor(C.ROJO, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(centro, 110, 110)

        # Ondas decorativas en la parte inferior (señal transmitida)
        base_y = r.height() * 0.78
        for k in range(16):
            ruta = QPainterPath()
            fase = k * 0.16
            amplitud = 24 + k * 2.4
            for i in range(0, int(r.width()) + 8, 6):
                x = float(i)
                y = base_y - x * 0.22 + math.sin(x / 52 + fase) * amplitud * (0.35 + x / r.width())
                if i == 0:
                    ruta.moveTo(QPointF(x, y))
                else:
                    ruta.lineTo(QPointF(x, y))
            p.setPen(QPen(qcolor(C.ROJO, 12 + k * 3), 1.1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(ruta)

        p.setPen(QPen(qcolor(C.BORDE_SUAVE), 1))
        p.drawLine(QPointF(r.right() - 0.5, 0), QPointF(r.right() - 0.5, r.bottom()))
        p.end()
