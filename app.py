"""Punto de entrada de la interfaz gráfica de CodeChat Pro.

Uso:
    python app.py
"""

import sys
from pathlib import Path

# Garantiza que los paquetes `core` e `interfaz` sean importables
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from interfaz.ventana_principal import VentanaPrincipal, configurar_aplicacion  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    configurar_aplicacion(app)
    ventana = VentanaPrincipal()
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
