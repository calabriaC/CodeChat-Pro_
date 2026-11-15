
from core.codificador import codificar_repeticion
from core.canal_bsc import transmitir_bsc
from core.decodificador import decodificar_repeticion
from core.metricas import calcular_ber


def simular_transmision(mensaje, n, p):
    """
    Compara una transmisión sin código y otra con repetición.

    Admite longitudes pares e impares.
    Los empates se representan con '?'.
    """

    # 1. Transmisión sin protección
    recibido_sin_codigo = transmitir_bsc(mensaje, p)
    ber_sin_codigo = calcular_ber(mensaje, recibido_sin_codigo)

    # 2. Transmisión con código de repetición
    codificado = codificar_repeticion(mensaje, n)
    recibido_codificado = transmitir_bsc(codificado, p)
    recuperado = decodificar_repeticion(recibido_codificado, n)

    # 3. Contar los empates
    empates = recuperado.count("?")

    # 4. Contar errores en los bits que sí fueron decodificados
    errores_residuales = sum(
        bit_original != bit_recuperado
        for bit_original, bit_recuperado in zip(mensaje, recuperado)
        if bit_recuperado != "?"
    )

    # 5. Calcular cuántos bits tienen una decisión válida
    bits_decididos = len(mensaje) - empates

    # 6. BER condicionado a que exista una decisión
    ber_con_codigo = (
        errores_residuales / bits_decididos
        if bits_decididos > 0
        else None
    )

    # 7. Tasa de empates
    tasa_empates = empates / len(mensaje)

    # 8. Capacidad de corrección
    t = (n - 1) // 2

    # 9. Devolver resultados
    return {
        "original": mensaje,
        "codificado": codificado,
        "recibido_sin_codigo": recibido_sin_codigo,
        "recibido_codificado": recibido_codificado,
        "recuperado": recuperado,

        "ber_sin_codigo": ber_sin_codigo,
        "ber_con_codigo": ber_con_codigo,

        "errores_residuales": errores_residuales,
        "empates": empates,
        "bits_decididos": bits_decididos,
        "tasa_empates": tasa_empates,

        "t": t,
        "tasa": 1 / n
    }


if __name__ == "__main__":

    mensaje = "10110010" * 1000

    # Puedes probar valores pares e impares
    n = 4
    p = 0.30

    resultado = simular_transmision(mensaje, n, p)

    print("SIMULACIÓN CODECHAT PRO")
    print("-" * 45)

    print("Bits originales:", len(mensaje))
    print("Longitud del código (n):", n)
    print("Probabilidad del canal (p):", p)
    print("Errores corregibles (t):", resultado["t"])

    print()
    print(f"BER sin código: {resultado['ber_sin_codigo']:.4%}")

    if resultado["ber_con_codigo"] is not None:
        print(
            f"BER sobre bits decididos: "
            f"{resultado['ber_con_codigo']:.4%}"
        )
    else:
        print("BER no disponible: todos los bloques tienen empate.")

    print("Cantidad de empates:", resultado["empates"])
    print(f"Tasa de empates: {resultado['tasa_empates']:.4%}")
    print(f"Tasa del código: {resultado['tasa']:.4%}")

    print()
    print("Mensaje original (primeros 40 bits):")
    print(resultado["original"][:40])

    print("Mensaje recuperado (primeros 40 bits):")
    print(resultado["recuperado"][:40])

