"""Interpretador temporal de dobles extraído del script experimental validado."""
import cv2
from reconocimiento_vexa.facial.motor import (
    escribir, TIEMPO_ESTABILIDAD, RETENCION_BUCAL, REARME_GLOBAL,
    SEG_GE1, SEG_GE2,
)
VENTANA_SEGUNDO = 1.20
GRACIA_CONFIRMACION = 1.05
LIMITE_GESTO_SOSTENIDO = 2.00

DOBLES = {
    "G1": "G6",
    "G2": "G7",
    "G3": "G8",
    "G4": "G9",
    "G5": "G10",
}

OCULARES = {"GE1_D", "GE1_I", "GE2"}


# ==================================================
# INTERPRETADOR TEMPORAL
# ==================================================

class InterpretadorTemporal:

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.pendiente = None
        self.t_primero = None
        self.t_rearme = None
        self.estado = "DISPONIBLE"
        self.ultimo = "--"
        self.ultima_razon = "--"

    def limpiar(self):
        self.pendiente = None
        self.t_primero = None
        self.t_rearme = None

    def emitir(self, nombre, razon, resultados):
        resultados.append((nombre, razon))
        self.ultimo = nombre
        self.ultima_razon = razon

    def guardar_primero(self, gesto, ahora):
        self.pendiente = gesto
        self.t_primero = ahora
        self.t_rearme = None
        self.estado = "ESPERANDO_REARME"

    def restante(self, ahora):
        if self.t_rearme is None:
            return None
        return max(
            0.0,
            VENTANA_SEGUNDO - (ahora - self.t_rearme)
        )

    def actualizar(self, evento_base, ahora, detector, boca):
        """
        Devuelve lista de eventos finales (gesto, razon).

        Etapas:
        1. Primer gesto validado.
        2. Espera de rearme.
        3. Ventana para segundo gesto.
        4. Confirmacion simple o doble.
        """

        resultados = []

        # ------------------------------------------
        # EVENTOS OCULARES: MAXIMA PRIORIDAD
        # ------------------------------------------

        if evento_base in OCULARES:
            self.limpiar()
            self.emitir(
                evento_base,
                "PRIORIDAD_OCULAR",
                resultados
            )
            self.estado = "OCULAR_CONFIRMADO"
            return resultados

        # ------------------------------------------
        # PERDIDA DE ROSTRO
        # ------------------------------------------

        if detector.estado == "SIN ROSTRO":
            self.limpiar()
            self.estado = "SIN_ROSTRO"
            return resultados

        # ------------------------------------------
        # PRIMER GESTO
        # ------------------------------------------

        if self.pendiente is None:
            if evento_base in DOBLES:
                self.guardar_primero(evento_base, ahora)
            else:
                self.estado = "DISPONIBLE"
            return resultados

        # ------------------------------------------
        # REARME DESPUES DEL PRIMER GESTO
        # ------------------------------------------

        if self.t_rearme is None:

            # Detectar gesto sostenido.
            if (
                detector.bloqueado
                and ahora - self.t_primero
                    >= LIMITE_GESTO_SOSTENIDO
            ):
                self.emitir(
                    self.pendiente,
                    "SIMPLE_GESTO_SOSTENIDO",
                    resultados
                )
                self.limpiar()
                self.estado = "SIMPLE_CONFIRMADO"
                return resultados

            # El detector termina el rearme cuando
            # bloqueado cambia a False.
            if not detector.bloqueado:
                self.t_rearme = ahora
                self.estado = "VENTANA_SEGUNDO"
            else:
                self.estado = "ESPERANDO_REARME"

            return resultados

        # ------------------------------------------
        # SEGUNDO GESTO: CANDIDATURA
        # ------------------------------------------

        ocular_en_curso = detector.ocular is not None

        inicio_segundo = detector.boca_inicio

        candidato_a_tiempo = (
            not detector.bloqueado
            and boca in DOBLES
            and inicio_segundo is not None
            and self.t_rearme <= inicio_segundo
            and inicio_segundo - self.t_rearme
                <= VENTANA_SEGUNDO
        )

        transcurrido = ahora - self.t_rearme

        # ------------------------------------------
        # SEGUNDO GESTO YA CONFIRMADO
        # ------------------------------------------

        if evento_base in DOBLES:

            inicio_validado = (
                detector.ultimo_inicio_candidato
            )

            a_tiempo = (
                inicio_validado is not None
                and self.t_rearme <= inicio_validado
                and inicio_validado - self.t_rearme
                    <= VENTANA_SEGUNDO
                and transcurrido
                    <= VENTANA_SEGUNDO
                    + GRACIA_CONFIRMACION
            )

            if evento_base == self.pendiente and a_tiempo:
                self.emitir(
                    DOBLES[evento_base],
                    "DOBLE_CONFIRMADO",
                    resultados
                )
                self.limpiar()
                self.estado = "DOBLE_CONFIRMADO"
                return resultados

            # Gesto distinto o repeticion tardia.
            self.emitir(
                self.pendiente,
                "SIMPLE_POR_NUEVA_ACTIVACION",
                resultados
            )

            self.guardar_primero(evento_base, ahora)
            return resultados

        # ------------------------------------------
        # PRIORIDAD OCULAR DURANTE LA VENTANA
        # ------------------------------------------

        if ocular_en_curso:
            self.estado = "PRIORIDAD_OCULAR_EN_CURSO"
            return resultados

        # ------------------------------------------
        # ESPERAR CONFIRMACION DEL SEGUNDO
        # ------------------------------------------

        if (
            candidato_a_tiempo
            and transcurrido
                <= VENTANA_SEGUNDO + GRACIA_CONFIRMACION
        ):
            self.estado = "SEGUNDO_EN_VALIDACION"
            return resultados

        # ------------------------------------------
        # VENCIMIENTO: GESTO SIMPLE
        # ------------------------------------------

        if transcurrido >= VENTANA_SEGUNDO:
            self.emitir(
                self.pendiente,
                "SIMPLE_POR_TIMEOUT",
                resultados
            )
            self.limpiar()
            self.estado = "SIMPLE_CONFIRMADO"
            return resultados

        self.estado = "VENTANA_SEGUNDO"
        return resultados


# ==================================================
# BARRAS VISUALES
# ==================================================

def dibujar_barra(
    imagen, x, y, ancho,
    progreso, titulo, detalle, color
):
    progreso = max(0.0, min(1.0, progreso))

    escribir(
        imagen,
        f"{titulo}: {detalle}",
        y - 9,
        (255, 255, 255),
        0.43
    )

    cv2.rectangle(
        imagen,
        (x, y),
        (x + ancho, y + 18),
        (60, 60, 60),
        -1
    )

    cv2.rectangle(
        imagen,
        (x, y),
        (x + int(ancho * progreso), y + 18),
        color,
        -1
    )

    cv2.rectangle(
        imagen,
        (x, y),
        (x + ancho, y + 18),
        (220, 220, 220),
        1
    )


def progreso_detector(detector, boca, ahora):

    # Progreso de candidato ocular.
    if (
        detector.ocular is not None
        and detector.ocular_inicio is not None
    ):
        limite = (
            SEG_GE2
            if detector.ocular == "GE2"
            else SEG_GE1
        )

        transcurrido = max(
            0.0,
            ahora - detector.ocular_inicio
        )

        return (
            min(1.0, transcurrido / limite),
            f"{detector.ocular} "
            f"{min(transcurrido, limite):.2f}/{limite:.2f}s"
        )

    # Rearme mediante neutralidad.
    if detector.bloqueado:
        transcurrido = (
            max(0.0, ahora - detector.neutro_inicio)
            if detector.neutro_inicio is not None
            else 0.0
        )

        return (
            min(1.0, transcurrido / REARME_GLOBAL),
            f"NEUTRO/REARME "
            f"{min(transcurrido, REARME_GLOBAL):.2f}/"
            f"{REARME_GLOBAL:.2f}s"
        )

    # Progreso del candidato bucal.
    if (
        boca in DOBLES
        and detector.boca_inicio is not None
    ):
        total = TIEMPO_ESTABILIDAD + RETENCION_BUCAL

        if detector.boca_listo is None:
            transcurrido = min(
                max(0.0, ahora - detector.boca_inicio),
                TIEMPO_ESTABILIDAD
            )
        else:
            transcurrido = (
                TIEMPO_ESTABILIDAD
                + max(0.0, ahora - detector.boca_listo)
            )

        return (
            min(1.0, transcurrido / total),
            f"{boca} "
            f"{min(transcurrido, total):.2f}/{total:.2f}s"
        )

    return 0.0, "ESPERANDO GESTO"


