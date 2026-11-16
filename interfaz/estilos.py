"""Paleta, tipografías y hoja de estilos (QSS) centralizadas de CodeChat Pro.

Todo color, fuente o medida visual de la interfaz debe salir de este módulo
para mantener una identidad coherente en todas las vistas.
"""

from pathlib import Path

from PySide6.QtGui import QColor, QFont


# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
class C:
    """Colores de la aplicación (hex) — identidad «Signal Lab»."""

    FONDO = "#060B16"            # fondo principal
    FONDO_VENTANA = "#0B1424"    # fondo secundario
    BARRA_SUPERIOR = "#0B1424"
    FONDO_LATERAL = "#08101E"    # barra lateral
    PANEL = "#0F192A"            # panel principal
    SUPERFICIE = "#14243B"       # superficie secundaria
    SUPERFICIE_ALTA = "#1A2A44"  # hover / elementos elevados
    CAMPO = "#142037"            # superficie de entradas
    CAMPO_OSCURO = "#0A1322"     # visores de bits y fondos hundidos
    BRILLO_BORDE = "#2E4466"     # filo superior de las tarjetas
    ROJO = "#F2384B"             # rojo principal
    ROJO_SECUNDARIO = "#C42A3D"
    ROJO_CLARO = "#FF5265"       # rojo brillante
    ROJO_OSCURO = "#9E1F31"
    AZUL_ELECTRICO = "#168BFF"   # azul eléctrico
    AZUL = "#38B6FF"             # azul luminoso (datos, información)
    VERDE = "#26D98A"            # éxito
    AMBAR = "#FFB547"            # advertencia
    ERROR = "#FF5265"            # error
    MORADO = "#B78AFF"           # violeta
    CIAN = "#00C8F8"
    TEXTO = "#E8F3FF"
    TEXTO_SECUNDARIO = "#A6B7CF"
    TEXTO_TENUE = "#6F819C"
    BORDE = "#304861"            # bordes secundarios
    BORDE_SUAVE = "#1B2A41"      # bordes sutiles


def qcolor(hex_color: str, alfa: int = 255) -> QColor:
    """Devuelve un QColor a partir de un hex y una opacidad 0‑255."""
    color = QColor(hex_color)
    color.setAlpha(alfa)
    return color


def rgba(hex_color: str, alfa: float) -> str:
    """Convierte un hex a la notación rgba() de QSS (alfa 0‑1)."""
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {int(alfa * 255)})"


# ---------------------------------------------------------------------------
# Tipografía
# ---------------------------------------------------------------------------
# Tipografía de CodeChat Pro (archivos incluidos en interfaz/recursos/fuentes, licencia SIL OFL):
#   · Sora: interfaz. ExtraBold 800 títulos y logotipo · SemiBold 600 subtítulos, tarjetas,
#     menús y botones · Regular 400 mensajes y explicaciones.
#   · JetBrains Mono: números, BER, tasas, métricas y bits (Bold 700 en los valores).
#   · STIX Two Math: fórmulas matemáticas.
# Si los archivos faltaran, Qt usa las siguientes familias de cada lista (fuentes de Windows).
FAMILIAS_UI = ["Sora", "Bahnschrift", "Segoe UI"]
FAMILIAS_MONO = ["JetBrains Mono", "Cascadia Code", "Cascadia Mono", "Consolas", "Courier New"]
FAMILIAS_MATH = ["STIX Two Math", "Cambria Math", "Times New Roman"]
FUENTE = FAMILIAS_UI[0]
FUENTE_MONO = FAMILIAS_MONO[0]
FUENTE_MONO_RESPALDO = "JetBrains Mono"
PILA_UI = ", ".join(f'"{f}"' for f in FAMILIAS_UI)
PILA_MONO = ", ".join(f'"{f}"' for f in FAMILIAS_MONO)
PILA_MATH = ", ".join(f'"{f}"' for f in FAMILIAS_MATH)


def preparar_fuentes() -> list[str]:
    """Registra las fuentes incluidas en el proyecto (requiere QApplication).

    No instala nada en el sistema: las fuentes solo existen mientras la aplicación está abierta.
    Devuelve las familias cargadas.
    """
    from PySide6.QtGui import QFontDatabase
    cargadas: list[str] = []
    carpeta = Path(__file__).resolve().parent / "recursos" / "fuentes"
    for archivo in sorted(carpeta.glob("*.ttf")):
        indice = QFontDatabase.addApplicationFont(str(archivo))
        if indice >= 0:
            cargadas += QFontDatabase.applicationFontFamilies(indice)
    return sorted(set(cargadas))


def fuente(tamano: int = 10, peso: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont(FUENTE)
    f.setFamilies(FAMILIAS_UI)
    f.setPointSizeF(tamano)
    f.setWeight(peso)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def fuente_mono(tamano: int = 10) -> QFont:
    f = QFont(FUENTE_MONO)
    f.setFamilies(FAMILIAS_MONO)
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSizeF(tamano)
    return f


# ---------------------------------------------------------------------------
# Medidas
# ---------------------------------------------------------------------------
RADIO_TARJETA = 16
RADIO_CONTROL = 8
ANCHO_BARRA_LATERAL = 284
ANCHO_PANEL_DERECHO = 440

RECURSOS = Path(__file__).resolve().parent / "recursos"


def _ruta_qss(nombre: str) -> str:
    return (RECURSOS / nombre).as_posix()


# ---------------------------------------------------------------------------
# Hoja de estilos global
# ---------------------------------------------------------------------------
def hoja_estilos() -> str:
    chevron = _ruta_qss("chevron_abajo.svg")
    return f"""
* {{
    font-family: {PILA_UI};
    color: {C.TEXTO};
    outline: none;
}}

QMainWindow, QWidget#Raiz {{
    background: {C.FONDO};
}}
QWidget#Pagina, QStackedWidget {{ background: transparent; }}

QToolTip {{
    background: {C.SUPERFICIE_ALTA};
    color: {C.TEXTO};
    border: 1px solid {C.BORDE};
    border-radius: 6px;
    padding: 7px 9px;
    font-size: 12px;
}}

/* ---------- Tipografía por rol ---------- */
QLabel {{ background: transparent; }}
QLabel#TituloPagina {{ font-size: 24px; font-weight: 800; letter-spacing: -0.4px; }}
QLabel#SubtituloPagina {{ font-size: 13px; font-weight: 600; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#TituloTarjeta {{ font-size: 16px; font-weight: 600; letter-spacing: -0.2px; }}
QLabel#SubtituloTarjeta {{ font-size: 13px; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#ValorMetricaPequeno {{ font-family: {PILA_MONO}; font-size: 20px; font-weight: 700; }}
QLabel#Etiqueta {{ font-size: 14px; color: {C.TEXTO}; }}
QLabel#EtiquetaSecundaria {{ font-size: 13px; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#EtiquetaTenue {{ font-size: 12px; color: {C.TEXTO_TENUE}; }}
QLabel#Seccion {{
    padding-top: 3px;   /* deja sitio a las tildes de las mayúsculas (Ó, Á) */
    font-size: 11px; font-weight: 700; letter-spacing: 1.4px;
    color: {C.TEXTO_TENUE};
}}
QLabel#ValorMetrica {{ font-family: {PILA_MONO}; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }}
QLabel#ValorMetricaVacio {{ font-family: {PILA_MONO}; font-size: 20px; font-weight: 600; color: {C.TEXTO_TENUE}; }}
QLabel#Mono {{ font-family: {PILA_MONO}; font-size: 13px; font-weight: 600; }}
QLabel#Ayuda {{ font-size: 12px; color: {C.TEXTO_TENUE}; }}
QLabel#Error {{ font-size: 13px; color: {C.ERROR}; }}

/* ---------- Contenedores ---------- */
QFrame#Tarjeta {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #13213A, stop:0.2 {C.PANEL}, stop:1 {C.PANEL});
    border: 1px solid {C.BORDE};
    border-top-color: {C.BRILLO_BORDE};
    border-radius: 6px;
}}
QFrame#TarjetaInterna {{
    background: {C.CAMPO_OSCURO};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 12px;
}}
QFrame#EncabezadoPagina {{
    background: transparent;
    border: none;
    margin: 14px 16px 0px 16px;
}}
QFrame#PanelPrincipal {{
    background: {C.PANEL};
    border: 1px solid {C.BORDE};
    border-radius: 16px;
}}
QFrame#AccesoRapido {{
    background: {C.PANEL};
    border: 1px solid {C.BORDE};
    border-radius: 14px;
}}
QFrame#AccesoRapido:hover {{ border-color: {rgba(C.ROJO, 0.55)}; background: #181F2E; }}
QFrame#SubTarjeta {{
    background: {C.SUPERFICIE};
    border: 1px solid {C.BORDE};
    border-left: 2px solid {rgba(C.AZUL_ELECTRICO, 0.75)};
    border-radius: 5px;
}}
QLabel#CampoLectura {{
    background: {C.CAMPO}; border: 1px solid {C.BORDE}; border-radius: 6px;
    padding: 6px 10px; font-family: {PILA_MONO}; font-size: 14px; font-weight: 700; color: {C.TEXTO};
}}
QLabel#CajaValor {{
    background: {C.CAMPO}; border: 1px solid {C.BORDE_SUAVE}; border-radius: 7px;
    padding: 5px 10px; font-family: {PILA_MONO}; font-size: 13px;
}}
QFrame#TarjetaTransmision {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10203A, stop:1 {C.PANEL});
    border: 1px solid {rgba(C.AZUL_ELECTRICO, 0.55)};
    border-radius: 8px;
}}
QFrame#PanelEtapas, QFrame#PanelEstado {{
    background: {C.CAMPO_OSCURO};
    border: 1px solid {C.BORDE};
    border-radius: 6px;
}}
QFrame#Separador {{ background: {C.BORDE_SUAVE}; border: none; max-height: 1px; min-height: 1px; }}

QFrame#BarraEntrada {{
    background: {C.PANEL};
    border: 1px solid {rgba(C.ROJO, 0.55)};
    border-radius: 8px;
}}
QFrame#BarraEntrada[foco="true"] {{ border: 1px solid {rgba(C.ROJO, 0.75)}; }}
QFrame#BarraEntrada[alerta="true"] {{ border: 1px solid {C.ERROR}; }}
QPlainTextEdit#EntradaMensaje {{
    background: {C.CAMPO}; border: 1px solid {C.BORDE}; border-radius: 8px; padding: 9px 12px;
    font-family: {PILA_UI}; font-size: 15px; color: {C.TEXTO};
}}
QPlainTextEdit#EntradaMensaje:focus {{ border: 1px solid {rgba(C.ROJO, 0.7)}; }}

/* ---------- Detalle de transmisión ---------- */
QFrame#MiniDato {{
    background: {C.CAMPO_OSCURO}; border: 1px solid {C.BORDE}; border-radius: 5px;
}}
QFrame#MiniDato:hover {{ border-color: {C.BORDE}; }}
QLabel#MiniDatoTitulo {{ font-size: 12px; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#MiniDatoValor {{ font-family: {PILA_MONO}; font-size: 17px; font-weight: 700; }}
QLabel#NumeroPaso {{
    background: {rgba(C.ROJO, 0.14)}; color: {C.ROJO_CLARO};
    border: 1px solid {rgba(C.ROJO, 0.45)}; border-radius: 10px;
    font-family: {PILA_MONO}; font-size: 11px; font-weight: 700;
}}
QLabel#TituloPaso {{ font-size: 13px; font-weight: 600; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#NoDisponible {{ font-size: 13px; font-style: italic; color: {C.TEXTO_TENUE}; }}
QPushButton#BotonDetalles {{
    background: transparent; border: 1px solid {C.BORDE}; border-radius: 9px;
    padding: 5px 11px; font-size: 12px; font-weight: 600; color: {C.TEXTO_SECUNDARIO};
}}
QPushButton#BotonDetalles:hover {{ color: {C.TEXTO}; border-color: {rgba(C.ROJO, 0.7)}; background: {rgba(C.ROJO, 0.08)}; }}
QPushButton#BotonDetalles:checked {{ color: {C.TEXTO}; border-color: {rgba(C.ROJO, 0.7)}; background: {rgba(C.ROJO, 0.14)}; }}
QPushButton#BotonDetalles:pressed {{ background: {rgba(C.ROJO, 0.20)}; }}

/* ---------- Burbujas ---------- */
QFrame#BurbujaEnviada {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1767D8, stop:1 #0B3577);
    border: 1px solid {rgba(C.AZUL, 0.85)};
    border-radius: 12px;
}}
QFrame#BurbujaRecibida {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0F1D33, stop:1 {C.PANEL});
    border: 1px solid {rgba(C.ROJO, 0.65)};
    border-left: 2px solid {C.ROJO};
    border-radius: 10px;
}}
QFrame#BurbujaSistema {{
    background: {rgba(C.ROJO, 0.10)};
    border: 1px solid {rgba(C.ROJO, 0.35)};
    border-radius: 12px;
}}
QLabel#TextoBurbuja {{ font-size: 14px; font-weight: 400; }}
QLabel#AutorBurbuja {{ font-size: 16px; font-weight: 600; color: {C.TEXTO}; }}
QLabel#HoraBurbuja {{ font-family: {PILA_MONO}; font-size: 11px; color: {rgba(C.TEXTO, 0.62)}; }}

QLabel#SeparadorFecha {{
    background: {C.CAMPO};
    border: 1px solid {C.BORDE};
    border-radius: 13px;
    padding: 4px 16px;
    font-size: 12px;
    font-weight: 600;
    color: {C.TEXTO_SECUNDARIO};
}}

/* ---------- Chips de estado ---------- */
QLabel[chip="exito"] {{
    background: {rgba(C.VERDE, 0.13)}; color: {C.VERDE};
    border: 1px solid {rgba(C.VERDE, 0.45)}; border-radius: 8px; padding: 3px 10px;
}}
QLabel[chip="error"] {{
    background: {rgba(C.ERROR, 0.13)}; color: {C.ERROR};
    border: 1px solid {rgba(C.ERROR, 0.45)}; border-radius: 8px; padding: 3px 10px;
}}
QLabel[chip="info"] {{
    background: {rgba(C.AZUL, 0.12)}; color: {C.AZUL};
    border: 1px solid {rgba(C.AZUL, 0.40)}; border-radius: 8px; padding: 3px 10px;
}}
QLabel[chip="aviso"] {{
    background: {rgba(C.AMBAR, 0.12)}; color: {C.AMBAR};
    border: 1px solid {rgba(C.AMBAR, 0.40)}; border-radius: 8px; padding: 3px 10px;
}}
QLabel[chip="neutro"] {{
    background: {C.SUPERFICIE}; color: {C.TEXTO_SECUNDARIO};
    border: 1px solid {C.BORDE}; border-radius: 8px; padding: 3px 10px;
}}

/* ---------- Botones ---------- */
QPushButton {{
    font-size: 13px;
    font-weight: 600;
    border-radius: {RADIO_CONTROL}px;
    padding: 9px 16px;
    background: {C.SUPERFICIE};
    border: 1px solid {C.BORDE};
}}
QPushButton:hover {{ background: {C.SUPERFICIE_ALTA}; border-color: #3B4560; }}
QPushButton:pressed {{ background: {C.PANEL}; border-color: {C.BORDE}; }}
QPushButton:focus {{ border-color: {rgba(C.ROJO, 0.55)}; }}
QPushButton:disabled {{ color: {C.TEXTO_TENUE}; background: {C.PANEL}; border-color: {C.BORDE_SUAVE}; }}

QPushButton#BotonPrimario {{
    font-size: 14px; font-weight: 600; letter-spacing: 0.2px;
    border: 1px solid {rgba(C.ROJO_CLARO, 0.65)};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {C.ROJO}, stop:1 {C.ROJO_SECUNDARIO});
    padding: 10px 18px;
    min-height: 20px;
}}
QPushButton#BotonPrimario:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {C.ROJO_CLARO}, stop:1 #DD2A4D);
    border-color: {rgba("#FFFFFF", 0.35)};
}}
QPushButton#BotonPrimario:pressed {{ background: {C.ROJO_OSCURO}; }}
QPushButton#BotonPrimario:disabled {{
    background: {C.SUPERFICIE}; color: {C.TEXTO_TENUE}; border-color: {C.BORDE};
}}
QPushButton#BotonPrimario::menu-indicator {{ subcontrol-position: right center; right: 10px; }}

QPushButton#BotonEnviar {{
    border: 1px solid {rgba(C.ROJO_CLARO, 0.6)}; border-radius: 10px; padding: 0 18px;
    font-size: 15px; font-weight: 700;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {C.ROJO}, stop:1 {C.ROJO_SECUNDARIO});
}}
QPushButton#BotonEnviar:hover {{ background: {C.ROJO_CLARO}; }}
QPushButton#BotonEnviar:pressed {{ background: {C.ROJO_OSCURO}; }}
QPushButton#BotonEnviar:disabled {{ background: {C.SUPERFICIE_ALTA}; border-color: {C.BORDE}; }}

QPushButton#BotonFantasma {{
    background: transparent; border: 1px solid transparent;
    color: {C.TEXTO_SECUNDARIO}; padding: 7px 12px;
}}
QPushButton#BotonFantasma:hover {{ background: {C.SUPERFICIE}; color: {C.TEXTO}; border-color: {C.BORDE}; }}
QPushButton#BotonFantasma:pressed {{ background: {C.PANEL}; }}

QPushButton#Sugerencia {{
    background: {C.PANEL}; border: 1px solid {C.BORDE};
    border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: 500;
    color: {C.TEXTO_SECUNDARIO};
}}
QPushButton#Sugerencia:hover {{ border-color: {rgba(C.ROJO, 0.7)}; color: {C.TEXTO}; background: {rgba(C.ROJO, 0.08)}; }}

QPushButton#Segmento {{
    background: transparent; border: none; border-radius: 8px;
    padding: 7px 15px; color: {C.TEXTO_SECUNDARIO}; font-weight: 600;
}}
QPushButton#Segmento:hover {{ color: {C.TEXTO}; }}
QPushButton#Segmento:checked {{
    background: {C.SUPERFICIE_ALTA}; color: {C.TEXTO};
    border-bottom: 2px solid {C.ROJO};
}}
QFrame#ContenedorSegmentos {{
    background: {C.CAMPO}; border: 1px solid {C.BORDE}; border-radius: 10px;
}}

/* ---------- Entradas ---------- */
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {C.CAMPO};
    border: 1px solid {C.BORDE};
    border-radius: {RADIO_CONTROL}px;
    padding: 8px 11px;
    font-size: 14px;
    selection-background-color: {C.ROJO_OSCURO};
}}
QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: #3B4560;
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {rgba(C.ROJO, 0.85)};
    background: #10141F;
}}
QLineEdit#EntradaMensaje {{
    background: {C.FONDO}; border-radius: 14px; padding: 12px 16px; font-size: 14px;
}}
QLineEdit#EntradaMensaje[alerta="true"] {{ border: 1px solid {C.ROJO}; }}
QPlainTextEdit {{ font-family: {PILA_MONO}; font-size: 13px; }}

QSpinBox, QDoubleSpinBox {{ font-family: {PILA_MONO}; font-weight: 600; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: none; }}

QComboBox {{ padding-right: 30px; font-family: {PILA_MONO}; font-weight: 700; }}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: center right;
    width: 28px; border: none;
}}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{
    background: {C.PANEL};
    border: 1px solid {C.BORDE};
    border-radius: 8px;
    padding: 4px;
    font-family: {PILA_MONO};
    selection-background-color: {rgba(C.ROJO, 0.30)};
    selection-color: {C.TEXTO};
}}
QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 2px 10px; border-radius: 6px; }}

QSlider {{ min-height: 22px; }}
QSlider::groove:horizontal {{
    height: 6px; border-radius: 3px; background: {C.SUPERFICIE_ALTA};
}}
QSlider::sub-page:horizontal {{
    border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {C.ROJO_OSCURO}, stop:1 {C.ROJO});
}}
QSlider::handle:horizontal {{
    width: 18px; height: 18px; margin: -7px 0; border-radius: 9px;
    background: {C.TEXTO}; border: 3px solid {C.ROJO};
}}
QSlider::handle:horizontal:hover {{ background: #FFFFFF; border-color: {C.ROJO_CLARO}; }}
QSlider::handle:horizontal:pressed {{ background: {C.ROJO_CLARO}; border-color: #FFFFFF; }}

/* ---------- Visor de bits ---------- */
QTextBrowser#VisorBits {{
    background: {C.CAMPO_OSCURO};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 8px;
    padding: 4px 6px;
    font-family: {PILA_MONO};
    font-size: 13px;
}}
QTextBrowser#VisorBits:hover {{ border-color: {C.BORDE}; }}

/* ---------- Scroll ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C.BORDE}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #46506A; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {C.BORDE}; border-radius: 3px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- Menús y diálogos ---------- */
QMenu {{
    background: {C.PANEL}; border: 1px solid {C.BORDE}; border-radius: 10px; padding: 6px;
}}
QMenu::item {{ padding: 8px 14px; border-radius: 6px; font-size: 13px; }}
QMenu::item:selected {{ background: {rgba(C.ROJO, 0.22)}; }}
QDialog {{ background: {C.FONDO}; }}
QMessageBox {{ background: {C.PANEL}; }}
QMessageBox QLabel {{ font-size: 13px; }}
"""
