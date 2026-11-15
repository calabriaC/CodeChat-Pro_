"""Iconografía vectorial de la interfaz.

Los iconos se definen como SVG de trazo (24×24) y se colorean en tiempo de
ejecución, de modo que no se necesitan archivos de imagen externos.
"""

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from interfaz.estilos import C

_ICONOS = {
    "chat": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "laboratorio": (
        '<path d="M9 3h6"/><path d="M10 3v6.5L4.6 18.4A1.7 1.7 0 0 0 6.1 21h11.8'
        'a1.7 1.7 0 0 0 1.5-2.6L14 9.5V3"/><path d="M7 15h10"/>'
    ),
    "analisis": (
        '<path d="M3 3v18h18"/><path d="M8 17v-3"/><path d="M12 17V9"/>'
        '<path d="M16 17v-5"/><path d="M20 17V6"/>'
    ),
    "teoria": (
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
    ),
    "historial": (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
        '<path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>'
    ),
    "ajustes": (
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0'
        'l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51'
        'a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08'
        'a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18'
        'a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39'
        'a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09'
        'a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25'
        'a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>'
    ),
    "enviar": (
        '<path d="M14.54 21.69a.5.5 0 0 0 .94-.03l6.5-19a.5.5 0 0 0-.64-.63l-19 6.5'
        'a.5.5 0 0 0-.02.93l7.93 3.18a2 2 0 0 1 1.11 1.11z"/><path d="m21.85 2.15-10.94 10.94"/>'
    ),
    "antena": (
        '<path d="M4.9 16.1C1 12.2 1 5.8 4.9 1.9"/><path d="M7.8 4.7a6.14 6.14 0 0 0-.8 7.5"/>'
        '<circle cx="12" cy="9" r="2"/><path d="M16.2 4.8c2 2 2.26 5.11.8 7.47"/>'
        '<path d="M19.1 1.9a9.96 9.96 0 0 1 0 14.1"/><path d="M9.5 18h5"/>'
        '<path d="m8 22 4-11 4 11"/>'
    ),
    "exito": '<circle cx="12" cy="12" r="10"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "fallo": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "alerta": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "capas": (
        '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>'
    ),
    "bot": (
        '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/>'
        '<path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>'
    ),
    "play": '<path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5z" fill="{c}"/>',
    "aleatorio": (
        '<path d="m18 14 4 4-4 4"/><path d="m18 2 4 4-4 4"/>'
        '<path d="M2 18h1.97a4 4 0 0 0 3.3-1.7l5.45-8.6a4 4 0 0 1 3.3-1.7H22"/>'
        '<path d="M2 6h1.97a4 4 0 0 1 3.3 1.7l.53.84"/><path d="M22 18h-6a4 4 0 0 1-3.3-1.8l-.36-.55"/>'
    ),
    "papelera": (
        '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'
        '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
    ),
    "grafica": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "actividad": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "reloj": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "doble_check": '<path d="M18 6 7 17l-5-5"/><path d="m22 10-7.5 7.5L13 16"/>',
    "binario": (
        '<rect x="14" y="14" width="4" height="6" rx="2"/><rect x="6" y="4" width="4" height="6" rx="2"/>'
        '<path d="M6 20h4"/><path d="M14 10h4"/><path d="M6 14h2v6"/><path d="M14 4h2v6"/>'
    ),
    "expandir": (
        '<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/>'
    ),
    "chispa": (
        '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>'
        '<path d="M19 15v4"/><path d="M17 17h4"/>'
    ),
    "flecha_derecha": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "flecha_abajo": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "copiar": '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "escudo": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "texto": '<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>',
}


def _svg(nombre: str, color: str, trazo: float) -> bytes:
    cuerpo = _ICONOS[nombre].replace("{c}", color)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{trazo}" stroke-linecap="round" '
        f'stroke-linejoin="round">{cuerpo}</svg>'
    ).encode("utf-8")


@lru_cache(maxsize=256)
def pixmap(nombre: str, color: str = C.TEXTO, tamano: int = 20,
           trazo: float = 2.0, escala: float = 2.0) -> QPixmap:
    """Renderiza un icono a QPixmap nítido en pantallas de alta densidad."""
    lado = int(tamano * escala)
    imagen = QPixmap(lado, lado)
    imagen.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(_svg(nombre, color, trazo)))
    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(pintor, QRectF(0, 0, lado, lado))
    pintor.end()
    imagen.setDevicePixelRatio(escala)
    return imagen


def icono(nombre: str, color: str = C.TEXTO, tamano: int = 20, trazo: float = 2.0) -> QIcon:
    return QIcon(pixmap(nombre, color, tamano, trazo))
