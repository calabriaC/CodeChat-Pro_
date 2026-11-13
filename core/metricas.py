
def calcular_ber(original, recibido):
    """Calcula la tasa de error de bits entre dos mensajes."""

    if not isinstance(original, str) or not isinstance(recibido, str):
        raise TypeError("Los mensajes deben ser cadenas binarias.")

    if not original or not recibido:
        raise ValueError("Los mensajes no pueden estar vacíos.")

    if len(original) != len(recibido):
        raise ValueError("Los mensajes deben tener la misma longitud.")

    if any(bit not in "01" for bit in original + recibido):
        raise ValueError("Los mensajes deben contener solo 0 y 1.")

    errores = 0

    for bit_original, bit_recibido in zip(original, recibido):
        if bit_original != bit_recibido:
            errores += 1

    return errores / len(original)


if __name__ == "__main__":
    original = "10110010"
    recibido = "10010011"

    ber = calcular_ber(original, recibido)

    print("Mensaje original:", original)
    print("Mensaje recibido:", recibido)
    print(f"BER: {ber:.2%}")
