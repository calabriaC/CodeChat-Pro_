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
    """Colores de la aplicación (hex)."""

    FONDO = "#090B12"
    FONDO_LATERAL = "#0C0E17"
    PANEL = "#121622"
    SUPERFICIE = "#1B2030"
    SUPERFICIE_ALTA = "#232A3D"
    ROJO = "#FF334A"
    ROJO_CLARO = "#FF5A6D"
    ROJO_OSCURO = "#9F1732"
    AZUL = "#46A6FF"
    VERDE = "#19D99A"
    AMBAR = "#FFB547"
    MORADO = "#A274FF"
    TEXTO = "#F5F7FF"
    TEXTO_SECUNDARIO = "#9CA6BA"
    TEXTO_TENUE = "#6B7488"
    BORDE = "#2B3143"
    BORDE_SUAVE = "#20263A"


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
FUENTE = "Segoe UI"
FUENTE_MONO = "Cascadia Mono"
FUENTE_MONO_RESPALDO = "Consolas"


def fuente(tamano: int = 10, peso: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont(FUENTE)
    f.setPointSizeF(tamano)
    f.setWeight(peso)
    return f


def fuente_mono(tamano: int = 10) -> QFont:
    f = QFont(FUENTE_MONO)
    f.setFamilies([FUENTE_MONO, FUENTE_MONO_RESPALDO, "Courier New"])
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSizeF(tamano)
    return f


# ---------------------------------------------------------------------------
# Medidas
# ---------------------------------------------------------------------------
RADIO_TARJETA = 16
RADIO_CONTROL = 10
ANCHO_BARRA_LATERAL = 268
ANCHO_PANEL_DERECHO = 400

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
    font-family: "{FUENTE}";
    color: {C.TEXTO};
    outline: none;
}}

QMainWindow, QWidget#Raiz, QWidget#Pagina, QStackedWidget {{
    background: {C.FONDO};
}}

QToolTip {{
    background: {C.SUPERFICIE_ALTA};
    color: {C.TEXTO};
    border: 1px solid {C.BORDE};
    border-radius: 6px;
    padding: 6px 8px;
}}

/* ---------- Tipografía por rol ---------- */
QLabel {{ background: transparent; }}
QLabel#TituloPagina {{ font-size: 26px; font-weight: 700; }}
QLabel#SubtituloPagina {{ font-size: 14px; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#TituloTarjeta {{ font-size: 16px; font-weight: 700; }}
QLabel#SubtituloTarjeta {{ font-size: 12px; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#Etiqueta {{ font-size: 13px; color: {C.TEXTO}; }}
QLabel#EtiquetaSecundaria {{ font-size: 12px; color: {C.TEXTO_SECUNDARIO}; }}
QLabel#EtiquetaTenue {{ font-size: 11px; color: {C.TEXTO_TENUE}; }}
QLabel#Seccion {{
    font-size: 11px; font-weight: 700; letter-spacing: 1px;
    color: {C.TEXTO_TENUE};
}}
QLabel#ValorMetrica {{ font-size: 26px; font-weight: 700; }}
QLabel#ValorMetricaVacio {{ font-size: 22px; font-weight: 600; color: {C.TEXTO_TENUE}; }}
QLabel#Mono {{ font-family: "{FUENTE_MONO}", "{FUENTE_MONO_RESPALDO}"; font-size: 13px; }}
QLabel#Ayuda {{ font-size: 11px; color: {C.TEXTO_TENUE}; }}
QLabel#Error {{ font-size: 12px; color: {C.ROJO_CLARO}; }}

/* ---------- Contenedores ---------- */
QFrame#Tarjeta {{
    background: {C.PANEL};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: {RADIO_TARJETA}px;
}}
QFrame#TarjetaInterna {{
    background: {C.FONDO};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 12px;
}}
QFrame#EncabezadoPagina {{
    background: {C.PANEL};
    border: none;
    border-bottom: 1px solid {C.BORDE_SUAVE};
}}
QFrame#Separador {{ background: {C.BORDE_SUAVE}; border: none; max-height: 1px; min-height: 1px; }}

QFrame#BarraEntrada {{
    background: {C.PANEL};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 18px;
}}

/* ---------- Burbujas ---------- */
QFrame#BurbujaEnviada {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #A51C38, stop:1 #6E1026);
    border: 1px solid {rgba(C.ROJO, 0.45)};
    border-radius: 16px;
    border-bottom-right-radius: 5px;
}}
QFrame#BurbujaRecibida {{
    background: {C.SUPERFICIE};
    border: 1px solid {C.BORDE};
    border-radius: 16px;
    border-top-left-radius: 5px;
}}
QFrame#BurbujaSistema {{
    background: {rgba(C.ROJO, 0.10)};
    border: 1px solid {rgba(C.ROJO, 0.35)};
    border-radius: 12px;
}}
QLabel#TextoBurbuja {{ font-size: 14px; }}
QLabel#AutorBurbuja {{ font-size: 13px; font-weight: 700; }}
QLabel#HoraBurbuja {{ font-size: 11px; color: {rgba(C.TEXTO, 0.65)}; }}

QLabel#SeparadorFecha {{
    background: {C.SUPERFICIE};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 13px;
    padding: 4px 16px;
    font-size: 12px;
    color: {C.TEXTO_SECUNDARIO};
}}

/* ---------- Chips de estado ---------- */
QLabel[chip="exito"] {{
    background: {rgba(C.VERDE, 0.13)}; color: {C.VERDE};
    border: 1px solid {rgba(C.VERDE, 0.45)}; border-radius: 8px; padding: 3px 10px;
}}
QLabel[chip="error"] {{
    background: {rgba(C.ROJO, 0.13)}; color: {C.ROJO_CLARO};
    border: 1px solid {rgba(C.ROJO, 0.45)}; border-radius: 8px; padding: 3px 10px;
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
    border-radius: {RADIO_CONTROL}px;
    padding: 9px 16px;
    background: {C.SUPERFICIE};
    border: 1px solid {C.BORDE};
}}
QPushButton:hover {{ background: {C.SUPERFICIE_ALTA}; border-color: #3A4258; }}
QPushButton:pressed {{ background: {C.PANEL}; }}
QPushButton:disabled {{ color: {C.TEXTO_TENUE}; background: {C.PANEL}; border-color: {C.BORDE_SUAVE}; }}

QPushButton#BotonPrimario {{
    font-size: 14px; font-weight: 700;
    border: 1px solid {rgba(C.ROJO_CLARO, 0.6)};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C.ROJO}, stop:1 #D61F45);
    padding: 11px 18px;
}}
QPushButton#BotonPrimario:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C.ROJO_CLARO}, stop:1 #E8284F);
}}
QPushButton#BotonPrimario:pressed {{ background: {C.ROJO_OSCURO}; }}
QPushButton#BotonPrimario:disabled {{
    background: {C.SUPERFICIE}; color: {C.TEXTO_TENUE}; border-color: {C.BORDE};
}}

QPushButton#BotonEnviar {{
    border: none; border-radius: 14px; padding: 0;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {C.ROJO}, stop:1 #C8173D);
}}
QPushButton#BotonEnviar:hover {{ background: {C.ROJO_CLARO}; }}
QPushButton#BotonEnviar:pressed {{ background: {C.ROJO_OSCURO}; }}
QPushButton#BotonEnviar:disabled {{ background: {C.SUPERFICIE_ALTA}; }}

QPushButton#BotonFantasma {{
    background: transparent; border: 1px solid transparent;
    color: {C.TEXTO_SECUNDARIO}; padding: 7px 12px;
}}
QPushButton#BotonFantasma:hover {{ background: {C.SUPERFICIE}; color: {C.TEXTO}; border-color: {C.BORDE}; }}

QPushButton#Sugerencia {{
    background: {C.PANEL}; border: 1px solid {C.BORDE};
    border-radius: 16px; padding: 7px 14px; font-size: 13px; color: {C.TEXTO_SECUNDARIO};
}}
QPushButton#Sugerencia:hover {{ border-color: {rgba(C.ROJO, 0.7)}; color: {C.TEXTO}; }}

QPushButton#Segmento {{
    background: transparent; border: none; border-radius: 8px;
    padding: 7px 14px; color: {C.TEXTO_SECUNDARIO}; font-weight: 600;
}}
QPushButton#Segmento:checked {{ background: {C.SUPERFICIE_ALTA}; color: {C.TEXTO}; }}
QFrame#ContenedorSegmentos {{
    background: {C.FONDO}; border: 1px solid {C.BORDE_SUAVE}; border-radius: 10px;
}}

/* ---------- Entradas ---------- */
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {C.FONDO};
    border: 1px solid {C.BORDE};
    border-radius: {RADIO_CONTROL}px;
    padding: 7px 10px;
    font-size: 13px;
    selection-background-color: {C.ROJO_OSCURO};
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {rgba(C.ROJO, 0.85)};
}}
QLineEdit#EntradaMensaje {{
    background: {C.FONDO}; border-radius: 14px; padding: 12px 16px; font-size: 14px;
}}
QLineEdit#EntradaMensaje[alerta="true"] {{ border: 1px solid {C.ROJO}; }}
QPlainTextEdit {{ font-family: "{FUENTE_MONO}", "{FUENTE_MONO_RESPALDO}"; }}

QSpinBox, QDoubleSpinBox {{ font-family: "{FUENTE_MONO}", "{FUENTE_MONO_RESPALDO}"; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: none; }}

QComboBox {{ padding-right: 30px; font-weight: 600; }}
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
    selection-background-color: {rgba(C.ROJO, 0.30)};
    selection-color: {C.TEXTO};
}}

QSlider::groove:horizontal {{
    height: 6px; border-radius: 3px; background: {C.SUPERFICIE_ALTA};
}}
QSlider::sub-page:horizontal {{
    border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {C.ROJO_OSCURO}, stop:1 {C.ROJO});
}}
QSlider::handle:horizontal {{
    width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
    background: {C.TEXTO}; border: 3px solid {C.ROJO};
}}
QSlider::handle:horizontal:hover {{ background: #FFFFFF; border-color: {C.ROJO_CLARO}; }}

/* ---------- Visor de bits ---------- */
QTextBrowser#VisorBits {{
    background: {C.FONDO};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 8px;
    padding: 4px 6px;
    font-family: "{FUENTE_MONO}", "{FUENTE_MONO_RESPALDO}";
    font-size: 13px;
}}

/* ---------- Scroll ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C.BORDE}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3C4560; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {C.BORDE}; border-radius: 3px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- Diálogos ---------- */
QDialog {{ background: {C.FONDO}; }}
QMessageBox {{ background: {C.PANEL}; }}
QMessageBox QLabel {{ font-size: 13px; }}
"""
