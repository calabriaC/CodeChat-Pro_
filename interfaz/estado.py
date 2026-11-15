"""Estado compartido de la interfaz, comunicado mediante señales Qt."""

from PySide6.QtCore import QObject, Signal

from interfaz import servicio
from interfaz.persistencia import AlmacenHistorial, ErrorHistorial


class EstadoApp(QObject):
    """Configuración activa del canal e historial (persistente) de transmisiones."""

    configuracion_cambiada = Signal(int, float)   # n, p
    transmision_registrada = Signal(object)       # ResultadoTransmision
    historial_limpiado = Signal()
    aviso_persistencia = Signal(str)              # problema al leer/guardar el historial

    def __init__(self, parent=None, almacen: AlmacenHistorial | None = None):
        super().__init__(parent)
        self._n = servicio.N_POR_DEFECTO
        self._p = servicio.P_POR_DEFECTO
        self._historial: list = []
        self.almacen = almacen if almacen is not None else AlmacenHistorial()
        self.error_carga: str | None = None
        self._cargar()

    # ---- persistencia --------------------------------------------------
    def _cargar(self) -> None:
        try:
            self._historial = self.almacen.cargar()
        except ErrorHistorial as e:
            self._historial = []
            self.error_carga = str(e)
        if self._historial:
            servicio.sincronizar_ids(max(r.id for r in self._historial))

    def _guardar(self) -> None:
        try:
            self.almacen.guardar(self._historial)
        except OSError as e:
            self.aviso_persistencia.emit(f"No se pudo guardar el historial en\n{self.almacen.ruta}\n\n{e}")

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
        if any(r.id == resultado.id for r in self._historial):
            return
        self._historial.append(resultado)
        self._guardar()
        self.transmision_registrada.emit(resultado)

    def limpiar_historial(self) -> None:
        self._historial.clear()
        try:
            self.almacen.borrar()
        except OSError as e:
            self.aviso_persistencia.emit(f"No se pudo vaciar el archivo de historial:\n{e}")
        self.historial_limpiado.emit()
