"""Historial: transmisiones realizadas durante la sesión."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from interfaz.componentes import (
    AreaDesplazable, Chip, ControlSegmentado, DialogoDetalle, EncabezadoPagina, EstadoVacio,
    TarjetaMetrica, etiqueta, formato_ber, formato_p,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import C, rgba
from interfaz.iconos import icono, pixmap

_ESTADOS = {
    "sin_errores": ("Sin errores en el canal", "exito"),
    "corregido": ("Errores corregidos", "exito"),
    "residual": ("Errores residuales", "error"),
}
_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


class FilaHistorial(QFrame):
    def __init__(self, r, parent=None):
        super().__init__(parent)
        self.setObjectName("FilaHistorial")
        self.setStyleSheet(f"""
            QFrame#FilaHistorial {{ background: {C.PANEL}; border: 1px solid {C.BORDE_SUAVE};
                                    border-radius: 14px; }}
            QFrame#FilaHistorial:hover {{ border-color: {rgba(C.ROJO, 0.55)}; }}""")
        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 12, 14, 12)
        fila.setSpacing(14)

        es_chat = r.origen == "chat"
        avatar = QLabel()
        avatar.setFixedSize(42, 42)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = C.ROJO if es_chat else C.AZUL
        avatar.setPixmap(pixmap("chat" if es_chat else "laboratorio", color, 20))
        avatar.setStyleSheet(f"background: {rgba(color, 0.12)}; border: 1px solid {rgba(color, 0.4)};"
                             " border-radius: 21px;")
        fila.addWidget(avatar)

        textos = QVBoxLayout()
        textos.setSpacing(3)
        if r.texto is not None:
            resumen = r.texto if len(r.texto) <= 70 else r.texto[:67] + "…"
        else:
            resumen = f"Secuencia de {len(r.bits_originales)} bits"
        textos.addWidget(etiqueta(resumen, "Etiqueta"))
        f = r.fecha
        textos.addWidget(etiqueta(
            f"#{r.id} · {f.day} {_MESES[f.month - 1]} {f.year} · {f:%H:%M:%S} · "
            f"{'Chat' if es_chat else 'Laboratorio BSC'}", "EtiquetaTenue"))
        fila.addLayout(textos, 1)

        fila.addWidget(Chip(f"n = {r.n}", "neutro"))
        fila.addWidget(Chip(f"p = {formato_p(r.p)}", "neutro"))
        ber = etiqueta(f"BER {formato_ber(r.ber_con_codigo)}", "Mono")
        ber.setMinimumWidth(110)
        ber.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        fila.addWidget(ber)
        texto_estado, tipo = _ESTADOS[r.estado]
        chip = Chip(texto_estado, tipo)
        chip.setMinimumWidth(150)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fila.addWidget(chip)

        ver = QPushButton()
        ver.setObjectName("BotonFantasma")
        ver.setIcon(icono("expandir", C.TEXTO_SECUNDARIO, 16))
        ver.setToolTip("Ver detalle de la transmisión")
        ver.setCursor(Qt.CursorShape.PointingHandCursor)
        ver.clicked.connect(lambda: DialogoDetalle(r, self.window()).exec())
        fila.addWidget(ver)


class VistaHistorial(QWidget):
    FILTROS = ["Todas", "Chat", "Laboratorio", "Con errores residuales"]

    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        cab = EncabezadoPagina("historial", "Historial",
                               "Transmisiones realizadas durante esta sesión")
        self.boton_limpiar = QPushButton("  Limpiar historial")
        self.boton_limpiar.setIcon(icono("papelera", C.TEXTO_SECUNDARIO, 16))
        self.boton_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        cab.agregar(self.boton_limpiar)
        caja.addWidget(cab)

        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(24, 22, 18, 0)
        cuerpo.setSpacing(16)
        caja.addLayout(cuerpo, 1)

        kpis = QHBoxLayout()
        kpis.setSpacing(12)
        self.k_total = TarjetaMetrica("Transmisiones", C.AZUL)
        self.k_ok = TarjetaMetrica("Recuperadas sin errores", C.VERDE)
        self.k_mal = TarjetaMetrica("Con errores residuales", C.ROJO)
        self.k_ber = TarjetaMetrica("BER medio con código", C.AMBAR)
        for k in (self.k_total, self.k_ok, self.k_mal, self.k_ber):
            kpis.addWidget(k)
        cuerpo.addLayout(kpis)

        fila_filtro = QHBoxLayout()
        self.filtro = ControlSegmentado(self.FILTROS)
        fila_filtro.addWidget(self.filtro)
        fila_filtro.addStretch(1)
        cuerpo.addLayout(fila_filtro)

        self.pila = QStackedWidget()
        self.vacio = EstadoVacio("historial", "Todavía no hay transmisiones",
                                 "Cada mensaje del chat y cada experimento del laboratorio "
                                 "aparecerá aquí con sus métricas.")
        self.lista = AreaDesplazable(margenes=(0, 0, 6, 22), espaciado=10)
        self.pila.addWidget(self.vacio)
        self.pila.addWidget(self.lista)
        cuerpo.addWidget(self.pila, 1)

        self.filtro.cambiado.connect(lambda _i: self._refrescar())
        self.boton_limpiar.clicked.connect(self._confirmar_limpieza)
        estado.transmision_registrada.connect(lambda _r: self._refrescar())
        estado.historial_limpiado.connect(self._refrescar)
        self._refrescar()

    def _confirmar_limpieza(self) -> None:
        if not self.estado.historial:
            return
        respuesta = QMessageBox.question(
            self, "Limpiar historial",
            "¿Eliminar todas las transmisiones registradas en esta sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            self.estado.limpiar_historial()

    def _refrescar(self) -> None:
        todos = self.estado.historial
        total = len(todos)
        ok = sum(1 for r in todos if r.exito)
        self.k_total.set_valor(str(total) if total else None, "en esta sesión" if total else "")
        self.k_ok.set_valor(str(ok) if total else None, f"{ok / total:.0%} del total" if total else "")
        self.k_mal.set_valor(str(total - ok) if total else None,
                             f"{(total - ok) / total:.0%} del total" if total else "")
        if total:
            self.k_ber.set_valor(formato_ber(sum(r.ber_con_codigo for r in todos) / total),
                                 "promedio de todas las transmisiones")
        else:
            self.k_ber.set_valor(None)
        self.boton_limpiar.setEnabled(bool(total))

        filtro = self.filtro.indice()
        visibles = [r for r in todos if filtro == 0
                    or (filtro == 1 and r.origen == "chat")
                    or (filtro == 2 and r.origen == "laboratorio")
                    or (filtro == 3 and not r.exito)]

        lay = self.lista.layout_interno
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not visibles:
            self.pila.setCurrentWidget(self.vacio)
            return
        for r in reversed(visibles):
            lay.addWidget(FilaHistorial(r))
        lay.addStretch(1)
        self.pila.setCurrentWidget(self.lista)
