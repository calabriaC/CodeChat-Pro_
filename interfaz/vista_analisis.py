"""Análisis: comparación de códigos de repetición n = 3, 5, 7."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from interfaz import servicio
from interfaz.componentes import (
    AreaDesplazable, Chip, ControlProbabilidad, EncabezadoPagina, Tarjeta, TarjetaMetrica,
    etiqueta, formato_ber, formato_p,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import C
from interfaz.grafica import GraficaBarras, GraficaBER, Serie
from interfaz.iconos import icono

COLORES_N = {3: C.AZUL, 5: C.MORADO, 7: C.VERDE}


class TarjetaCodigo(Tarjeta):
    """Resumen de un código concreto dentro de la comparación."""

    def __init__(self, n: int, parent=None):
        super().__init__(parent=parent, margen=16, espaciado=8)
        color = COLORES_N.get(n, C.ROJO)
        self.setStyleSheet(f"QFrame#Tarjeta {{ border-top: 3px solid {color}; }}")
        cab = QHBoxLayout()
        titulo = etiqueta(f"Repetición n = {n}", "TituloTarjeta")
        cab.addWidget(titulo)
        cab.addStretch(1)
        par = servicio.parametros(n)
        cab.addWidget(Chip(f"t = {par['errores_corregibles']}", "neutro"))
        self.cuerpo.addLayout(cab)
        self._rejilla = QGridLayout()
        self._rejilla.setHorizontalSpacing(12)
        self._rejilla.setVerticalSpacing(6)
        self._valores: dict[str, QLabel] = {}
        for i, (clave, nombre) in enumerate([("tasa", "Tasa R"), ("sin", "BER sin código"),
                                             ("con", "BER con código"), ("teo", "Pₑ teórico")]):
            self._rejilla.addWidget(etiqueta(nombre, "EtiquetaSecundaria"), i, 0)
            valor = etiqueta("—", "Mono")
            valor.setAlignment(Qt.AlignmentFlag.AlignRight)
            self._rejilla.addWidget(valor, i, 1)
            self._valores[clave] = valor
        self.cuerpo.addLayout(self._rejilla)

    def set_resultado(self, res: dict | None) -> None:
        if res is None:
            for v in self._valores.values():
                v.setText("—")
            return
        self._valores["tasa"].setText(f"{res['tasa']:.4f}")
        self._valores["sin"].setText(formato_ber(res["ber_sin_codigo"]))
        self._valores["con"].setText(formato_ber(res["ber_con_codigo"]))
        self._valores["teo"].setText(formato_ber(res["error_teorico"]))


class VistaAnalisis(QWidget):
    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        self._resultados: list[dict] | None = None
        self._p_resultados: float | None = None

        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        caja.addWidget(EncabezadoPagina(
            "analisis", "Análisis",
            "Compara el rendimiento de los códigos de repetición n = 3, 5 y 7 sobre el mismo canal"))
        area = AreaDesplazable(margenes=(24, 22, 18, 24))
        caja.addWidget(area, 1)
        lay = area.layout_interno

        # ---- Controles -------------------------------------------------
        controles = Tarjeta("Experimento comparativo", "actividad",
                            "Ejecuta core.experimentos sobre una secuencia aleatoria de bits")
        fila = QHBoxLayout()
        fila.setSpacing(18)
        col_p = QVBoxLayout()
        col_p.addWidget(etiqueta("Probabilidad de error (p)", "Etiqueta"))
        self.control_p = ControlProbabilidad(estado.p)
        col_p.addWidget(self.control_p)
        fila.addLayout(col_p, 3)
        col_l = QVBoxLayout()
        col_l.addWidget(etiqueta("Longitud del mensaje", "Etiqueta"))
        self.longitud = QSpinBox()
        self.longitud.setRange(1000, 200000)
        self.longitud.setSingleStep(1000)
        self.longitud.setValue(16000)
        self.longitud.setSuffix(" bits")
        self.longitud.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col_l.addWidget(self.longitud)
        fila.addLayout(col_l, 1)
        self.boton = QPushButton("  Ejecutar experimento")
        self.boton.setObjectName("BotonPrimario")
        self.boton.setIcon(icono("play", C.TEXTO, 18))
        self.boton.setIconSize(QSize(18, 18))
        self.boton.setCursor(Qt.CursorShape.PointingHandCursor)
        fila.addWidget(self.boton, 0, Qt.AlignmentFlag.AlignBottom)
        controles.cuerpo.addLayout(fila)
        self.aviso = etiqueta("", "Ayuda", ajustar=True)
        controles.cuerpo.addWidget(self.aviso)
        lay.addWidget(controles)

        # ---- Indicadores -----------------------------------------------
        indicadores = QHBoxLayout()
        indicadores.setSpacing(12)
        self.k_cap = TarjetaMetrica("Capacidad de Shannon C(p)", C.VERDE, "C = 1 − H₂(p)")
        self.k_h = TarjetaMetrica("Entropía binaria H₂(p)", C.MORADO)
        self.k_bits = TarjetaMetrica("Bits simulados por código", C.AZUL)
        self.k_mejor = TarjetaMetrica("Menor BER con código", C.ROJO)
        for k in (self.k_cap, self.k_h, self.k_bits, self.k_mejor):
            indicadores.addWidget(k)
        lay.addLayout(indicadores)

        # ---- Tarjetas por código ---------------------------------------
        codigos = QHBoxLayout()
        codigos.setSpacing(12)
        self.tarjetas_codigo = {n: TarjetaCodigo(n) for n in servicio.LONGITUDES_ANALISIS}
        for t in self.tarjetas_codigo.values():
            codigos.addWidget(t)
        lay.addLayout(codigos)

        # ---- Gráficas --------------------------------------------------
        graficas = QHBoxLayout()
        graficas.setSpacing(16)
        t1 = Tarjeta("BER frente a la tasa", "grafica", "Medición experimental frente a la fórmula teórica")
        self.grafica_ber = GraficaBER()
        self.grafica_ber.setMinimumHeight(320)
        t1.cuerpo.addWidget(self.grafica_ber)
        t2 = Tarjeta("Comparación por código", "analisis", "BER sin código, con código y teórico")
        self.grafica_barras = GraficaBarras()
        self.grafica_barras.setMinimumHeight(320)
        t2.cuerpo.addWidget(self.grafica_barras)
        graficas.addWidget(t1, 1)
        graficas.addWidget(t2, 1)
        lay.addLayout(graficas)
        lay.addStretch(1)

        self.boton.clicked.connect(self.ejecutar)
        self.control_p.valor_cambiado.connect(lambda _p: self._actualizar())
        self._actualizar()

    def ejecutar(self) -> None:
        p = self.control_p.valor()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._resultados = servicio.experimentos(p, self.longitud.value())
            self._p_resultados = p
            self._bits = self.longitud.value()
        except (ValueError, TypeError) as error:
            self._resultados = None
            self.aviso.setText(f"No se pudo ejecutar el experimento: {error}")
            self.aviso.setStyleSheet(f"color: {C.ROJO_CLARO};")
        else:
            self.aviso.setStyleSheet("")
        finally:
            QApplication.restoreOverrideCursor()
        self._actualizar()

    def _actualizar(self) -> None:
        p = self.control_p.valor()
        self.k_cap.set_valor(f"{servicio.capacidad(p):.4f}", f"p = {formato_p(p)}")
        self.k_h.set_valor(f"{servicio.entropia(p):.4f}", "bits de incertidumbre por bit")

        res = self._resultados
        vigente = res is not None and self._p_resultados == p
        if res is not None and not vigente:
            self.aviso.setText(f"Los resultados mostrados corresponden a p = {formato_p(self._p_resultados)}. "
                               "Vuelve a ejecutar el experimento para el nuevo valor.")
        elif res is not None:
            self.aviso.setText(f"Resultados para p = {formato_p(p)} con {self._bits} bits aleatorios.")
        elif not self.aviso.text().startswith("No se pudo"):
            self.aviso.setText("Aún no se ha ejecutado ningún experimento.")

        if res is None:
            self.k_bits.set_valor(None, "Ejecuta un experimento")
            self.k_mejor.set_valor(None, "Ejecuta un experimento")
            for t in self.tarjetas_codigo.values():
                t.set_resultado(None)
            vacio = "Ejecuta un experimento para ver la comparación"
            self.grafica_ber.set_datos([], mensaje_vacio=vacio)
            self.grafica_barras.set_datos([], [], mensaje_vacio=vacio)
            return

        p_res = self._p_resultados
        self.k_bits.set_valor(f"{self._bits:,}".replace(",", " "), "misma secuencia para cada n")
        mejor = min(res, key=lambda r: r["ber_con_codigo"])
        self.k_mejor.set_valor(formato_ber(mejor["ber_con_codigo"]), f"n = {mejor['n']}")
        for r in res:
            self.tarjetas_codigo[r["n"]].set_resultado(r)

        etiquetas = [f"n={r['n']}" for r in res]
        self.grafica_ber.set_datos([
            Serie("Teórico (todas las n impares)", C.AZUL, servicio.curva_teorica(p_res), discontinua=True),
            Serie("Experimental con código", C.AMBAR,
                  [(r["tasa"], r["ber_con_codigo"]) for r in res], tipo="puntos", etiquetas=etiquetas),
            Serie("Experimental sin código", C.ROJO,
                  [(1.0, sum(r["ber_sin_codigo"] for r in res) / len(res))], tipo="puntos"),
        ], vertical=(servicio.capacidad(p_res), "C"))
        self.grafica_barras.set_datos(
            [f"n = {r['n']}" for r in res],
            [("Sin código", C.ROJO, [r["ber_sin_codigo"] for r in res]),
             ("Con código", C.AMBAR, [r["ber_con_codigo"] for r in res]),
             ("Teórico", C.AZUL, [r["error_teorico"] for r in res])])
