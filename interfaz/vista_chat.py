"""Vista de Chat: conversación central + panel derecho de canal y métricas."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from interfaz import servicio
from interfaz.componentes import (
    AreaDesplazable, Chip, ControlProbabilidad, EncabezadoPagina, EstadoVacio, SelectorN,
    Tarjeta, TarjetaDetalleTransmision, TarjetaMetrica, etiqueta, formato_ber, formato_p,
    icono_label, repulir, texto_ajustable,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import ANCHO_PANEL_DERECHO, C, qcolor, rgba
from interfaz.grafica import GraficaBER, Serie
from interfaz.iconos import icono, pixmap

LONGITUD_MAXIMA = 500


def _hora() -> str:
    return datetime.now().strftime("%H:%M")


class _ConTextoAjustable:
    """Mezcla: da a la etiqueta principal su anchura natural sin superar el máximo."""

    _lbl: QLabel
    _relleno = 36

    def ajustar_ancho(self, ancho_max: int) -> None:
        self._lbl.ensurePolished()
        fm = self._lbl.fontMetrics()
        natural = max(fm.horizontalAdvance(linea) for linea in self._lbl.text().split("\n")) + 4
        self._lbl.setMinimumWidth(max(60, min(natural, ancho_max - self._relleno)))


# ===========================================================================
# Elementos de la conversación
# ===========================================================================
class BurbujaEnviada(_ConTextoAjustable, QFrame):
    """Mensaje del usuario, alineado a la derecha, con hora e indicador de estado."""

    def __init__(self, texto: str, parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaEnviada")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 11, 14, 8)
        caja.setSpacing(4)
        self._lbl = lbl = etiqueta(texto_ajustable(texto), "TextoBurbuja", ajustar=True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(lbl)
        pie = QHBoxLayout()
        pie.setSpacing(6)
        pie.addStretch(1)
        pie.addWidget(etiqueta(_hora(), "HoraBurbuja"))
        self._estado = QLabel()
        self._estado.setFixedSize(16, 16)
        pie.addWidget(self._estado)
        caja.addLayout(pie)
        self.set_estado("enviando")

    def set_estado(self, estado: str) -> None:
        nombre, color, ayuda = {
            "enviando": ("reloj", C.TEXTO_SECUNDARIO, "Transmitiendo por el canal BSC…"),
            "entregado": ("doble_check", C.TEXTO, "Transmitido y decodificado"),
            "error": ("alerta", C.AMBAR, "No se pudo transmitir"),
        }[estado]
        self._estado.setPixmap(pixmap(nombre, color, 15))
        self._estado.setToolTip(ayuda)


class BurbujaRecibida(_ConTextoAjustable, QFrame):
    """Respuesta de CodeChat Pro (o aviso del sistema)."""

    def __init__(self, texto: str, autor: str = "CodeChat Pro", sistema: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaSistema" if sistema else "BurbujaRecibida")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 12, 16, 9)
        caja.setSpacing(3)
        caja.addWidget(etiqueta(autor, "AutorBurbuja"))
        self._lbl = lbl = etiqueta(texto, "TextoBurbuja", ajustar=True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(lbl)
        hora = etiqueta(_hora(), "HoraBurbuja")
        hora.setAlignment(Qt.AlignmentFlag.AlignRight)
        caja.addWidget(hora)


class Avatar(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 46)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPixmap(pixmap("bot", C.TEXTO, 22))
        self.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {C.ROJO_OSCURO}, stop:1 #3A0E1C);"
            f" border: 1px solid {rgba(C.ROJO, 0.55)}; border-radius: 23px;")


class IndicadorEscritura(QFrame):
    """Tres puntos animados mientras el mensaje atraviesa el canal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BurbujaRecibida")
        self.setFixedSize(QSize(170, 46))
        self._fase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._avanzar)
        self._timer.start(160)

    def _avanzar(self):
        self._fase = (self._fase + 1) % 6
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(3):
            activo = (self._fase // 2) == i
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor(C.ROJO if activo else C.TEXTO_SECUNDARIO, 255 if activo else 120))
            p.drawEllipse(QRectF(18 + i * 13, 19 - (2 if activo else 0), 8, 8))
        p.setPen(QColor(C.TEXTO_SECUNDARIO))
        p.setFont(self.font())
        p.drawText(QRectF(64, 0, 100, self.height()), Qt.AlignmentFlag.AlignVCenter, "Transmitiendo…")
        p.end()


class Conversacion(QScrollArea):
    """Lista desplazable de mensajes con anchura máxima adaptable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido = QWidget()
        contenido.setObjectName("Pagina")
        self._lista = QVBoxLayout(contenido)
        self._lista.setContentsMargins(28, 20, 28, 20)
        self._lista.setSpacing(16)
        self._lista.addStretch(1)
        self.setWidget(contenido)
        self._limitados: list[tuple[QWidget, float]] = []
        self._seguir_final = False
        self.verticalScrollBar().rangeChanged.connect(self._al_cambiar_rango)
        self._animaciones: list[QPropertyAnimation] = []

    # ---- añadir elementos ---------------------------------------------
    def _insertar(self, widget: QWidget) -> None:
        self._lista.insertWidget(self._lista.count() - 1, widget)
        self._aparecer(widget)
        self._seguir_final = True

    def _aparecer(self, widget: QWidget) -> None:
        efecto = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(efecto)
        anim = QPropertyAnimation(efecto, b"opacity", self)
        anim.setDuration(240)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def terminar():
            widget.setGraphicsEffect(None)
            if anim in self._animaciones:
                self._animaciones.remove(anim)

        anim.finished.connect(terminar)
        self._animaciones.append(anim)
        anim.start()

    def _limitar(self, widget: QWidget, proporcion: float) -> None:
        self._limitados.append((widget, proporcion))
        self._aplicar_limite(widget, proporcion, self.viewport().width())

    @staticmethod
    def _aplicar_limite(widget: QWidget, proporcion: float, ancho: int) -> None:
        maximo = max(260, int(ancho * proporcion))
        widget.setMaximumWidth(maximo)
        if isinstance(widget, _ConTextoAjustable):
            widget.ajustar_ancho(maximo)

    def agregar_separador(self, texto: str) -> None:
        lbl = etiqueta(texto, "SeparadorFecha")
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addStretch(1)
        fila.addWidget(lbl)
        fila.addStretch(1)
        self._insertar(envoltura)

    def agregar_enviado(self, texto: str) -> BurbujaEnviada:
        burbuja = BurbujaEnviada(texto)
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(80, 0, 0, 0)
        fila.addStretch(1)
        fila.addWidget(burbuja)
        self._limitar(burbuja, 0.62)
        self._insertar(envoltura)
        return burbuja

    def agregar_recibido(self, widgets: list[QWidget]) -> QWidget:
        envoltura = QWidget()
        fila = QHBoxLayout(envoltura)
        fila.setContentsMargins(0, 0, 40, 0)
        fila.setSpacing(14)
        fila.addWidget(Avatar(), 0, Qt.AlignmentFlag.AlignTop)
        columna = QVBoxLayout()
        columna.setSpacing(12)
        for w in widgets:
            if isinstance(w, TarjetaDetalleTransmision):
                # Ocupa todo el ancho disponible hasta su máximo.
                columna.addWidget(w)
                self._limitar(w, 0.80)
            else:
                linea = QHBoxLayout()
                linea.setContentsMargins(0, 0, 0, 0)
                linea.addWidget(w)
                linea.addStretch(1)
                columna.addLayout(linea)
                self._limitar(w, 0.66)
        fila.addLayout(columna, 1)
        self._insertar(envoltura)
        return envoltura

    def quitar(self, widget: QWidget) -> None:
        self._limitados = [(w, prop) for w, prop in self._limitados if w is not widget
                           and not widget.isAncestorOf(w)]
        self._lista.removeWidget(widget)
        widget.deleteLater()

    def limpiar(self) -> None:
        while self._lista.count() > 1:
            item = self._lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._limitados.clear()

    # ---- comportamiento ---------------------------------------------
    def _al_cambiar_rango(self, _min, maximo):
        if self._seguir_final:
            self.verticalScrollBar().setValue(maximo)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        ancho = self.viewport().width()
        for w, proporcion in self._limitados:
            self._aplicar_limite(w, proporcion, ancho)


# ===========================================================================
# Panel derecho
# ===========================================================================
class PanelCanal(AreaDesplazable):
    """Configuración del canal, métricas y gráfica BER frente a la tasa."""

    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(margenes=(0, 18, 18, 18), espaciado=16, parent=parent)
        self.estado = estado
        self.setMinimumWidth(ANCHO_PANEL_DERECHO - 50)
        self.setMaximumWidth(ANCHO_PANEL_DERECHO + 30)
        caja = self.layout_interno

        # ---- Configuración --------------------------------------------
        config = Tarjeta("Configuración del canal", "ajustes")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(12)
        rejilla.setVerticalSpacing(6)
        rejilla.addWidget(etiqueta("Código de repetición (n)", "Etiqueta"), 0, 0)
        self.selector_n = SelectorN(estado.n)
        rejilla.addWidget(self.selector_n, 0, 1)
        rejilla.addWidget(etiqueta("Cada bit se envía n veces · solo n impar", "Ayuda"), 1, 0, 1, 2)
        rejilla.setRowMinimumHeight(2, 8)
        rejilla.addWidget(etiqueta("Probabilidad de error (p)", "Etiqueta"), 3, 0, 1, 2)
        self.control_p = ControlProbabilidad(estado.p)
        rejilla.addWidget(self.control_p, 4, 0, 1, 2)
        rejilla.addWidget(etiqueta("Probabilidad de que el canal BSC invierta cada bit (0 – 0.5)",
                                   "Ayuda", ajustar=True), 5, 0, 1, 2)
        config.cuerpo.addLayout(rejilla)
        self.boton_transmitir = QPushButton("  Transmitir mensaje")
        self.boton_transmitir.setObjectName("BotonPrimario")
        self.boton_transmitir.setIcon(icono("play", C.TEXTO, 18))
        self.boton_transmitir.setIconSize(QSize(18, 18))
        self.boton_transmitir.setCursor(Qt.CursorShape.PointingHandCursor)
        config.cuerpo.addWidget(self.boton_transmitir)
        caja.addWidget(config)

        # ---- Métricas --------------------------------------------------
        metricas = Tarjeta("Métricas de la transmisión", "analisis")
        rej = QGridLayout()
        rej.setSpacing(10)
        self.m_dmin = TarjetaMetrica("Distancia mínima d_min", C.MORADO,
                                     "d_min = n para un código de repetición.")
        self.m_t = TarjetaMetrica("t (errores corregibles)", C.ROJO, "t = ⌊(d_min − 1) / 2⌋")
        self.m_r = TarjetaMetrica("Tasa R = k/n", C.AZUL, "Fracción de bits útiles transmitidos.")
        self.m_ber = TarjetaMetrica("BER experimental", C.AMBAR,
                                    "Tasa de error de bits medida en la última transmisión.")
        self.m_cap = TarjetaMetrica("Capacidad de Shannon", C.VERDE, "C = 1 − H₂(p)")
        rej.addWidget(self.m_t, 0, 0)
        rej.addWidget(self.m_r, 0, 1)
        rej.addWidget(self.m_dmin, 1, 0)
        rej.addWidget(self.m_cap, 1, 1)
        rej.addWidget(self.m_ber, 2, 0, 1, 2)
        metricas.cuerpo.addLayout(rej)
        caja.addWidget(metricas)

        # ---- Gráfica ---------------------------------------------------
        tarjeta_grafica = Tarjeta("BER frente a la tasa", "grafica",
                                  "Curva teórica para el p actual y puntos medidos en el chat")
        self.grafica = GraficaBER()
        self.grafica.setMinimumHeight(270)
        tarjeta_grafica.cuerpo.addWidget(self.grafica)
        caja.addWidget(tarjeta_grafica)
        caja.addStretch(1)

        # ---- Señales ---------------------------------------------------
        self.selector_n.n_cambiado.connect(estado.establecer_n)
        self.control_p.valor_cambiado.connect(estado.establecer_p)
        estado.configuracion_cambiada.connect(self._al_configurar)
        estado.transmision_registrada.connect(lambda _r: self._refrescar())
        estado.historial_limpiado.connect(self._refrescar)
        self._refrescar()

    def _al_configurar(self, n: int, p: float) -> None:
        self.selector_n.set_n(n)
        if abs(self.control_p.valor() - p) > 1e-9:
            self.control_p.set_valor(p)
        self._refrescar()

    def _refrescar(self) -> None:
        n, p = self.estado.n, self.estado.p
        par = servicio.parametros(n)
        self.m_dmin.set_valor(str(par["distancia_minima"]), f"Detecta hasta {par['errores_detectables']} errores")
        self.m_t.set_valor(str(par["errores_corregibles"]), "por bloque de n bits")
        self.m_r.set_valor(f"{par['tasa']:.2f}", f"k = {par['k']}, n = {par['n']}")
        cap = servicio.capacidad(p)
        self.m_cap.set_valor(f"{cap:.3f}", f"bits por uso del canal (p = {formato_p(p)})")

        chat = [r for r in self.estado.historial if r.origen == "chat"]
        if chat:
            u = chat[-1]
            self.m_ber.set_valor(formato_ber(u.ber_con_codigo),
                                 f"Última transmisión (n = {u.n}, p = {formato_p(u.p)}) · "
                                 f"sin código: {formato_ber(u.ber_sin_codigo)}")
        else:
            self.m_ber.set_valor(None, "Transmite un mensaje para medirla")

        # Gráfica: curva teórica (core) + puntos medidos con el mismo p
        medidos = [r for r in chat if abs(r.p - p) < 1e-9]
        por_n: dict[int, list[float]] = {}
        for r in medidos:
            por_n.setdefault(r.n, []).append(r.ber_con_codigo)
        exp_con = sorted((1 / k, sum(v) / len(v)) for k, v in por_n.items())
        etiquetas = [f"n={round(1 / x)}" for x, _ in exp_con]
        series = [Serie("Teórico con código", C.AZUL, servicio.curva_teorica(p))]
        if exp_con:
            series.append(Serie("Medido con código", C.AMBAR, exp_con, tipo="puntos", etiquetas=etiquetas))
            sin = [r.ber_sin_codigo for r in medidos]
            series.append(Serie("Medido sin código", C.ROJO, [(1.0, sum(sin) / len(sin))], tipo="puntos"))
        self.grafica.set_datos(series, vertical=(cap, "C"))


# ===========================================================================
# Vista completa
# ===========================================================================
class VistaChat(QWidget):
    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        self._ocupado = False
        self._hay_mensajes = False

        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(18)

        # ---- Columna central ------------------------------------------
        centro = QFrame()
        centro.setObjectName("Pagina")
        col = QVBoxLayout(centro)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        cabecera = EncabezadoPagina(
            "chat", "Chat",
            "Envía mensajes con protección de errores mediante códigos de repetición")
        self.chip_canal = Chip("", "info")
        cabecera.agregar(self.chip_canal)
        self.boton_limpiar = QPushButton()
        self.boton_limpiar.setObjectName("BotonFantasma")
        self.boton_limpiar.setIcon(icono("papelera", C.TEXTO_SECUNDARIO, 18))
        self.boton_limpiar.setToolTip("Vaciar la conversación (el historial se conserva)")
        self.boton_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        cabecera.agregar(self.boton_limpiar)
        col.addWidget(cabecera)

        self.pila = QStackedWidget()
        self.vacio = EstadoVacio(
            "chat", "Tu conversación empieza aquí",
            "Escribe un mensaje: se convertirá a bits, se codificará con repetición, "
            "atravesará el canal BSC y será decodificado por mayoría.",
            ["Hola, CodeChat Pro 👋", "Teoría de códigos", "¡Perfecto! 🚀"])
        self.conversacion = Conversacion()
        self.pila.addWidget(self.vacio)
        self.pila.addWidget(self.conversacion)
        col.addWidget(self.pila, 1)

        barra = QFrame()
        barra.setObjectName("BarraEntrada")
        fila_barra = QHBoxLayout(barra)
        fila_barra.setContentsMargins(14, 10, 10, 10)
        fila_barra.setSpacing(10)
        fila_barra.addWidget(icono_label("binario", C.TEXTO_TENUE, 22))
        self.entrada = QLineEdit()
        self.entrada.setObjectName("EntradaMensaje")
        self.entrada.setPlaceholderText("Escribe un mensaje…")
        self.entrada.setMaxLength(LONGITUD_MAXIMA)
        fila_barra.addWidget(self.entrada, 1)
        self.contador = etiqueta(f"0/{LONGITUD_MAXIMA}", "EtiquetaTenue")
        self.contador.setMinimumWidth(52)
        self.contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fila_barra.addWidget(self.contador)
        self.boton_enviar = QPushButton()
        self.boton_enviar.setObjectName("BotonEnviar")
        self.boton_enviar.setIcon(icono("enviar", C.TEXTO, 22))
        self.boton_enviar.setIconSize(QSize(22, 22))
        self.boton_enviar.setFixedSize(52, 48)
        self.boton_enviar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_enviar.setToolTip("Transmitir (Enter)")
        fila_barra.addWidget(self.boton_enviar)

        envoltura_barra = QWidget()
        eb = QVBoxLayout(envoltura_barra)
        eb.setContentsMargins(18, 8, 0, 18)
        eb.addWidget(barra)
        col.addWidget(envoltura_barra)
        fila.addWidget(centro, 1)

        # ---- Panel derecho --------------------------------------------
        self.panel = PanelCanal(estado)
        fila.addWidget(self.panel)

        # ---- Señales --------------------------------------------------
        self.entrada.returnPressed.connect(self.enviar)
        self.entrada.textChanged.connect(self._al_escribir)
        self.boton_enviar.clicked.connect(self.enviar)
        self.panel.boton_transmitir.clicked.connect(self.enviar)
        self.boton_limpiar.clicked.connect(self.limpiar)
        self.vacio.sugerencia_elegida.connect(self._usar_sugerencia)
        estado.configuracion_cambiada.connect(lambda n, p: self._actualizar_chip())
        self._actualizar_chip()

    # ---- interacción ------------------------------------------------------
    def _actualizar_chip(self) -> None:
        self.chip_canal.setText(f"Canal BSC · n = {self.estado.n} · p = {formato_p(self.estado.p)}")

    def _al_escribir(self, texto: str) -> None:
        self.contador.setText(f"{len(texto)}/{LONGITUD_MAXIMA}")
        if self.entrada.property("alerta"):
            self.entrada.setProperty("alerta", False)
            repulir(self.entrada)

    def _usar_sugerencia(self, texto: str) -> None:
        self.entrada.setText(texto)
        self.entrada.setFocus()

    def _alertar_vacio(self) -> None:
        self.entrada.setProperty("alerta", True)
        repulir(self.entrada)
        self.entrada.setPlaceholderText("Escribe un mensaje para transmitirlo…")
        self.entrada.setFocus()

    def enviar(self) -> None:
        texto = self.entrada.text().strip()
        if self._ocupado:
            return
        if not texto:
            self._alertar_vacio()
            return
        self._ocupado = True
        self.boton_enviar.setEnabled(False)
        self.panel.boton_transmitir.setEnabled(False)
        self.entrada.clear()
        self.entrada.setPlaceholderText("Escribe un mensaje…")

        if not self._hay_mensajes:
            self._hay_mensajes = True
            self.pila.setCurrentWidget(self.conversacion)
            self.conversacion.agregar_separador("Hoy")

        burbuja = self.conversacion.agregar_enviado(texto)
        indicador = self.conversacion.agregar_recibido([IndicadorEscritura()])
        n, p = self.estado.n, self.estado.p
        QTimer.singleShot(650, lambda: self._completar(texto, n, p, burbuja, indicador))

    def _completar(self, texto, n, p, burbuja: BurbujaEnviada, indicador: QWidget) -> None:
        self.conversacion.quitar(indicador)
        try:
            r = servicio.transmitir_texto(texto, n, p)
        except (ValueError, TypeError) as error:
            burbuja.set_estado("error")
            self.conversacion.agregar_recibido(
                [BurbujaRecibida(f"No se pudo transmitir el mensaje: {error}", "Aviso del sistema", True)])
        else:
            burbuja.set_estado("entregado")
            self.estado.registrar(r)
            self.conversacion.agregar_recibido([
                BurbujaRecibida(self._respuesta(r)),
                TarjetaDetalleTransmision(r, compacta=True),
            ])
        self._ocupado = False
        self.boton_enviar.setEnabled(True)
        self.panel.boton_transmitir.setEnabled(True)
        self.entrada.setFocus()

    @staticmethod
    def _respuesta(r: servicio.ResultadoTransmision) -> str:
        base = f"Tu mensaje fue transmitido a través del canal BSC usando un código de repetición (n = {r.n})."
        if r.estado == "sin_errores":
            return f"{base} El canal no alteró ningún bit."
        if r.estado == "corregido":
            return (f"{base} El canal alteró {r.errores_canal} bit(s) y la "
                    f"decodificación por mayoría los corrigió todos.")
        return (f"{base} El canal alteró {r.errores_canal} bit(s); {r.bloques_fallidos} bloque(s) "
                f"superaron t = {r.t}, por lo que el mensaje recuperado contiene errores.")

    def limpiar(self) -> None:
        if self._ocupado:
            return
        self.conversacion.limpiar()
        self._hay_mensajes = False
        self.pila.setCurrentWidget(self.vacio)
