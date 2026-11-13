import pytest

from core.codificador import codificar_repeticion


def test_codificacion_n3():
    resultado = codificar_repeticion("101", 3)
    assert resultado == "111000111"


def test_codificacion_n5():
    resultado = codificar_repeticion("1101", 5)
    assert resultado == "11111111110000011111"


def test_longitud_codificada():
    mensaje = "10110"
    n = 7

    resultado = codificar_repeticion(mensaje, n)

    assert len(resultado) == len(mensaje) * n


def test_mensaje_invalido():
    with pytest.raises(ValueError):
        codificar_repeticion("10A1", 3)


def test_longitud_invalida():
    with pytest.raises(ValueError):
        codificar_repeticion("101", 0)