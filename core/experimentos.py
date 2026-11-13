
from core.simulador import simular_transmision
from core.matematicas import probabilidad_error_residual


def ejecutar_experimentos(mensaje, p, longitudes=(3, 5, 7)):
    """Compara el rendimiento de distintas longitudes de repetición."""

    resultados = []

    for n in longitudes:
        simulacion = simular_transmision(mensaje, n, p)

        resultados.append({
            "n": n,
            "tasa": simulacion["tasa"],
            "ber_sin_codigo": simulacion["ber_sin_codigo"],
            "ber_con_codigo": simulacion["ber_con_codigo"],
            "error_teorico": probabilidad_error_residual(n, p)
        })

    return resultados


if __name__ == "__main__":
    mensaje = "10110010" * 2000
    p = 0.10

    resultados = ejecutar_experimentos(mensaje, p)

    print("COMPARACIÓN DE CÓDIGOS DE REPETICIÓN")
    print("-" * 70)

    for resultado in resultados:
        print(
            f"n={resultado['n']} | "
            f"R={resultado['tasa']:.4f} | "
            f"BER sin código={resultado['ber_sin_codigo']:.4%} | "
            f"BER con código={resultado['ber_con_codigo']:.4%} | "
            f"Error teórico={resultado['error_teorico']:.4%}"
        )
