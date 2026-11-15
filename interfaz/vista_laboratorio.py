"""Laboratorio BSC: experimentación libre con n, p y secuencias binarias."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget,
)

from interfaz import servicio
from interfaz.componentes import (
    AreaDesplazable, ControlProbabilidad, ControlSegmentado, EncabezadoPagina, EstadoVacio,
    SelectorN, Tarjeta, TarjetaDetalleTransmision, TarjetaMetrica, etiqueta, formato_ber,
    formato_p,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import C
from interfaz.iconos import icono

MAX_BITS = 20000
MAX_CARACTERES = 500


class TablaComparacion(Tarjeta):
    """Medición experimental frente a predicción teórica, claramente separadas."""

    def __init__(self, parent=None):
        super().__init__("Teoría frente a experimento", "analisis",
                         "Las mediciones dependen del azar del canal; las predicciones, solo de n y p",
                         parent=parent)
        fila = QHBoxLayout()
        fila.setSpacing(14)
        self._exp = self._columna(fila, "MEDICIÓN EXPERIMENTAL (ESTA EJECUCIÓN)", C.AMBAR, [
            ("ber_sin", "BER sin código", "El mismo mensaje enviado sin codificar"),
            ("ber_canal", "BER antes de decodificar", "Bits codificados enviados vs. recibidos"),
            ("ber_con", "BER después de decodificar", "Bits originales vs. bits decodificados"),
        ])
        self._teo = self._columna(fila, "PREDICCIÓN TEÓRICA (NÚCLEO)", C.MORADO, [
            ("pe", "Pₑ residual teórico", "Suma de C(n,i)·p^i·(1−p)^(n−i) para i > t"),
            ("t", "Capacidad de corrección t", "⌊(d_min − 1)/2⌋"),
            ("r", "Tasa R = k/n", "Información útil por bit transmitido"),
            ("c", "Capacidad de Shannon C", "1 − H₂(p): límite teórico de tasa fiable"),
        ])
        self.cuerpo.addLayout(fila)
        self.nota = etiqueta("", "Ayuda", ajustar=True)
        self.cuerpo.addWidget(self.nota)

    def _columna(self, fila, titulo, color, filas):
        marco = QFrame()
        marco.setObjectName("TarjetaInterna")
        marco.setStyleSheet(f"QFrame#TarjetaInterna {{ border-top: 3px solid {color}; }}")
        rej = QGridLayout(marco)
        rej.setContentsMargins(14, 12, 14, 12)
        rej.setHorizontalSpacing(12)
        rej.setVerticalSpacing(8)
        cab = etiqueta(titulo, "Seccion")
        cab.setStyleSheet(f"color: {color};")
        rej.addWidget(cab, 0, 0, 1, 2)
        valores = {}
        for i, (clave, nombre, ayuda) in enumerate(filas, 1):
            lbl = etiqueta(nombre, "EtiquetaSecundaria")
            lbl.setToolTip(ayuda)
            rej.addWidget(lbl, i, 0)
            v = etiqueta("—", "Mono")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            rej.addWidget(v, i, 1)
            valores[clave] = v
        rej.setColumnStretch(0, 1)
        rej.setRowStretch(len(filas) + 1, 1)
        fila.addWidget(marco, 1)
        return valores

    def mostrar(self, r: servicio.ResultadoTransmision) -> None:
        self._exp["ber_sin"].setText(formato_ber(r.ber_sin_codigo))
        self._exp["ber_canal"].setText(formato_ber(r.ber_canal))
        self._exp["ber_con"].setText(formato_ber(r.ber_con_codigo))
        pe = r.error_residual_teorico
        self._teo["pe"].setText(formato_ber(pe) if pe is not None else "No disponible")
        self._teo["t"].setText(str(r.t))
        self._teo["r"].setText(f"{r.parametros['tasa']:.4f}")
        self._teo["c"].setText(f"{r.capacidad:.4f}")
        self.nota.setText(
            f"Con {len(r.bits_originales)} bits, la BER medida es una estimación sujeta a variación "
            "aleatoria y no tiene por qué coincidir con Pₑ. "
            + ("La tasa R supera la capacidad C: según Shannon, a esa tasa no puede lograrse una "
               "comunicación arbitrariamente fiable." if r.parametros["tasa"] > r.capacidad else
               "La tasa R está por debajo de C; aun así, C es un límite teórico para códigos óptimos, "
               "no una garantía de ausencia de errores para este código ni para una ejecución concreta."))


class VistaLaboratorio(QWidget):
    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        caja.addWidget(EncabezadoPagina(
            "laboratorio", "Laboratorio BSC",
            "Experimenta con la longitud del código y el ruido del canal sobre cualquier secuencia"))

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(24, 22, 18, 0)
        cuerpo.setSpacing(20)
        caja.addLayout(cuerpo, 1)

        # ---- Controles -------------------------------------------------
        controles = Tarjeta("Parámetros del experimento", "ajustes")
        controles.setFixedWidth(370)
        c = controles.cuerpo
        c.addWidget(etiqueta("ENTRADA", "Seccion"))
        self.modo = ControlSegmentado(["Texto", "Bits"])
        c.addWidget(self.modo)
        self.entrada = QPlainTextEdit()
        self.entrada.setFixedHeight(120)
        self.entrada.setPlainText("Hola, CodeChat Pro")
        c.addWidget(self.entrada)

        self.fila_aleatoria = QWidget()
        fa = QHBoxLayout(self.fila_aleatoria)
        fa.setContentsMargins(0, 0, 0, 0)
        fa.setSpacing(8)
        self.longitud = QSpinBox()
        self.longitud.setRange(8, MAX_BITS)
        self.longitud.setSingleStep(8)
        self.longitud.setValue(64)
        self.longitud.setSuffix(" bits")
        self.longitud.setAlignment(Qt.AlignmentFlag.AlignCenter)
        boton_aleatorio = QPushButton("  Generar aleatorios")
        boton_aleatorio.setIcon(icono("aleatorio", C.TEXTO, 16))
        boton_aleatorio.setCursor(Qt.CursorShape.PointingHandCursor)
        fa.addWidget(self.longitud, 1)
        fa.addWidget(boton_aleatorio, 1)
        c.addWidget(self.fila_aleatoria)
        self.fila_aleatoria.hide()
        self.ayuda_entrada = etiqueta("", "Ayuda", ajustar=True)
        c.addWidget(self.ayuda_entrada)

        c.addSpacing(4)
        c.addWidget(etiqueta("CANAL", "Seccion"))
        fila_n = QHBoxLayout()
        fila_n.addWidget(etiqueta("Código de repetición (n)", "Etiqueta"), 1)
        self.selector_n = SelectorN(estado.n)
        fila_n.addWidget(self.selector_n)
        c.addLayout(fila_n)
        c.addWidget(etiqueta("Probabilidad de error (p)", "Etiqueta"))
        self.control_p = ControlProbabilidad(estado.p)
        c.addWidget(self.control_p)
        self.info_parametros = etiqueta("", "Ayuda", ajustar=True)
        c.addWidget(self.info_parametros)

        c.addSpacing(6)
        self.boton_ejecutar = QPushButton("  Ejecutar transmisión")
        self.boton_ejecutar.setObjectName("BotonPrimario")
        self.boton_ejecutar.setIcon(icono("play", C.TEXTO, 18))
        self.boton_ejecutar.setIconSize(QSize(18, 18))
        self.boton_ejecutar.setCursor(Qt.CursorShape.PointingHandCursor)
        c.addWidget(self.boton_ejecutar)
        self.boton_repetir = QPushButton("  Repetir experimento")
        self.boton_repetir.setIcon(icono("aleatorio", C.TEXTO, 16))
        self.boton_repetir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_repetir.setToolTip("Vuelve a transmitir la misma entrada con los mismos n y p.\n"
                                      "El canal es aleatorio: el resultado puede cambiar.")
        self.boton_repetir.setEnabled(False)
        c.addWidget(self.boton_repetir)
        self._ultima: tuple | None = None
        self.error = etiqueta("", "Error", ajustar=True)
        self.error.hide()
        c.addWidget(self.error)
        c.addStretch(1)

        col_controles = QVBoxLayout()
        col_controles.setContentsMargins(0, 0, 0, 22)
        col_controles.addWidget(controles)
        cuerpo.addLayout(col_controles)

        # ---- Resultados ------------------------------------------------
        self.pila = QStackedWidget()
        self.vacio = EstadoVacio(
            "laboratorio", "Sin resultados todavía",
            "Configura la entrada, n y p, y pulsa «Ejecutar transmisión» para ver cada etapa: "
            "codificación, ruido del canal y decodificación por mayoría.")
        self.resultados = AreaDesplazable(margenes=(0, 0, 6, 22), espaciado=18)
        self.pila.addWidget(self.vacio)
        self.pila.addWidget(self.resultados)
        cuerpo.addWidget(self.pila, 1)

        # Resumen compacto (las etapas se ven en el panel inferior)
        rejilla = QGridLayout()
        rejilla.setSpacing(12)
        self.m_bits = TarjetaMetrica("Bits de información", C.MORADO)
        self.m_trans = TarjetaMetrica("Bits transmitidos", C.AZUL)
        self.m_alterados = TarjetaMetrica("Alterados por el canal", C.AMBAR)
        self.m_fallidos = TarjetaMetrica("Bloques fallidos", C.ROJO)
        for i, m in enumerate([self.m_bits, self.m_trans, self.m_alterados, self.m_fallidos]):
            rejilla.addWidget(m, 0, i)
        self.resultados.layout_interno.addLayout(rejilla)

        self.comparacion = TablaComparacion()
        self.resultados.layout_interno.addWidget(self.comparacion)
        self._detalle: QWidget | None = None
        self.resultados.layout_interno.addStretch(1)

        # ---- Señales ---------------------------------------------------
        self.modo.cambiado.connect(self._cambiar_modo)
        boton_aleatorio.clicked.connect(self._generar)
        self.boton_ejecutar.clicked.connect(self.ejecutar)
        self.boton_repetir.clicked.connect(self.repetir)
        self.selector_n.n_cambiado.connect(lambda _n: self._actualizar_info())
        self.control_p.valor_cambiado.connect(lambda _p: self._actualizar_info())
        self.entrada.textChanged.connect(self._actualizar_info)
        self._cambiar_modo(0)

    # ---------------------------------------------------------------------
    def _cambiar_modo(self, indice: int) -> None:
        bits = indice == 1
        self.fila_aleatoria.setVisible(bits)
        if bits:
            self.entrada.setPlaceholderText("Escribe o pega una secuencia de 0 y 1…")
            if not self._entrada_es_binaria():
                self._generar()
        else:
            self.entrada.setPlaceholderText("Escribe un texto (se convertirá a UTF‑8)…")
            if self._entrada_es_binaria():
                self.entrada.setPlainText("Hola, CodeChat Pro")
        self._actualizar_info()

    def _entrada_es_binaria(self) -> bool:
        limpio = "".join(self.entrada.toPlainText().split())
        return bool(limpio) and set(limpio) <= {"0", "1"}

    def _generar(self) -> None:
        self.entrada.setPlainText(servicio.bits_aleatorios(self.longitud.value()))

    def _bits_entrada(self) -> tuple[str, str | None]:
        contenido = self.entrada.toPlainText()
        if self.modo.indice() == 1:
            return "".join(contenido.split()), None
        texto = contenido.strip()
        return servicio.texto_a_bits(texto), texto

    def _actualizar_info(self) -> None:
        bits, texto = self._bits_entrada()
        n = self.selector_n.n()
        par = servicio.parametros(n)
        if texto is not None:
            self.ayuda_entrada.setText(f"{len(texto)} caracteres → {len(bits)} bits (máx. {MAX_CARACTERES} caracteres)")
        else:
            self.ayuda_entrada.setText(f"{len(bits)} bits (máx. {MAX_BITS}). Los espacios se ignoran.")
        self.info_parametros.setText(
            f"d_min = {par['distancia_minima']} · t = {par['errores_corregibles']} · "
            f"R = {par['tasa']:.3f} · {len(bits) * n} bits por el canal")

    def _mostrar_error(self, texto: str) -> None:
        self.error.setText(texto)
        self.error.setVisible(bool(texto))

    def ejecutar(self) -> None:
        bits, texto = self._bits_entrada()
        if not bits:
            self._mostrar_error("La entrada está vacía: escribe un texto o una secuencia de bits.")
            return
        if texto is not None and len(texto) > MAX_CARACTERES:
            self._mostrar_error(f"El texto supera los {MAX_CARACTERES} caracteres.")
            return
        if len(bits) > MAX_BITS:
            self._mostrar_error(f"La secuencia supera los {MAX_BITS} bits.")
            return
        self._transmitir(bits, texto, self.selector_n.n(), self.control_p.valor())

    def repetir(self) -> None:
        """Repite con la misma entrada y los mismos parámetros (el canal sigue siendo aleatorio)."""
        if self._ultima is not None:
            self._transmitir(*self._ultima)

    def _transmitir(self, bits: str, texto: str | None, n: int, p: float) -> None:
        try:
            r = servicio.transmitir(bits, n, p, texto=texto, origen="laboratorio")
        except (ValueError, TypeError) as error:
            self._mostrar_error(str(error))
            return
        self._mostrar_error("")
        self._ultima = (bits, texto, n, p)
        self.boton_repetir.setEnabled(True)
        self.boton_repetir.setText(f"  Repetir experimento (n = {n}, p = {formato_p(p)})")
        self.estado.registrar(r)
        self._mostrar(r)

    def _mostrar(self, r: servicio.ResultadoTransmision) -> None:
        self.m_bits.set_valor(str(len(r.bits_originales)))
        self.m_trans.set_valor(str(len(r.codificado)), f"R = {r.parametros['tasa']:.3f}")
        self.m_alterados.set_valor(str(r.errores_canal),
                                   f"en {r.bloques_afectados} de {r.total_bloques} bloques")
        self.m_fallidos.set_valor(str(r.bloques_fallidos),
                                  f"{r.bloques_corregidos} bloque(s) con errores corregidos")
        self.comparacion.mostrar(r)

        lay = self.resultados.layout_interno
        if self._detalle is not None:
            lay.removeWidget(self._detalle)
            self._detalle.deleteLater()
        self._detalle = TarjetaDetalleTransmision(r, compacta=False, mostrar_metricas=False)
        lay.insertWidget(lay.count() - 1, self._detalle)
        self.pila.setCurrentWidget(self.resultados)
