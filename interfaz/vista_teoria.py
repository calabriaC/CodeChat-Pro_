"""Teoría: conceptos del código de repetición y del canal BSC con ejemplos en vivo."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFontDatabase, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from interfaz import servicio
from interfaz.componentes import (
    AreaDesplazable, ControlProbabilidad, ControlSegmentado, EncabezadoPagina, FlujoLayout,
    SelectorN, Tarjeta, etiqueta, formato_ber, formato_p, icono_label, repulir,
)
from interfaz.estado import EstadoApp
from interfaz.estilos import C, FAMILIAS_MATH, FAMILIAS_MONO, FAMILIAS_UI, FUENTE_MONO_RESPALDO, qcolor, rgba
from interfaz.ilustraciones import Ilustracion, tiene_ilustracion
from interfaz.marcos_globales import pintar_nivel2
from interfaz.iconos import icono

# (clave, símbolo, nombre, fórmula en HTML, descripción, color)
CONCEPTOS = [
    ("n", "<i>n</i>", "Longitud del código", "<i>n</i> ∈ {1, 2, 3, …, 21}",
     "Número de bits que se transmiten por cada bit de información. Con n impar la mayoría nunca "
     "empata; con n par un bloque puede quedar empatado y su bit se marca como «?».", C.ROJO),
    ("k", "<i>k</i>", "Dimensión", "<i>k</i> = 1",
     "Bits de información por palabra código: el código de repetición transporta un único bit.", C.ROJO),
    ("M", "<i>M</i>", "Número de palabras código", "<i>M</i> = 2<sup><i>k</i></sup> = 2",
     "Las dos palabras posibles son 00…0 y 11…1.", C.MORADO),
    ("dmin", "<i>d</i><sub>min</sub>", "Distancia mínima", "<i>d</i><sub>min</sub> = <i>n</i>",
     "Menor distancia de Hamming entre dos palabras código distintas: 00…0 y 11…1 difieren en las n posiciones.",
     C.MORADO),
    ("det", "<i>d</i><sub>min</sub>−1", "Capacidad de detección",
     "<i>e</i><sub>det</sub> = <i>d</i><sub>min</sub> − 1 = <i>n</i> − 1",
     "Cualquier patrón de hasta n − 1 errores convierte la palabra en algo que no es una palabra "
     "código, así que puede detectarse. Detectar no es corregir: saber que hay errores no indica "
     "cuál era el bit. La decodificación por mayoría de esta aplicación corrige; no señala errores.",
     C.AMBAR),
    ("t", "<i>t</i>", "Capacidad de corrección",
     "<i>t</i> = ⌊(<i>d</i><sub>min</sub> − 1) / 2⌋",
     "Se corrige con certeza cualquier patrón de hasta t errores por bloque. En el código de "
     "repetición con n impar, con t + 1 o más errores la mayoría elige el bit equivocado.", C.ROJO),
    ("R", "<i>R</i>", "Tasa del código", "<i>R</i> = <i>k</i> / <i>n</i> = 1 / <i>n</i>",
     "Fracción de cada bloque que es información útil. Más repeticiones dan más protección y menor tasa.",
     C.AZUL),
    ("p", "<i>p</i>", "Canal binario simétrico (BSC)",
     "P(<i>y</i> ≠ <i>x</i>) = <i>p</i>,  0 ≤ <i>p</i> ≤ 0.5",
     "Cada bit se invierte de forma independiente con probabilidad p, sea 0 o 1.", C.AMBAR),
    ("maj", "maj", "Decodificación por mayoría",
     "<i>x̂</i> = 1 si #unos &gt; #ceros;  <i>x̂</i> = 0 si #ceros &gt; #unos;  <i>x̂</i> = ? si empatan",
     "Cada bloque de n bits recibidos se decide por el valor más frecuente. Con n impar no hay "
     "empates; con n par, si hay tantos unos como ceros, el bit queda ambiguo («?»): no es un "
     "acierto ni se cuenta como bit incorrecto.",
     C.AZUL),
    ("BER", "BER", "Tasa de error de bits",
     "BER = bits erróneos / bits comparados",
     "Es una medición experimental: estima la probabilidad de error, pero varía entre ejecuciones.",
     C.AMBAR),
    ("Pe", "<i>P</i><sub>e</sub>", "Probabilidad residual teórica",
     "<i>P</i><sub>e</sub> = Σ<sub><i>i</i>=<i>t</i>+1</sub><sup><i>n</i></sup> "
     "C(<i>n</i>, <i>i</i>) · <i>p</i><sup><i>i</i></sup> · (1 − <i>p</i>)<sup><i>n</i>−<i>i</i></sup>",
     "Probabilidad de que más de t bits del bloque se inviertan y la mayoría falle. Es una "
     "predicción, no el resultado de una transmisión concreta.", C.ROJO),
    ("H2", "<i>H</i><sub>2</sub>", "Entropía binaria",
     "<i>H</i><sub>2</sub>(<i>p</i>) = −<i>p</i> log<sub>2</sub> <i>p</i> − (1 − <i>p</i>) "
     "log<sub>2</sub>(1 − <i>p</i>)",
     "Incertidumbre, en bits, que introduce el canal sobre cada bit transmitido.", C.MORADO),
    ("C", "<i>C</i>", "Capacidad de Shannon", "<i>C</i> = 1 − <i>H</i><sub>2</sub>(<i>p</i>)",
     "Máxima tasa a la que existen códigos con probabilidad de error tan pequeña como se quiera. "
     "Es un límite teórico: no garantiza ausencia de errores en una transmisión concreta, y los "
     "códigos de repetición solo reducen el error haciendo R → 0.", C.VERDE),
]


def _familias(preferidas: list[str], respaldo: list[str]) -> str:
    """Pila de fuentes CSS con las preferidas solo si están instaladas (sin errores si faltan)."""
    instaladas = set(QFontDatabase.families())
    lista = [f for f in preferidas if f in instaladas] + list(respaldo)
    return ", ".join(f"'{f}'" for f in dict.fromkeys(lista))


class TarjetaConcepto(QFrame):
    """Tarjeta de un concepto: ilustración, título, valor actual, fórmula y explicación."""

    def __init__(self, simbolo, nombre, formula, descripcion, color, parent=None, clave: str | None = None):
        super().__init__(parent)
        self.setObjectName("Tarjeta")
        self.setProperty("acento", color)
        self._color = color
        self._hover = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ui = _familias([], FAMILIAS_UI)          # Sora
        mono = _familias([], FAMILIAS_MONO)      # JetBrains Mono
        matematica = _familias([], FAMILIAS_MATH)   # STIX Two Math
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 12, 18, 18)
        caja.setSpacing(9)

        # 1. Ilustración conceptual (o el símbolo, si el concepto no tiene dibujo)
        if clave and tiene_ilustracion(clave):
            # Sin halo propio: el resplandor lo pinta la tarjeta (uno solo, suave).
            self.ilustracion = Ilustracion(clave, alto=112, halo=False)
            caja.addWidget(self.ilustracion)
        else:
            self.ilustracion = None
            simbolo_lbl = QLabel(simbolo)
            simbolo_lbl.setTextFormat(Qt.TextFormat.RichText)
            simbolo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            simbolo_lbl.setFixedHeight(112)
            simbolo_lbl.setStyleSheet(f"color: {color}; font-size: 34px; font-family: {matematica};")
            caja.addWidget(simbolo_lbl)

        # 2. Título
        titulo = etiqueta(nombre, "TituloTarjeta", ajustar=True)
        titulo.setStyleSheet(f"font-family: {ui}; font-size: 17px; font-weight: 600; color: {C.TEXTO};")
        caja.addWidget(titulo)
        subrayado = QFrame()            # línea roja corta bajo el título (referencia)
        subrayado.setFixedSize(38, 3)
        subrayado.setStyleSheet(f"background: {C.ROJO}; border-radius: 1px;")
        caja.addWidget(subrayado)

        # 3. Valor actual (dinámico, calculado por el núcleo)
        self.ejemplo = etiqueta("", "EtiquetaSecundaria", ajustar=True)
        self.ejemplo.setStyleSheet(f"font-family: {mono}; font-size: 12px; font-weight: 700; color: {color};"
                                   f" background: {rgba(color, 0.08)}; border: 1px solid {rgba(color, 0.28)};"
                                   " border-radius: 6px; padding: 4px 8px;")
        caja.addWidget(self.ejemplo)

        # 4. Fórmula
        formula_lbl = QLabel(formula)
        formula_lbl.setObjectName("Formula")
        formula_lbl.setProperty("acento", color)
        formula_lbl.setTextFormat(Qt.TextFormat.RichText)
        formula_lbl.setWordWrap(True)
        formula_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        formula_lbl.setStyleSheet(
            f"background: {C.CAMPO_OSCURO}; border: 1px solid {C.BORDE_SUAVE}; border-radius: 8px;"
            f" border-left: 3px solid {rgba(color, 0.75)};"
            f" padding: 9px 12px; color: {C.TEXTO}; font-size: 17px; font-family: {matematica};")
        caja.addWidget(formula_lbl)

        # 5. Explicación
        explicacion = etiqueta(descripcion, "EtiquetaSecundaria", ajustar=True)
        explicacion.setStyleSheet(f"font-family: {ui}; font-size: 12.5px; font-weight: 400;"
                                  f" color: {C.TEXTO_SECUNDARIO};")
        caja.addWidget(explicacion)
        caja.addStretch(1)

    def set_ejemplo(self, texto: str) -> None:
        self.ejemplo.setText(texto)

    # ---- marco y efecto al pasar el cursor -----------------------------
    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        # Tarjeta común de la aplicación (marcos_globales.pintar_nivel2), realzada con el cursor
        pintar_nivel2(p, r, "#0F1D33", "#22406A", realce=1.0 if self._hover else 0.25)
        if self.ilustracion is not None:
            zona = QRectF(self.ilustracion.geometry())
            radio = min(zona.width() * 0.32, 120.0)
            halo = QRadialGradient(zona.center(), radio)
            halo.setColorAt(0, qcolor(self._color, 34 if self._hover else 18))
            halo.setColorAt(1, qcolor(self._color, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawEllipse(zona.center(), radio, zona.height() * 0.55)
        p.end()


class RejillaConceptos(QWidget):
    """Rejilla adaptable: 3 columnas si hay espacio, 2 en ventanas medianas, 1 en estrechas."""

    def __init__(self, tarjetas: list[QWidget], parent=None):
        super().__init__(parent)
        self._tarjetas = tarjetas
        self._columnas = 0
        self._rejilla = QGridLayout(self)
        self._rejilla.setContentsMargins(0, 0, 0, 0)
        self._rejilla.setSpacing(16)
        self._colocar(3)

    def _colocar(self, columnas: int) -> None:
        if columnas == self._columnas:
            return
        self._columnas = columnas
        for t in self._tarjetas:
            self._rejilla.removeWidget(t)
        for c in range(3):
            self._rejilla.setColumnStretch(c, 1 if c < columnas else 0)
        for i, t in enumerate(self._tarjetas):
            self._rejilla.addWidget(t, i // columnas, i % columnas)

    def resizeEvent(self, event):
        ancho = event.size().width()
        self._colocar(3 if ancho >= 960 else 2 if ancho >= 620 else 1)
        super().resizeEvent(event)


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


class EjemploMayoria(Tarjeta):
    """Ejemplo interactivo: un bit, su bloque de n repeticiones y la decisión por mayoría.

    La codificación, el canal y la decisión los realiza el núcleo (core/).
    """

    def __init__(self, estado: EstadoApp, parent=None):
        super().__init__("Ejemplo interactivo: decodificación por mayoría", "escudo",
                         "Haz clic en los bits recibidos para invertirlos o aplica el canal BSC con el p actual",
                         parent=parent)
        self.estado = estado
        fila = QHBoxLayout()
        fila.setSpacing(12)
        fila.addWidget(etiqueta("Bit de información:", "Etiqueta"))
        self.selector_bit = ControlSegmentado(["0", "1"])
        fila.addWidget(self.selector_bit)
        fila.addStretch(1)
        self.boton_canal = QPushButton("  Aplicar canal BSC")
        self.boton_canal.setIcon(icono("antena", C.TEXTO, 16))
        self.boton_canal.setCursor(Qt.CursorShape.PointingHandCursor)
        fila.addWidget(self.boton_canal)
        self.boton_reiniciar = QPushButton("  Restablecer")
        self.boton_reiniciar.setIcon(icono("aleatorio", C.TEXTO, 16))
        self.boton_reiniciar.setCursor(Qt.CursorShape.PointingHandCursor)
        fila.addWidget(self.boton_reiniciar)
        self.cuerpo.addLayout(fila)

        self.codificado_lbl = etiqueta("", "EtiquetaSecundaria")
        self.cuerpo.addWidget(self.codificado_lbl)
        self.contenedor_celdas = QWidget()
        self.celdas_layout = FlujoLayout(self.contenedor_celdas, espaciado=6)
        self.cuerpo.addWidget(self.contenedor_celdas)
        self.resultado = QLabel()
        self.resultado.setTextFormat(Qt.TextFormat.RichText)
        self.resultado.setWordWrap(True)
        self.resultado.setObjectName("Etiqueta")
        self.cuerpo.addWidget(self.resultado)

        self._celdas: list[QPushButton] = []
        self._codificado = ""
        self.selector_bit.cambiado.connect(lambda _i: self.reiniciar())
        self.boton_reiniciar.clicked.connect(self.reiniciar)
        self.boton_canal.clicked.connect(self.aplicar_canal)
        estado.configuracion_cambiada.connect(lambda _n, _p: self.reiniciar())
        self.reiniciar()

    def reiniciar(self) -> None:
        n = self.estado.n
        bit = str(self.selector_bit.indice())
        self._codificado = servicio.codificar(bit, n)
        for celda in self._celdas:
            self.celdas_layout.removeWidget(celda)
            celda.deleteLater()
        self._celdas = []
        for i in range(n):
            b = QPushButton()
            b.setCheckable(True)
            b.setFixedSize(36, 40)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(f"Posición {i + 1}: clic para invertir este bit")
            b.toggled.connect(lambda _c, b=b: (self._pintar_celda(b), self._evaluar()))
            self.celdas_layout.addWidget(b)
            self._celdas.append(b)
        self.codificado_lbl.setText(f"Palabra enviada (n = {n}): {self._codificado}")
        for b in self._celdas:
            self._pintar_celda(b)
        self.boton_canal.setText(f"  Aplicar canal BSC (p = {formato_p(self.estado.p)})")
        self._evaluar()

    def aplicar_canal(self) -> None:
        recibido = servicio.canal_bsc(self._codificado, self.estado.p)
        for b, enviado, llegado in zip(self._celdas, self._codificado, recibido):
            b.blockSignals(True)
            b.setChecked(enviado != llegado)
            b.blockSignals(False)
            self._pintar_celda(b)
        self._evaluar()

    def _recibido(self) -> str:
        return "".join(("1" if e == "0" else "0") if b.isChecked() else e
                       for b, e in zip(self._celdas, self._codificado))

    def _pintar_celda(self, b: QPushButton) -> None:
        i = self._celdas.index(b) if b in self._celdas else 0
        enviado = self._codificado[i] if i < len(self._codificado) else "0"
        invertido = b.isChecked()
        b.setText(("1" if enviado == "0" else "0") if invertido else enviado)
        fondo, borde, color = ((rgba(C.ERROR, 0.18), C.ERROR, C.ERROR) if invertido
                               else (C.CAMPO, C.BORDE, C.TEXTO))
        b.setStyleSheet(f"QPushButton {{ background: {fondo}; border: 1px solid {borde};"
                        f" border-radius: 8px; color: {color}; font-size: 16px; font-weight: 700;"
                        f" font-family: '{FUENTE_MONO_RESPALDO}'; padding: 0; }}")

    def _evaluar(self) -> None:
        if not self._celdas:
            return
        n, t = self.estado.n, servicio.parametros(self.estado.n)["errores_corregibles"]
        recibido = self._recibido()
        decision = servicio.decodificar(recibido, n)
        original = self._codificado[0]
        errores = sum(b.isChecked() for b in self._celdas)
        unos = recibido.count("1")
        acierto = decision == original
        if decision == "?":
            color, veredicto = C.AMBAR, "ambigua: empate"
            explicacion = (f"{errores} &gt; t = {t}, y el bloque quedó con {unos} unos y {n - unos} "
                           "ceros: no hay mayoría, el bit no puede decidirse.")
        else:
            color = C.VERDE if acierto else C.ERROR
            veredicto = "correcta" if acierto else "incorrecta"
            explicacion = (f"{errores} ≤ t = {t}: la mayoría sigue representando el bit enviado."
                           if errores <= t else
                           f"{errores} &gt; t = {t}: la mayoría queda del lado equivocado.")
        self.resultado.setText(
            f"Recibido <b style=\"font-family:'{FUENTE_MONO_RESPALDO}';\">{recibido}</b> → "
            f"{unos} uno(s) y {n - unos} cero(s) → decisión <b>{decision}</b> "
            f"<span style='color:{color};'>({veredicto})</span>.<br>"
            f"<span style='color:{C.TEXTO_SECUNDARIO};'>Bits invertidos: {explicacion}</span>")


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

        lay.addWidget(EjemploMayoria(estado))

        self.tarjetas: dict[str, TarjetaConcepto] = {}
        for clave, simbolo, nombre, formula, desc, color in CONCEPTOS:
            self.tarjetas[clave] = TarjetaConcepto(simbolo, nombre, formula, desc, color, clave=clave)
        lay.addWidget(RejillaConceptos(list(self.tarjetas.values())))
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
        if historial:
            u = historial[-1]
            ber = (f"Última medición: {formato_ber(u.ber_con_codigo)} "
                   f"(n = {u.n}, p = {formato_p(u.p)})")
        else:
            ber = "Se mide al transmitir un mensaje"
        ejemplos = {
            "n": f"Actual: n = {par['n']}",
            "k": f"Actual: k = {par['k']}",
            "M": f"Actual: M = {par['M']}",
            "dmin": f"Actual: d_min = {par['distancia_minima']}",
            "det": f"Actual: detecta hasta {par['errores_detectables']} error(es)",
            "t": f"Actual: corrige hasta t = {par['errores_corregibles']} error(es)",
            "R": f"Actual: R = {par['tasa']:.4f}",
            "p": f"Actual: p = {ps}",
            "maj": f"Bloques de {n} bit(s)",
            "BER": ber,
            "Pe": (f"n = {n}, p = {ps}: Pₑ = {formato_ber(servicio.error_residual(n, p))}"
                   if n % 2 else f"N/D para n = {n}: la fórmula del núcleo requiere n impar"),
            "H2": f"p = {ps}: H₂ = {servicio.entropia(p):.4f}",
            "C": f"p = {ps}: C = {servicio.capacidad(p):.4f}",
        }
        for clave, texto in ejemplos.items():
            self.tarjetas[clave].set_ejemplo(texto)
