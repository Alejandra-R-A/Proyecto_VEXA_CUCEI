"""Lector EMG independiente para dos AD8232 con Arduino Uno."""

import math
import threading
import time
from collections import deque

import serial

BAUDIOS = 250000
FRECUENCIA = 500
CORTE_HZ = 10.0
VENTANA_RMS = 100


class CanalRMS:
    def __init__(self):
        rc = 1.0 / (2.0 * math.pi * CORTE_HZ)
        self.alpha = rc / (rc + 1.0 / FRECUENCIA)
        self.reiniciar()

    def reiniciar(self):
        self.anterior = None
        self.filtrado = 0.0
        self.energia = deque()
        self.total = 0.0

    def actualizar(self, adc):
        valor = float(adc)

        if self.anterior is None:
            self.anterior = valor
            return None

        self.filtrado = self.alpha * (
            self.filtrado + valor - self.anterior
        )
        self.anterior = valor

        energia = self.filtrado ** 2
        self.energia.append(energia)
        self.total += energia

        if len(self.energia) > VENTANA_RMS:
            self.total -= self.energia.popleft()

        if len(self.energia) < VENTANA_RMS:
            return None

        return math.sqrt(
            max(0.0, self.total) / VENTANA_RMS
        )


class LectorEMG:
    def __init__(self, puerto="COM9"):
        self.puerto = puerto
        self.muestras = deque(maxlen=5000)
        self.lock = threading.Lock()
        self.detener_evento = threading.Event()
        self.hilo = None
        self.error = None
        self.recibidas = 0
        self.validas = 0
        self.ultimo_dato = None

    def iniciar(self):
        if self.hilo is not None and self.hilo.is_alive():
            return

        self.detener_evento.clear()
        self.error = None

        self.hilo = threading.Thread(
            target=self._ejecutar,
            daemon=True,
            name="VEXA_EMG"
        )
        self.hilo.start()

    def _ejecutar(self):
        canales = [CanalRMS(), CanalRMS()]
        anterior_contador = None
        anterior_tiempo_us = None

        try:
            with serial.Serial(
                self.puerto,
                BAUDIOS,
                timeout=0.1
            ) as arduino:

                time.sleep(2.0)
                arduino.reset_input_buffer()

                while not self.detener_evento.is_set():
                    linea = arduino.readline()

                    if not linea:
                        continue

                    try:
                        valores = [
                            int(x)
                            for x in linea.strip().split(b",")
                        ]

                        if len(valores) != 8:
                            continue

                        n, micros, a, b, l1p, l1n, l2p, l2n = valores

                        if not (
                            0 <= a <= 1023
                            and 0 <= b <= 1023
                            and all(
                                x in (0, 1)
                                for x in (l1p, l1n, l2p, l2n)
                            )
                        ):
                            continue

                    except ValueError:
                        continue

                    continuo = (
                        anterior_contador is None
                        or n == anterior_contador + 1
                    )

                    if anterior_tiempo_us is not None:
                        delta_us = (
                            micros - anterior_tiempo_us
                        ) & 0xffffffff

                        if delta_us > 1000000:
                            continuo = False

                    anterior_contador = n
                    anterior_tiempo_us = micros

                    if not continuo:
                        for canal in canales:
                            canal.reiniciar()

                    calidad = (
                        continuo and l1p == 0 and l1n == 0
                        and 5 < a < 1018,
                        continuo and l2p == 0 and l2n == 0
                        and 5 < b < 1018,
                    )

                    rms = []

                    for i, adc in enumerate((a, b)):
                        if calidad[i]:
                            rms.append(
                                canales[i].actualizar(adc)
                            )
                        else:
                            canales[i].reiniciar()
                            rms.append(None)

                    muestra = (
                        time.monotonic(),
                        rms[0],
                        rms[1],
                        calidad[0] and rms[0] is not None,
                        calidad[1] and rms[1] is not None,
                    )

                    with self.lock:
                        self.muestras.append(muestra)
                        self.recibidas += 1
                        self.ultimo_dato = muestra[0]

                        if muestra[3] or muestra[4]:
                            self.validas += 1

        except Exception as exc:
            self.error = (
                f"{type(exc).__name__}: {exc}"
            )

    def obtener_muestras(self):
        with self.lock:
            return list(self.muestras)

    def estado(self):
        with self.lock:
            return {
                "recibidas": self.recibidas,
                "validas": self.validas,
                "ultimo_dato": self.ultimo_dato,
                "error": self.error,
            }

    def detener(self):
        self.detener_evento.set()

        if self.hilo is not None:
            self.hilo.join(timeout=3.0)
