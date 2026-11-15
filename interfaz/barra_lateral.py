"""Barra lateral: logotipo, navegación y tarjeta del código actual."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from interfaz import servicio
from interfaz.componentes import BotonNavegacion, Logo, etiqueta, formato_p, icono_label, separador
from interfaz.estilos import ANCHO_BARRA_LATERAL, C, qcolor, rgba

SECCIONES = [
    ("Chat", "chat"),
    ("Laboratorio BSC", "laboratorio"),
    ("Análisis", "analisis"),
    ("Teoría", "teoria"),
    ("Historial", "historial"),
]


class TarjetaCodigoActual(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TarjetaCodigo")
        self.setStyleSheet(f"""
            QFrame#TarjetaCodigo {{
                background: {rgba(C.PANEL, 0.92)};
                border: 1px solid {C.BORDE};
                border-radius: 14px;
            }}""")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 16, 18, 16)
        caja.setSpacing(10)
        caja.addWidget(etiqueta("Código actual", "TituloTarjeta"))
        caja.addWidget(separador())

        fila = QHBoxLayout()
        fila.setSpacing(12)
        fila.addWidget(icono_label("capas", C.ROJO, 26), 0, Qt.AlignmentFlag.AlignTop)
        datos = QVBoxLayout()
        datos.setSpacing(4)
        datos.addWidget(etiqueta("Código de repetición", "EtiquetaSecundaria"))
        self._valores = QLabel()
        self._valores.setTextFormat(Qt.TextFormat.RichText)
        self._valores.setObjectName("Mono")
        datos.addWidget(self._valores)
        fila.addLayout(datos, 1)
        caja.addLayout(fila)

    def actualizar(self, n: int, p: float | None = None) -> None:
        par = servicio.parametros(n)
        filas = [("n", str(par["n"])), ("d<sub>min</sub>", str(par["distancia_minima"])),
                 ("t", str(par["errores_corregibles"])), ("R", f"{par['tasa']:.2f}")]
        if p is not None:
            filas.append(("p", formato_p(p)))
        self._valores.setText(
            "<table cellspacing='0' cellpadding='1'>" + "".join(
                f"<tr><td style='color:{C.TEXTO_SECUNDARIO}; padding-right:10px;'>{k}</td>"
                f"<td>=&nbsp;&nbsp;<b>{v}</b></td></tr>" for k, v in filas) + "</table>")


class BarraLateral(QFrame):
    seccion_elegida = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(ANCHO_BARRA_LATERAL)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 26, 18, 20)
        caja.setSpacing(6)

        caja.addWidget(Logo(), 0, Qt.AlignmentFlag.AlignHCenter)
        marca = QLabel(f"CodeChat <span style='color:{C.ROJO};'>Pro</span>")
        marca.setTextFormat(Qt.TextFormat.RichText)
        marca.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marca.setStyleSheet("font-size: 27px; font-weight: 800;")
        caja.addWidget(marca)
        sub = etiqueta("Mensajería con Teoría de Códigos", "EtiquetaSecundaria")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caja.addWidget(sub)
        caja.addSpacing(18)
        caja.addWidget(separador())
        caja.addSpacing(12)
        seccion = etiqueta("NAVEGACIÓN", "Seccion")
        seccion.setContentsMargins(10, 0, 0, 4)
        caja.addWidget(seccion)

        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self.botones: list[BotonNavegacion] = []
        for i, (texto, nombre_icono) in enumerate(SECCIONES):
            b = BotonNavegacion(texto, nombre_icono)
            b.setToolTip(f"{texto}  (Ctrl+{i + 1})")
            self._grupo.addButton(b, i)
            self.botones.append(b)
            caja.addWidget(b)
        self.botones[0].setChecked(True)
        self._grupo.idClicked.connect(self.seccion_elegida.emit)

        caja.addStretch(1)
        seccion_cfg = etiqueta("CONFIGURACIÓN ACTIVA", "Seccion")
        seccion_cfg.setContentsMargins(10, 0, 0, 4)
        caja.addWidget(seccion_cfg)
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
        fondo.setColorAt(1, qcolor("#0A0B12"))
        p.fillRect(r, fondo)

        # Ondas decorativas discretas (señal transmitida)
        base_y = r.height() * 0.66
        for k in range(14):
            ruta = QPainterPath()
            fase = k * 0.18
            amplitud = 26 + k * 2.2
            for i in range(0, int(r.width()) + 8, 6):
                x = float(i)
                y = base_y - x * 0.20 + math.sin(x / 48 + fase) * amplitud * (0.4 + x / r.width())
                if i == 0:
                    ruta.moveTo(QPointF(x, y))
                else:
                    ruta.lineTo(QPointF(x, y))
            p.setPen(QPen(qcolor(C.ROJO, 14 + k * 3), 1.1))
            p.drawPath(ruta)

        p.setPen(QPen(qcolor(C.BORDE_SUAVE), 1))
        p.drawLine(QPointF(r.right() - 0.5, 0), QPointF(r.right() - 0.5, r.bottom()))
        p.end()
