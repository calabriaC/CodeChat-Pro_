"""Ventana principal de CodeChat Pro."""

from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from interfaz.barra_lateral import BarraLateral
from interfaz.componentes import pixmap_logo
from interfaz.estado import EstadoApp
from interfaz.estilos import fuente, hoja_estilos
from interfaz.vista_analisis import VistaAnalisis
from interfaz.vista_chat import VistaChat
from interfaz.vista_historial import VistaHistorial
from interfaz.vista_laboratorio import VistaLaboratorio
from interfaz.vista_teoria import VistaTeoria


class VentanaPrincipal(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CodeChat Pro")
        self.setWindowIcon(QIcon(pixmap_logo(64)))
        self.resize(1440, 850)
        self.setMinimumSize(1180, 720)

        self.estado = EstadoApp(self)

        raiz = QWidget()
        raiz.setObjectName("Raiz")
        fila = QHBoxLayout(raiz)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)

        self.barra = BarraLateral()
        fila.addWidget(self.barra)

        self.paginas = QStackedWidget()
        self.vista_chat = VistaChat(self.estado)
        self.vista_laboratorio = VistaLaboratorio(self.estado)
        self.vista_analisis = VistaAnalisis(self.estado)
        self.vista_teoria = VistaTeoria(self.estado)
        self.vista_historial = VistaHistorial(self.estado)
        for vista in (self.vista_chat, self.vista_laboratorio, self.vista_analisis,
                      self.vista_teoria, self.vista_historial):
            vista.setObjectName("Pagina")
            self.paginas.addWidget(vista)
        fila.addWidget(self.paginas, 1)
        self.setCentralWidget(raiz)

        # Señales
        self.barra.seccion_elegida.connect(self.ir_a)
        self.estado.configuracion_cambiada.connect(lambda n, _p: self.barra.tarjeta_codigo.actualizar(n))
        self.estado.transmision_registrada.connect(lambda _r: self._actualizar_insignia())
        self.estado.historial_limpiado.connect(self._actualizar_insignia)
        self.barra.tarjeta_codigo.actualizar(self.estado.n)

        # Atajos Ctrl+1 … Ctrl+5
        for i in range(self.paginas.count()):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.ir_a(i))

    def ir_a(self, indice: int) -> None:
        self.paginas.setCurrentIndex(indice)
        self.barra.seleccionar(indice)
        if indice == 0:
            self.vista_chat.entrada.setFocus()

    def _actualizar_insignia(self) -> None:
        self.barra.botones[4].set_insignia(len(self.estado.historial))


def configurar_aplicacion(app: QApplication) -> None:
    """Aplica estilo base, tipografía y hoja de estilos global."""
    app.setStyle("Fusion")
    app.setFont(fuente(10))
    app.setStyleSheet(hoja_estilos())
    app.setApplicationName("CodeChat Pro")
