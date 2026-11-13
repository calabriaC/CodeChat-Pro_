
import random


def transmitir_bsc(mensaje, p):
    """Simula un canal binario simétrico."""

    if not isinstance(mensaje, str):
        raise TypeError("El mensaje debe ser una cadena binaria.")

    if not mensaje or any(bit not in "01" for bit in mensaje):
        raise ValueError("El mensaje debe contener solamente 0 y 1.")

    if isinstance(p, bool) or not isinstance(p, (int, float)):
        raise ValueError("La probabilidad debe ser numérica.")

    if not 0 <= p <= 0.5:
        raise ValueError("La probabilidad debe estar entre 0 y 0.5.")

    resultado = ""

    for bit in mensaje:
        numero_aleatorio = random.random()

        if numero_aleatorio < p:
            nuevo_bit = "1" if bit == "0" else "0"
        else:
            nuevo_bit = bit

        resultado += nuevo_bit

    return resultado


if __name__ == "__main__":
    mensaje = "111000111"
    p = 0.10

    print("Mensaje enviado:", mensaje)
    print("Mensaje recibido:", transmitir_bsc(mensaje, p))
