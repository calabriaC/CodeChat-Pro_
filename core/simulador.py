
from core.codificador import codificar_repeticion
from core.canal_bsc import transmitir_bsc
from core.decodificador import decodificar_repeticion
from core.metricas import calcular_ber


def simular_transmision(mensaje, n, p):
    """Compara una transmisión sin código y otra con repetición."""

    # Transmisión sin protección
    recibido_sin_codigo = transmitir_bsc(mensaje, p)
    ber_sin_codigo = calcular_ber(mensaje, recibido_sin_codigo)

    # Transmisión con código de repetición
    codificado = codificar_repeticion(mensaje, n)
    recibido_codificado = transmitir_bsc(codificado, p)
    recuperado = decodificar_repeticion(recibido_codificado, n)

    # Para calcular BER, no debe haber bits ambiguos.
    if "?" in recuperado:
        raise ValueError(
            "Hay empates en la decodificación. Usa n impar."
        )

    ber_con_codigo = calcular_ber(mensaje, recuperado)

    return {
        "original": mensaje,
        "codificado": codificado,
        "recibido_sin_codigo": recibido_sin_codigo,
        "recibido_codificado": recibido_codificado,
        "recuperado": recuperado,
        "ber_sin_codigo": ber_sin_codigo,
        "ber_con_codigo": ber_con_codigo,
        "tasa": 1 / n
    }


if __name__ == "__main__":
    mensaje = "10110010" * 1000
    n = 3
    p = 0.10

    resultado = simular_transmision(mensaje, n, p)

    print("Bits originales:", len(mensaje))
    print("Longitud del código:", n)
    print("Probabilidad del canal:", p)

    print(f"BER sin código: {resultado['ber_sin_codigo']:.4%}")
    print(f"BER con código: {resultado['ber_con_codigo']:.4%}")
    print(f"Tasa de información: {resultado['tasa']:.4%}")
