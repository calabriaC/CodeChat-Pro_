# CodeChat-Pro_


**Proyecto final de Teoría de Códigos — Tema 6: Canal Binario Simétrico (BSC)**

**Universidad del Norte | 2026**

**Integrantes:** Alberto Aponte, Ethan Barreneche, Carlos Calabria y Angel Fontalvo.

## 1. Descripción del proyecto

**CodeChat Pro** es una aplicación de escritorio desarrollada en Python que simula la transmisión de mensajes a través de un Canal Binario Simétrico (BSC). Implementa códigos de repetición y decodificación por mayoría para demostrar cómo la redundancia permite corregir errores introducidos durante una transmisión digital.

La aplicación cuenta con cinco módulos: **Chat, Laboratorio BSC, Análisis, Teoría e Historial**. Permite transmitir mensajes, configurar la probabilidad de error, comparar códigos de repetición y visualizar métricas y gráficas utilizando texto personalizado o bits aleatorios.

## 2. Fundamento matemático

En un código de repetición binario de longitud `n`, cada bit se transmite `n` veces. Sus parámetros son:

- Dimensión: `k = 1`.
- Distancia mínima: `d_min = n`.
- Capacidad correctora: `t = ⌊(n−1)/2⌋`.
- Tasa de transmisión: `R = 1/n`.

El canal BSC invierte cada bit de forma independiente con probabilidad `p`. La capacidad teórica de Shannon es:

**C = 1 − H₂(p)**

donde **H₂(p) = −p log₂(p) − (1−p) log₂(1−p)**.

## 3. Instalación y ejecución

**Requisitos:** Python 3, PySide6 y Matplotlib.

Abrir una terminal en la carpeta principal del proyecto e instalar las dependencias, si todavía no están instaladas:

```bash
python -m pip install PySide6 matplotlib
```

Ejecutar la aplicación:

```bash
python app.py
```

No es necesario crear un entorno virtual.

## 4. Resultados principales

Para un canal BSC con **p = 0.10**, los valores teóricos de error después de decodificar por mayoría son:

| Código     | Tasa R | Errores corregibles | Error residual teórico |
| ---------- | -----: | ------------------: | ---------------------: |
| Sin código | 1.0000 |                   0 |               0.100000 |
| n = 3      | 0.3333 |                   1 |               0.028000 |
| n = 5      | 0.2000 |                   2 |               0.008560 |
| n = 7      | 0.1429 |                   3 |               0.002728 |

La comparación demuestra que aumentar la longitud del código reduce la probabilidad teórica de error residual, pero también disminuye la tasa de transmisión debido a la redundancia. Para `p = 0.10`, la capacidad de Shannon es aproximadamente **C = 0.5310**.

El módulo Análisis permite contrastar estos resultados con simulaciones experimentales y graficar el error frente a la tasa de transmisión.

## 5. Herramientas utilizadas:



- **PySide6 y Matplotlib:** construcción de la interfaz gráfica y visualización de resultados.
- **JSON:** almacenamiento del historial de transmisiones.
- **Git y GitHub:** control de versiones y gestión del código fuente.
- **Asistentes de programación con IA Chat-GPT Y Claude:** apoyo en propuestas de diseño, rediseño de la interfaz y ajustes visuales.
- Python donde se desarrollo la aplicación.
