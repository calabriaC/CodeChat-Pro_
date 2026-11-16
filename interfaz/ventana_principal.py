"""Ventana principal de CodeChat Pro."""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QStyleFactory, QVBoxLayout,
    QWidget,
)

from interfaz.barra_lateral import BarraLateral
from interfaz.componentes import pixmap_logo
from interfaz.estado import EstadoApp
from interfaz.marcos import FondoOndas
from interfaz.marcos_globales import EstiloMarcos
from interfaz import estilos
from interfaz.estilos import C, qcolor
from interfaz.vista_analisis import VistaAnalisis
from interfaz.vista_chat import VistaChat
from interfaz import servicio_dual
from interfaz.vista_chat_dual import VistaChatDual
from interfaz.vista_historial import VistaHistorial
from interfaz.vista_laboratorio import VistaLaboratorio
from interfaz.vista_teoria import VistaTeoria


class VentanaPrincipal(QMainWindow):
    def __init__(self, parent=None, almacen=None):
        super().__init__(parent)
        self.setWindowTitle("CodeChat Pro")
        self.setWindowIcon(QIcon(pixmap_logo(64)))
        self.resize(1440, 850)
        self.setMinimumSize(1240, 700)

        self.estado = EstadoApp(self, almacen=almacen)

        raiz = FondoOndas()
        raiz.setObjectName("Raiz")
        fila = QHBoxLayout(raiz)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)

        self.barra = BarraLateral()
        fila.addWidget(self.barra)

        self.paginas = QStackedWidget()
        self.vista_chat = VistaChat(self.estado)
        # Conversación del Chat Dual en su propio archivo, junto al historial (sin mezclarse con él).
        self.vista_chat_dual = VistaChatDual(
            ruta=self.estado.almacen.ruta.with_name(servicio_dual.NOMBRE_ARCHIVO))
        self.vista_laboratorio = VistaLaboratorio(self.estado)
        self.vista_analisis = VistaAnalisis(self.estado)
        self.vista_teoria = VistaTeoria(self.estado)
        self.vista_historial = VistaHistorial(self.estado)
        # El orden coincide con SECCIONES de la barra lateral.
        for vista in (self.vista_chat, self.vista_chat_dual, self.vista_laboratorio,
                      self.vista_analisis, self.vista_teoria, self.vista_historial):
            vista.setObjectName("Pagina")
            self.paginas.addWidget(vista)
        fila.addWidget(self.paginas, 1)
        self.setCentralWidget(raiz)

        # Señales
        self.barra.seccion_elegida.connect(self.ir_a)
        self.estado.configuracion_cambiada.connect(self.barra.tarjeta_codigo.actualizar)
        self.estado.transmision_registrada.connect(lambda _r: self._actualizar_insignia())
        self.estado.historial_limpiado.connect(self._actualizar_insignia)
        self.estado.aviso_persistencia.connect(self._avisar)
        self.barra.tarjeta_codigo.actualizar(self.estado.n, self.estado.p)
        self._actualizar_insignia()
        if self.estado.error_carga:
            # Se informa cuando la ventana ya es visible.
            QTimer.singleShot(300, lambda: self._avisar(self.estado.error_carga))

        # Atajos Ctrl+1 … Ctrl+5
        for i in range(self.paginas.count()):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.ir_a(i))

    def ir_a(self, indice: int) -> None:
        self.paginas.setCurrentIndex(indice)
        self.barra.seleccionar(indice)
        actual = self.paginas.currentWidget()
        if actual is self.vista_chat:
            self.vista_chat.entrada.setFocus()
        elif actual is self.vista_chat_dual:
            self.vista_chat_dual.panel_a.entrada.setFocus()

    def _avisar(self, mensaje: str) -> None:
        QMessageBox.warning(self, "Historial", mensaje)

    def _actualizar_insignia(self) -> None:
        self.barra.botones[self.paginas.indexOf(self.vista_historial)].set_insignia(
            len(self.estado.historial))


def configurar_aplicacion(app: QApplication) -> None:
    """Aplica estilo base, tipografía y hoja de estilos global."""
    # Fusion + diseño de interfaz/marcos.py aplicado a toda la interfaz (ver marcos_globales.py).
    app.setStyle(EstiloMarcos(QStyleFactory.create("Fusion")))
    estilos.preparar_fuentes()            # Sora, JetBrains Mono y STIX Two Math (interfaz/recursos/fuentes)
    app.setFont(estilos.fuente(10))
    paleta = app.palette()
    paleta.setColor(QPalette.ColorRole.PlaceholderText, qcolor(C.TEXTO_SECUNDARIO, 175))
    app.setPalette(paleta)
    app.setStyleSheet(estilos.hoja_estilos())
    app.setApplicationName("CodeChat Pro")
