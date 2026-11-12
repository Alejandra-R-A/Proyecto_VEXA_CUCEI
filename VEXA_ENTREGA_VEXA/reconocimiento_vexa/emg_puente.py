"""Puente entre adquisici?n EMG y validaci?n de gestos VEXA."""

import time

from .emg_validador import validar_gesto_emg


class PuenteEMG:
    def __init__(
        self,
        lector,
        umbrales,
        ventana_segundos=2.5,
        tolerancia_segundos=0.25,
    ):
        self.lector = lector
        self.umbrales = tuple(umbrales)
        self.ventana_segundos = float(ventana_segundos)
        self.tolerancia_segundos = float(tolerancia_segundos)

    def validar(self, gesto, instante_evento=None):
        """Devuelve (autorizado, motivo).

        El instante del evento debe expresarse en time.monotonic().
        La ventana inicial es provisional y se ajustar? al
        comportamiento real del motor facial.
        """
        if instante_evento is None:
            instante_evento = time.monotonic()

        # Los gestos oculares nunca requieren Arduino ni EMG.
        if gesto in {"GE1_DF", "GE1_IF", "GE2F"}:
            return True, "OCULAR_SIN_EMG"

        muestras = self.lector.obtener_muestras()

        if not muestras:
            return False, "SIN_MUESTRAS"

        estado = self.lector.estado()

        if estado.get("error"):
            return False, "ERROR_LECTOR"

        ultimo_dato = estado.get("ultimo_dato")

        if ultimo_dato is None:
            return False, "SIN_DATOS_RECIENTES"

        if instante_evento - ultimo_dato > self.tolerancia_segundos:
            return False, "DATOS_EMG_ANTIGUOS"

        if ultimo_dato - instante_evento > self.tolerancia_segundos:
            return False, "RELOJES_NO_SINCRONIZADOS"

        inicio = instante_evento - self.ventana_segundos

        ventana = [
            m for m in muestras
            if inicio <= m[0] <= instante_evento
        ]

        if len(ventana) < 60:
            return False, "VENTANA_INSUFICIENTE"

        # Exigir al menos un canal con datos v?lidos recientes.
        recientes = [
            m for m in ventana
            if m[0] >= instante_evento - self.tolerancia_segundos
        ]

        if not any(m[3] or m[4] for m in recientes):
            return False, "SIN_CANAL_EMG_VALIDO_RECIENTE"

        # Primero conservar la validacion historica original.
        autorizado, motivo = validar_gesto_emg(
            gesto,
            ventana,
            self.umbrales,
            inicio,
            instante_evento,
        )

        if not autorizado:
            return autorizado, motivo

        # Una contraccion antigua no debe autorizar por si sola
        # un nuevo evento facial. Ventana provisional de 0.5 s.
        inicio_reciente = max(
            inicio,
            instante_evento - 0.5,
        )

        autorizado_reciente, motivo_reciente = validar_gesto_emg(
            gesto,
            ventana,
            self.umbrales,
            inicio_reciente,
            instante_evento,
        )

        if not autorizado_reciente:
            return False, "EMG_ACTIVIDAD_NO_RECIENTE"

        return True, motivo_reciente
