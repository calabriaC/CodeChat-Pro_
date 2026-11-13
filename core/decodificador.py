
def decodificar_repeticion(mensaje, n):
    """Recupera bits utilizando decodificación por mayoría."""

    if not isinstance(mensaje, str):
        raise TypeError("El mensaje debe ser una cadena binaria.")

    if not mensaje or any(bit not in "01" for bit in mensaje):
        raise ValueError("El mensaje debe contener solamente 0 y 1.")

    if type(n) is not int or not 1 <= n <= 21:
        raise ValueError("La longitud debe ser un entero entre 1 y 21.")

    if len(mensaje) % n != 0:
        raise ValueError("La longitud del mensaje no es divisible entre n.")

    resultado = ""

    for i in range(0, len(mensaje), n):
        bloque = mensaje[i:i + n]

        unos = bloque.count("1")
        ceros = bloque.count("0")

        if unos > ceros:
            resultado += "1"
        elif ceros > unos:
            resultado += "0"
        else:
            resultado += "?"

    return resultado


if __name__ == "__main__":
    mensaje = "10101"
    n = 5

    print("Mensaje recibido:", mensaje)
    print("Mensaje recuperado:", decodificar_repeticion(mensaje, n))
