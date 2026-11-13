
import matplotlib.pyplot as plt

from core.experimentos import ejecutar_experimentos
from core.matematicas import capacidad_shannon


def graficar_error_vs_tasa(mensaje, p):
    """Compara BER experimental y teórico frente a la tasa."""

    resultados = ejecutar_experimentos(mensaje, p)

    tasas = [r["tasa"] for r in resultados]
    ber_experimental = [r["ber_con_codigo"] for r in resultados]
    ber_teorico = [r["error_teorico"] for r in resultados]

    capacidad = capacidad_shannon(p)

    plt.figure(figsize=(9, 5))

    plt.plot(
        tasas,
        ber_experimental,
        "o-",
        label="BER experimental"
    )

    plt.plot(
        tasas,
        ber_teorico,
        "s--",
        label="BER teórico"
    )

    plt.axvline(
        x=capacidad,
        linestyle=":",
        label=f"Capacidad de Shannon = {capacidad:.3f}"
    )

    for resultado in resultados:
        plt.annotate(
            f"n={resultado['n']}",
            (
                resultado["tasa"],
                resultado["error_teorico"]
            ),
            xytext=(6, 8),
            textcoords="offset points"
        )

    plt.xlabel("Tasa del código (R)")
    plt.ylabel("Tasa de error de bits (BER)")
    plt.title(f"Error vs tasa | Canal BSC con p={p}")

    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    mensaje = "10110010" * 2000
    graficar_error_vs_tasa(mensaje, 0.10)
