
import pytest
from core.canal_bsc import transmitir_bsc


def test_canal_sin_ruido():
    mensaje = "10110010"
    resultado = transmitir_bsc(mensaje, 0)

    assert resultado == mensaje


def test_conserva_longitud():
    mensaje = "11001010"
    resultado = transmitir_bsc(mensaje, 0.2)

    assert len(resultado) == len(mensaje)


def test_resultado_binario():
    mensaje = "10110101"
    resultado = transmitir_bsc(mensaje, 0.3)

    assert all(bit in "01" for bit in resultado)


def test_probabilidad_invalida():
    with pytest.raises(ValueError):
        transmitir_bsc("1010", 0.8)


def test_mensaje_invalido():
    with pytest.raises(ValueError):
        transmitir_bsc("10A1", 0.1)


def test_probabilidad_cero():
    assert transmitir_bsc("111000", 0.0) == "111000"
