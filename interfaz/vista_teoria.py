"""Teoría: conceptos del código de repetición y del canal BSC con ejemplos en vivo."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from interfaz import servicio
from interfaz.componentes import (
    AreaDesplazable, ControlProbabilidad, EncabezadoPagina, SelectorN, Tarjeta, etiqueta,
    formato_ber, formato_p, icono_label,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import C, rgba

# (símbolo, nombre, fórmula, descripción, color)
CONCEPTOS = [
    ("n", "Longitud del código", "n ∈ {1, 3, 5, …, 21}",
     "Número de bits que se transmiten por cada bit de información.", C.ROJO),
    ("k", "Bits de información", "k = 1",
     "Un código de repetición transporta un único bit de información por palabra.", C.ROJO),
    ("M", "Palabras código", "M = 2ᵏ",
     "Cantidad de palabras distintas del código: 00…0 y 11…1.", C.MORADO),
    ("d<sub>min</sub>", "Distancia mínima", "d_min = n",
     "Menor distancia de Hamming entre dos palabras código distintas.", C.MORADO),
    ("t", "Errores corregibles", "t = ⌊(d_min − 1) / 2⌋",
     "Máximo de bits alterados por bloque que la decodificación por mayoría siempre corrige.", C.ROJO),
    ("R", "Tasa del código", "R = k / n",
     "Fracción de cada bloque que es información útil. Más protección implica menor tasa.", C.AZUL),
    ("p", "Canal binario simétrico", "P(bit invertido) = p,  0 ≤ p ≤ 0.5",
     "Cada bit se invierte de forma independiente con probabilidad p.", C.AMBAR),
    ("maj", "Decodificación por mayoría", "bit = 1 si #unos > #ceros",
     "Cada bloque de n bits se decide por el valor que más se repite.", C.AZUL),
    ("BER", "Tasa de error de bits", "BER = bits erróneos / bits totales",
     "Se mide comparando los bits originales con los recuperados.", C.AMBAR),
    ("P<sub>e</sub>", "Error residual teórico", "Pₑ = Σᵢ₌ₜ₊₁ⁿ C(n, i)·pⁱ·(1 − p)ⁿ⁻ⁱ",
     "Probabilidad de que más de t bits del bloque se inviertan y la mayoría falle.", C.ROJO),
    ("H<sub>2</sub>", "Entropía binaria", "H₂(p) = −p·log₂p − (1 − p)·log₂(1 − p)",
     "Incertidumbre que introduce el canal por cada bit transmitido.", C.MORADO),
    ("C", "Capacidad de Shannon", "C = 1 − H₂(p)",
     "Máxima tasa a la que se puede transmitir con error arbitrariamente pequeño.", C.VERDE),
]


class TarjetaConcepto(QFrame):
    def __init__(self, simbolo, nombre, formula, descripcion, color, parent=None):
        super().__init__(parent)
        self.setObjectName("Tarjeta")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 16, 18, 16)
        caja.setSpacing(8)
        cab = QHBoxLayout()
        cab.setSpacing(14)
        simbolo_lbl = QLabel(simbolo)
        simbolo_lbl.setTextFormat(Qt.TextFormat.RichText)
        simbolo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        simbolo_lbl.setFixedSize(54, 54)
        tam = 22 if len(simbolo) <= 2 else 16
        simbolo_lbl.setStyleSheet(
            f"background: {rgba(color, 0.12)}; border: 1px solid {rgba(color, 0.45)};"
            f" border-radius: 14px; color: {color}; font-size: {tam}px; font-weight: 800;"
            " font-style: italic;")
        cab.addWidget(simbolo_lbl)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(etiqueta(nombre, "TituloTarjeta", ajustar=True))
        self.ejemplo = etiqueta("", "EtiquetaSecundaria", ajustar=True)
        textos.addWidget(self.ejemplo)
        cab.addLayout(textos, 1)
        caja.addLayout(cab)
        formula_lbl = etiqueta(formula, "Mono", ajustar=True)
        formula_lbl.setStyleSheet(
            f"background: {C.FONDO}; border: 1px solid {C.BORDE_SUAVE}; border-radius: 8px;"
            f" padding: 8px 10px; color: {C.TEXTO};")
        caja.addWidget(formula_lbl)
        caja.addWidget(etiqueta(descripcion, "EtiquetaSecundaria", ajustar=True))
        caja.addStretch(1)

    def set_ejemplo(self, texto: str) -> None:
        self.ejemplo.setText(texto)


class Flujo(QWidget):
    """Diagrama del recorrido de un mensaje."""

    PASOS = [("texto", "Texto"), ("binario", "Bits UTF‑8"), ("capas", "Codificador"),
             ("antena", "Canal BSC"), ("escudo", "Decodificador"), ("exito", "Texto recuperado")]

    def __init__(self, parent=None):
        super().__init__(parent)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(6)
        for i, (ic, nombre) in enumerate(self.PASOS):
            paso = QFrame()
            paso.setObjectName("TarjetaInterna")
            caja = QVBoxLayout(paso)
            caja.setContentsMargins(10, 12, 10, 12)
            caja.setSpacing(6)
            color = C.ROJO if ic == "antena" else (C.VERDE if ic == "exito" else C.TEXTO)
            caja.addWidget(icono_label(ic, color, 22), 0, Qt.AlignmentFlag.AlignHCenter)
            lbl = etiqueta(nombre, "EtiquetaSecundaria")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caja.addWidget(lbl)
            fila.addWidget(paso, 1)
            if i < len(self.PASOS) - 1:
                fila.addWidget(icono_label("flecha_derecha", C.TEXTO_TENUE, 16))


class VistaTeoria(QWidget):
    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__(parent)
        self.estado = estado
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        caja.addWidget(EncabezadoPagina(
            "teoria", "Teoría",
            "Conceptos clave de los códigos de repetición y del canal binario simétrico"))
        area = AreaDesplazable(margenes=(24, 22, 18, 24))
        caja.addWidget(area, 1)
        lay = area.layout_interno

        flujo = Tarjeta("Cómo viaja un mensaje", "flecha_derecha")
        flujo.cuerpo.addWidget(Flujo())
        lay.addWidget(flujo)

        ejemplo = Tarjeta("Valores de ejemplo", "chispa",
                          "Calculados en vivo por el núcleo matemático; comparten la configuración del chat")
        fila = QHBoxLayout()
        fila.setSpacing(16)
        fila.addWidget(etiqueta("n", "Etiqueta"))
        self.selector_n = SelectorN(estado.n)
        fila.addWidget(self.selector_n)
        fila.addSpacing(18)
        fila.addWidget(etiqueta("p", "Etiqueta"))
        self.control_p = ControlProbabilidad(estado.p)
        fila.addWidget(self.control_p, 1)
        ejemplo.cuerpo.addLayout(fila)
        lay.addWidget(ejemplo)

        rejilla = QGridLayout()
        rejilla.setSpacing(14)
        self.tarjetas: dict[str, TarjetaConcepto] = {}
        for i, (simbolo, nombre, formula, desc, color) in enumerate(CONCEPTOS):
            t = TarjetaConcepto(simbolo, nombre, formula, desc, color)
            self.tarjetas[nombre] = t
            rejilla.addWidget(t, i // 3, i % 3)
        for col in range(3):
            rejilla.setColumnStretch(col, 1)
        lay.addLayout(rejilla)
        lay.addStretch(1)

        self.selector_n.n_cambiado.connect(estado.establecer_n)
        self.control_p.valor_cambiado.connect(estado.establecer_p)
        estado.configuracion_cambiada.connect(self._sincronizar)
        estado.transmision_registrada.connect(lambda _r: self._actualizar())
        estado.historial_limpiado.connect(self._actualizar)
        self._actualizar()

    def _sincronizar(self, n: int, p: float) -> None:
        self.selector_n.set_n(n)
        if abs(self.control_p.valor() - p) > 1e-9:
            self.control_p.set_valor(p)
        self._actualizar()

    def _actualizar(self) -> None:
        n, p = self.estado.n, self.estado.p
        par = servicio.parametros(n)
        ps = formato_p(p)
        historial = self.estado.historial
        ber = (f"Última medición: {formato_ber(historial[-1].ber_con_codigo)} "
               f"(n = {historial[-1].n}, p = {formato_p(historial[-1].p)})"
               if historial else "Se mide al transmitir un mensaje")
        ejemplos = {
            "Longitud del código": f"Actual: n = {par['n']}",
            "Bits de información": f"Actual: k = {par['k']}",
            "Palabras código": f"Actual: M = {par['M']}",
            "Distancia mínima": f"Actual: d_min = {par['distancia_minima']} "
                                f"(detecta {par['errores_detectables']})",
            "Errores corregibles": f"Actual: t = {par['errores_corregibles']}",
            "Tasa del código": f"Actual: R = {par['tasa']:.4f}",
            "Canal binario simétrico": f"Actual: p = {ps}",
            "Decodificación por mayoría": f"Bloques de {n} bit(s)",
            "Tasa de error de bits": ber,
            "Error residual teórico": f"n = {n}, p = {ps}: Pₑ = {formato_ber(servicio.error_residual(n, p))}",
            "Entropía binaria": f"p = {ps}: H₂ = {servicio.entropia(p):.4f}",
            "Capacidad de Shannon": f"p = {ps}: C = {servicio.capacidad(p):.4f}",
        }
        for nombre, texto in ejemplos.items():
            self.tarjetas[nombre].set_ejemplo(texto)
