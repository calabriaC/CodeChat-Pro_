import math

def calcular_parametros(n):
    """Calcula los parámetros de un código de repetición binario."""

    if type(n) is not int or not 1 <= n <= 21:
        raise ValueError("n debe ser un entero entre 1 y 21.")

    k = 1
    M = 2 ** k
    distancia_minima = n

    errores_detectables = distancia_minima - 1
    errores_corregibles = (distancia_minima - 1) // 2

    tasa = k / n

    return {
        "n": n,
        "k": k,
        "M": M,
        "distancia_minima": distancia_minima,
        "errores_detectables": errores_detectables,
        "errores_corregibles": errores_corregibles,
        "tasa": tasa
    }

def entropia_binaria(p):
    """Calcula la entropía binaria H₂(p)."""

    if isinstance(p, bool) or not isinstance(p, (int, float)):
        raise ValueError("p debe ser un número.")

    if not 0 <= p <= 1:
        raise ValueError("p debe estar entre 0 y 1.")

    if p == 0 or p == 1:
        return 0.0

    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def capacidad_shannon(p):
    """Calcula la capacidad del canal binario simétrico."""

    if not 0 <= p <= 0.5:
        raise ValueError("Para nuestra simulación, p debe estar entre 0 y 0.5.")

    return 1 - entropia_binaria(p)


def probabilidad_error_residual(n, p):
    """Calcula el error residual con decodificación por mayoría."""

    if type(n) is not int or not 1 <= n <= 21:
        raise ValueError("n debe ser un entero entre 1 y 21.")

    if isinstance(p, bool) or not isinstance(p, (int, float)):
        raise ValueError("p debe ser numérica.")

    if not 0 <= p <= 0.5:
        raise ValueError("p debe estar entre 0 y 0.5.")

    if n % 2 == 0:
        raise ValueError(
            "Esta fórmula requiere n impar para evitar empates."
        )

    t = (n - 1) // 2
    probabilidad = 0.0

    for i in range(t + 1, n + 1):
        combinaciones = math.comb(n, i)

        termino = (
            combinaciones
            * (p ** i)
            * ((1 - p) ** (n - i))
        )

        probabilidad += termino

    return probabilidad


if __name__ == "__main__":
    parametros = calcular_parametros(5)

    for nombre, valor in parametros.items():
        print(f"{nombre}: {valor}")
         
print("\nCapacidad de Shannon:")

for p in [0, 0.1, 0.2, 0.5]:
    print(f"p = {p}: C = {capacidad_shannon(p):.4f}")


print("\nComparación de errores para p = 0.1")

for n in [3, 5, 7]:
    error = probabilidad_error_residual(n, 0.1)

    print(f"n = {n}: error residual = {error:.4%}")