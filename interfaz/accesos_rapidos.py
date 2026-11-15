"""Fila superior de accesos rápidos a las secciones (solo presentación + navegación)."""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from interfaz.componentes import ESTADOS_TRANSMISION, EtiquetaRecortada, etiqueta, icono_label
from interfaz.estado import EstadoApp
from interfaz.estilos import C, qcolor


class _MiniSenal(QWidget):
    """Ilustración: señal en zigzag con nodos (canal con errores)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        ys = (0.65, 0.35, 0.55, 0.25, 0.6, 0.3, 0.5, 0.35, 0.6)
        pts = [QPointF(w * (0.12 + 0.76 * i / (len(ys) - 1)), h * y) for i, y in enumerate(ys)]
        p.setPen(QPen(qcolor(C.ROJO, 200), 1.6))
        for a, b in zip(pts, pts[1:]):
            p.drawLine(a, b)
        p.setPen(Qt.PenStyle.NoPen)
        for i, q in enumerate(pts):
            if i % 2 == 0:
                p.setBrush(QColor(C.ROJO))
                p.drawEllipse(q, 3, 3)
        p.end()


class _MiniBarras(QWidget):
    """Ilustración: barras crecientes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        alturas = (0.18, 0.28, 0.36, 0.45, 0.55, 0.68, 0.82, 1.0)
        ancho = 11
        inicio = w - 34 - len(alturas) * (ancho + 4)
        for i, a in enumerate(alturas):
            ultimo = i == len(alturas) - 1
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor(C.ROJO if ultimo else "#5B6B8C", 230 if ultimo else 150))
            p.drawRect(QRectF(inicio + i * (ancho + 4), h * (1 - a), ancho, h * a))
        p.end()


class AccesoRapido(QFrame):
    clic = Signal()

    def __init__(self, nombre_icono: str, color_icono: str, titulo: str, contenido: QWidget,
                 subtitulo: str | None, parent=None):
        super().__init__(parent)
        self.setObjectName("AccesoRapido")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(108)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 12, 18, 10)
        caja.setSpacing(4)
        cab = QHBoxLayout()
        cab.setSpacing(12)
        cab.addWidget(icono_label(nombre_icono, color_icono, 26))
        t = etiqueta(titulo, "TituloTarjeta")
        t.setStyleSheet("font-size: 17px; font-weight: 650;")
        cab.addWidget(t)
        cab.addStretch(1)
        caja.addLayout(cab)
        caja.addWidget(contenido, 1)
        self._contenido = contenido
        self._sub = None
        if subtitulo:
            self._sub = etiqueta(subtitulo, "EtiquetaSecundaria")
            self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caja.addWidget(self._sub)

    def set_compacto(self, compacto: bool) -> None:
        """Versión reducida (icono + título) para ventanas de poca altura."""
        self._contenido.setVisible(not compacto)
        if self._sub is not None:
            self._sub.setVisible(not compacto)
        self.setFixedHeight(58 if compacto else 108)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clic.emit()
        super().mousePressEvent(event)


class _VistaPreviaHistorial(QWidget):
    """Últimas transmisiones guardadas (datos reales) o un estado vacío."""

    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        self._caja = QVBoxLayout(self)
        self._caja.setContentsMargins(4, 0, 0, 0)
        self._caja.setSpacing(3)
        estado.transmision_registrada.connect(lambda _r: self.refrescar())
        estado.historial_limpiado.connect(self.refrescar)
        self.refrescar()

    def refrescar(self) -> None:
        while self._caja.count():
            item = self._caja.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        registros = self.estado.historial
        if not registros:
            vacio = etiqueta("Aún no hay transmisiones guardadas", "EtiquetaTenue")
            self._caja.addWidget(vacio)
            self._caja.addStretch(1)
            return
        for r in list(reversed(registros))[:2]:
            fila = QHBoxLayout()
            fila.setSpacing(8)
            color = ESTADOS_TRANSMISION[r.estado][3]
            punto = QLabel("●")
            punto.setStyleSheet(f"color: {color}; font-size: 11px;")
            fila.addWidget(punto)
            if r.texto is not None:
                plano = " ".join(r.texto.split())
                resumen = f"“{plano if len(plano) <= 24 else plano[:23] + '…'}”"
            else:
                resumen = f"Secuencia de {len(r.bits_originales)} bits"
            resumen += f" (p = {r.p:.2f})" if r.origen == "laboratorio" else ""
            texto = EtiquetaRecortada(resumen, "EtiquetaSecundaria")
            texto.setStyleSheet(f"color: {C.TEXTO}; font-size: 13px;")
            fila.addWidget(texto, 1)
            hora = etiqueta(r.fecha.strftime("%H:%M"), "Mono")
            hora.setStyleSheet(f"color: {C.TEXTO_SECUNDARIO}; font-size: 12px;")
            fila.addWidget(hora)
            contenedor = QWidget()
            contenedor.setLayout(fila)
            fila.setContentsMargins(0, 0, 0, 0)
            self._caja.addWidget(contenedor)
        if len(registros) > 2:
            mas = etiqueta(f"… y {len(registros) - 2} más", "EtiquetaTenue")
            self._caja.addWidget(mas)
        self._caja.addStretch(1)


class FilaAccesos(QWidget):
    """Cuatro tarjetas que llevan a Laboratorio, Análisis, Teoría e Historial."""

    seccion_elegida = Signal(int)

    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 14, 16, 0)
        fila.setSpacing(16)

        formula = QLabel("<i>C</i> = 1 − <i>H</i><sub>2</sub>(<i>p</i>)")
        formula.setTextFormat(Qt.TextFormat.RichText)
        formula.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formula.setStyleSheet("font-size: 19px; font-family: 'Cambria Math', 'Cambria', serif;")

        tarjetas = [
            (1, AccesoRapido("laboratorio", C.ROJO, "Laboratorio BSC", _MiniSenal(),
                             "Simula el canal con errores")),
            (2, AccesoRapido("analisis", C.AZUL, "Análisis", _MiniBarras(),
                             "Métricas y rendimiento (BER, R, C)")),
            (3, AccesoRapido("teoria", C.TEXTO, "Teoría", formula,
                             "Conceptos, definiciones y teoremas")),
            (4, AccesoRapido("historial", C.ROJO, "Historial", _VistaPreviaHistorial(estado), None)),
        ]
        self._tarjetas = [t for _i, t in tarjetas]
        for indice, tarjeta in tarjetas:
            tarjeta.clic.connect(lambda i=indice: self.seccion_elegida.emit(i))
            tarjeta.setToolTip(f"Ir a la sección (Ctrl+{indice + 1})")
            fila.addWidget(tarjeta, 1)

    def set_compacto(self, compacto: bool) -> None:
        for tarjeta in self._tarjetas:
            tarjeta.set_compacto(compacto)
