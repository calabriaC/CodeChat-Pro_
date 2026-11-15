"""Estado compartido de la interfaz, comunicado mediante señales Qt."""

from PySide6.QtCore import QObject, Signal

from interfaz import servicio


class EstadoApp(QObject):
    """Configuración activa del canal e historial de la sesión."""

    configuracion_cambiada = Signal(int, float)   # n, p
    transmision_registrada = Signal(object)       # ResultadoTransmision
    historial_limpiado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._n = servicio.N_POR_DEFECTO
        self._p = servicio.P_POR_DEFECTO
        self._historial: list = []

    # ---- configuración -------------------------------------------------
    @property
    def n(self) -> int:
        return self._n

    @property
    def p(self) -> float:
        return self._p

    def establecer_n(self, n: int) -> None:
        if n != self._n:
            self._n = n
            self.configuracion_cambiada.emit(self._n, self._p)

    def establecer_p(self, p: float) -> None:
        p = round(float(p), 4)
        if p != self._p:
            self._p = p
            self.configuracion_cambiada.emit(self._n, self._p)

    # ---- historial -----------------------------------------------------
    @property
    def historial(self) -> list:
        return list(self._historial)

    def registrar(self, resultado) -> None:
        self._historial.append(resultado)
        self.transmision_registrada.emit(resultado)

    def limpiar_historial(self) -> None:
        self._historial.clear()
        self.historial_limpiado.emit()
