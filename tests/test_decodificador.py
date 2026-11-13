
import pytest

from core.decodificador import decodificar_repeticion


def test_decodificacion_sin_errores():
    assert decodificar_repeticion("111000111", 3) == "101"


def test_corrige_un_error():
    assert decodificar_repeticion("110", 3) == "1"


def test_corrige_dos_errores():
    assert decodificar_repeticion("10101", 5) == "1"


def test_empate_codigo_par():
    assert decodificar_repeticion("1100", 4) == "?"


def test_varios_bloques():
    assert decodificar_repeticion("110001111", 3) == "101"


def test_longitud_incorrecta():
    with pytest.raises(ValueError):
        decodificar_repeticion("11001", 3)


def test_caracteres_invalidos():
    with pytest.raises(ValueError):
        decodificar_repeticion("10A", 3)
