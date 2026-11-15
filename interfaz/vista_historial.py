"""Historial: transmisiones realizadas durante la sesión."""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from interfaz.componentes import (
    AreaDesplazable, Chip, ChipEstado, ControlSegmentado, EtiquetaRecortada, DialogoDetalle, EncabezadoPagina, EstadoVacio,
    TarjetaMetrica, etiqueta, formato_ber, formato_p,
)
from interfaz import persistencia
from interfaz.estado import EstadoApp
from interfaz.estilos import C, rgba
from interfaz.iconos import icono, pixmap

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
            plano = " ".join(r.texto.split())   # una sola línea en el listado
            resumen = plano if len(plano) <= 70 else plano[:67] + "…"
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
        contenedor_estado = QWidget()
        contenedor_estado.setFixedWidth(184)
        ce = QHBoxLayout(contenedor_estado)
        ce.setContentsMargins(0, 0, 0, 0)
        ce.addWidget(ChipEstado(r.estado))
        ce.addStretch(1)
        fila.addWidget(contenedor_estado)

        copiar = QPushButton()
        copiar.setObjectName("BotonFantasma")
        copiar.setIcon(icono("copiar", C.TEXTO_SECUNDARIO, 16))
        copiar.setToolTip("Copiar el mensaje recuperado" if r.texto is not None
                          else "Copiar los bits recuperados")
        copiar.setCursor(Qt.CursorShape.PointingHandCursor)

        def copiar_contenido():
            QApplication.clipboard().setText(r.texto_recuperado if r.texto_recuperado is not None
                                             else r.recuperado)
            copiar.setIcon(icono("doble_check", C.VERDE, 16))
            QTimer.singleShot(1200, lambda: copiar.setIcon(icono("copiar", C.TEXTO_SECUNDARIO, 16)))

        copiar.clicked.connect(copiar_contenido)
        fila.addWidget(copiar)

        ver = QPushButton("  Detalles")
        ver.setObjectName("BotonDetalles")
        ver.setIcon(icono("expandir", C.TEXTO_SECUNDARIO, 14))
        ver.setToolTip("Ver los detalles de transmisión")
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
                               "Transmisiones guardadas automáticamente en este equipo")
        self.boton_exportar = QPushButton("  Exportar JSON")
        self.boton_exportar.setObjectName("BotonPrimario")
        self.boton_exportar.setIcon(icono("descargar", C.TEXTO, 16))
        self.boton_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_exportar.setToolTip("Guardar una copia del historial en un archivo JSON")
        menu = QMenu(self.boton_exportar)
        menu.addAction("Historial completo (incluye mensajes y bits)…",
                       lambda: self._exportar(incluir_contenido=True))
        menu.addAction("Solo métricas (sin el contenido de los mensajes)…",
                       lambda: self._exportar(incluir_contenido=False))
        self.boton_exportar.setMenu(menu)
        cab.agregar(self.boton_exportar)
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
            "¿Eliminar todas las transmisiones guardadas?\n\n"
            "Se borrarán de la aplicación y del archivo de historial local. "
            "Las copias exportadas no se modifican.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            self.estado.limpiar_historial()

    def _refrescar(self) -> None:
        todos = self.estado.historial
        total = len(todos)
        ok = sum(1 for r in todos if r.exito)
        ambiguas = sum(1 for r in todos if r.estado == "ambiguo")
        residuales = sum(1 for r in todos if r.estado == "residual")
        self.k_total.set_valor(str(total) if total else None, "guardadas en este equipo" if total else "")
        self.k_ok.set_valor(str(ok) if total else None, f"{ok / total:.0%} del total" if total else "")
        self.k_mal.set_valor(str(residuales) if total else None,
                             (f"{residuales / total:.0%} del total"
                              + (f" · {ambiguas} ambigua(s) por empate" if ambiguas else ""))
                             if total else "")
        if total:
            con_ber = [r.ber_con_codigo for r in todos if r.ber_con_codigo is not None]
            self.k_ber.set_valor(formato_ber(sum(con_ber) / len(con_ber)) if con_ber else "N/D",
                                 "promedio de las transmisiones con BER definida"
                                 + (" (con empates: sobre bits decididos)" if ambiguas else ""))
        else:
            self.k_ber.set_valor(None)
        self.boton_limpiar.setEnabled(bool(total))
        self.boton_exportar.setEnabled(bool(total))

        filtro = self.filtro.indice()
        visibles = [r for r in todos if filtro == 0
                    or (filtro == 1 and r.origen == "chat")
                    or (filtro == 2 and r.origen == "laboratorio")
                    or (filtro == 3 and r.estado == "residual")]

        lay = self.lista.layout_interno
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not visibles:
            if todos:
                lay.addWidget(etiqueta("Ninguna transmisión coincide con este filtro.", "EtiquetaSecundaria"))
                lay.addStretch(1)
                self.pila.setCurrentWidget(self.lista)
            else:
                self.pila.setCurrentWidget(self.vacio)
            return
        for r in reversed(visibles):
            lay.addWidget(FilaHistorial(r))
        lay.addStretch(1)
        self.pila.setCurrentWidget(self.lista)

    def _exportar(self, incluir_contenido: bool) -> None:
        registros = self.estado.historial
        if not registros:
            return
        sufijo = "" if incluir_contenido else "-metricas"
        sugerido = Path.home() / f"codechat-historial{sufijo}-{datetime.now():%Y%m%d-%H%M}.json"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar historial", str(sugerido),
                                              "Archivos JSON (*.json)")
        if not ruta:
            return
        if not ruta.lower().endswith(".json"):
            ruta += ".json"
        try:
            cantidad = persistencia.exportar(Path(ruta), registros, incluir_contenido)
        except OSError as e:
            QMessageBox.critical(self, "Exportar JSON", f"No se pudo guardar el archivo:\n{e}")
            return
        detalle = "" if incluir_contenido else " (solo métricas, sin el contenido de los mensajes)"
        QMessageBox.information(self, "Exportar JSON",
                                f"Se exportaron {cantidad} registro(s){detalle} a:\n{ruta}")
