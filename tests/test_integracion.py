from core.codificador import codificar_repeticion
from core.canal_bsc import transmitir_bsc
from core.decodificador import decodificar_repeticion


def test_transmision_completa():
    mensaje = "101"
    n = 3
    p = 0

    codificado = codificar_repeticion(mensaje, n)
    recibido = transmitir_bsc(codificado, p)
    recuperado = decodificar_repeticion(recibido, n)

    assert recuperado == mensaje