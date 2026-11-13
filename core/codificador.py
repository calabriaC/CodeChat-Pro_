def codificar_repeticion(mensaje, n):
    if not isinstance(mensaje, str):
        raise TypeError("El mensaje debe ser una cadena de bits.")

    if not mensaje:
        raise ValueError("El mensaje no puede estar vacío.")

    if any(bit not in "01" for bit in mensaje):
        raise ValueError("El mensaje debe contener solamente 0 y 1.")

    if type(n) is not int or not 1 <= n <= 21:
        raise ValueError("La longitud n debe ser un entero entre 1 y 21.")

    resultado = ""

    for bit in mensaje:
        resultado += bit * n

    return resultado

if __name__ == "__main__":
    mensaje = "1101"
    n = 5

    print("Mensaje original:", mensaje)
    print("Mensaje codificado:", codificar_repeticion(mensaje, n))