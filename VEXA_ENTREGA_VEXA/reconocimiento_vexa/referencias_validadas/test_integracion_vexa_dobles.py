
"""
VEXA - Gestos simples y dobles
VERSION: Ventana temporal despues del rearme

Gestos dobles:
G1+G1=G6, G2+G2=G7, G3+G3=G8,
G4+G4=G9, G5+G5=G10.

Conserva el Integrador original sin modificarlo.

Archivos necesarios en la misma carpeta:
- test_integracion_vexa_retencion_030.py
- test_integracion_vexa_dobles.py
- face_landmarker.task

Controles:
Q/ESC: salir
R: reiniciar
L: activar/desactivar CSV
"""

import csv
import time
from pathlib import Path
from datetime import datetime

import cv2
import mediapipe as mp
import numpy as np

from test_integracion_vexa_retencion_030 import (
    Integrador,
    CAMARA,
    MODELO,
    CLAVES,
    escribir,
    TIEMPO_ESTABILIDAD,
    RETENCION_BUCAL,
    REARME_GLOBAL,
    SEG_GE1,
    SEG_GE2,
)

# ==================================================
# PARAMETROS EXPERIMENTALES
# ==================================================

VENTANA_SEGUNDO = 1.50
GRACIA_CONFIRMACION = 0.85
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


# ==================================================
# PROGRAMA PRINCIPAL
# ==================================================

def main():

    if not MODELO.exists():
        raise FileNotFoundError(
            f"No se encontro: {MODELO}"
        )

    opciones = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=str(MODELO)
        ),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(CAMARA, cv2.CAP_DSHOW)

    if not cap.isOpened():
        cap = cv2.VideoCapture(CAMARA)

    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la webcam.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    detector = Integrador()
    temporal = InterpretadorTemporal()

    inicio_programa = time.monotonic()
    ultimo_ms = -1
    grabando = True

    salida = (
        Path(__file__).resolve().parent
        / datetime.now().strftime(
            "vexa_dobles_rearme_%Y%m%d_%H%M%S.csv"
        )
    )

    columnas = [
        "tiempo_s",
        "evento_base",
        "evento_final",
        "razon",
        "estado_temporal",
        "pendiente",
        "tiempo_desde_primero_s",
        "tiempo_desde_rearme_s",
        "restante_segundo_s",
        "estado_detector",
        "bloqueado",
        "boca_raw",
        "ojos_raw",
        "candidato_ocular",
        "inicio_candidato_base_s",
        "latencia_base_s",
        "eyeBlinkLeft",
        "eyeBlinkRight",
        "eyeSquintLeft",
        "eyeSquintRight",
        "WN",
        "MAR",
        "HN_ext",
        "A_D_corr",
        "progreso_gesto",
        "progreso_ventana",
    ]

    print("=" * 55)
    print("VEXA - DOBLES DESPUES DEL REARME")
    print("=" * 55)
    print("Ventana segundo:", VENTANA_SEGUNDO, "s")
    print("Rearme:", REARME_GLOBAL, "s")
    print("Gesto sostenido:", LIMITE_GESTO_SOSTENIDO, "s")
    print("G1+G1=G6 | G2+G2=G7 | G3+G3=G8")
    print("G4+G4=G9 | G5+G5=G10")
    print("=" * 55)

    try:
        with salida.open(
            "w", newline="", encoding="utf-8"
        ) as archivo:

            writer = csv.writer(archivo)
            writer.writerow(columnas)

            with mp.tasks.vision.FaceLandmarker.create_from_options(
                opciones
            ) as modelo:

                while True:

                    ok, frame = cap.read()
                    if not ok:
                        break

                    ahora = time.monotonic()
                    tiempo_s = ahora - inicio_programa

                    t_ms = max(
                        ultimo_ms + 1,
                        int(tiempo_s * 1000)
                    )
                    ultimo_ms = t_ms

                    h, w = frame.shape[:2]

                    rgb = cv2.cvtColor(
                        frame, cv2.COLOR_BGR2RGB
                    )

                    imagen_mp = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=np.ascontiguousarray(rgb)
                    )

                    resultado = modelo.detect_for_video(
                        imagen_mp, t_ms
                    )

                    lm = (
                        resultado.face_landmarks[0]
                        if resultado.face_landmarks
                        else None
                    )

                    scores = (
                        {
                            x.category_name: float(x.score)
                            for x in resultado.face_blendshapes[0]
                        }
                        if resultado.face_blendshapes
                        else None
                    )

                    if scores is not None and not all(
                        k in scores for k in CLAVES
                    ):
                        scores = None

                    # -----------------------------
                    # DETECTOR ORIGINAL
                    # -----------------------------

                    (
                        evento_base,
                        s,
                        metricas,
                        boca,
                        ojos
                    ) = detector.actualizar(
                        lm, scores, w, h, ahora
                    )

                    # -----------------------------
                    # INTERPRETADOR TEMPORAL
                    # -----------------------------

                    finales = temporal.actualizar(
                        evento_base, ahora, detector, boca
                    )

                    if evento_base:
                        print(
                            f"[{tiempo_s:.2f}s] "
                            f"BASE: {evento_base}"
                        )

                    for gesto, razon in finales:
                        print(
                            f"[{tiempo_s:.2f}s] "
                            f"FINAL: {gesto} | {razon}"
                        )

                    # -----------------------------
                    # VALORES PARA BARRAS
                    # -----------------------------

                    progreso_1, detalle_1 = progreso_detector(
                        detector, boca, ahora
                    )

                    restante = temporal.restante(ahora)

                    if temporal.pendiente is None:
                        progreso_2 = 0.0
                        detalle_2 = "SIN GESTO PENDIENTE"

                    elif temporal.t_rearme is None:
                        progreso_2 = 0.0
                        detalle_2 = "ESPERANDO REARME"

                    else:
                        progreso_2 = (
                            1.0 - restante / VENTANA_SEGUNDO
                        )

                        if temporal.estado == "SEGUNDO_EN_VALIDACION":
                            detalle_2 = (
                                "SEGUNDO EN VALIDACION"
                            )
                        else:
                            detalle_2 = (
                                f"{restante:.2f}s RESTANTES"
                            )

                    # -----------------------------
                    # PANTALLA ESPEJADA
                    # -----------------------------

                    pantalla = cv2.flip(frame, 1)

                    overlay = pantalla.copy()
                    cv2.rectangle(
                        overlay,
                        (0, 0), (w, 355),
                        (0, 0, 0), -1
                    )

                    pantalla = cv2.addWeighted(
                        overlay, 0.72,
                        pantalla, 0.28, 0
                    )

                    escribir(
                        pantalla,
                        "VEXA - DOBLES / REARME",
                        25,
                        escala=0.54
                    )

                    escribir(
                        pantalla,
                        f"Boca: {boca or '--'}  "
                        f"Ojos: {ojos or '--'}",
                        54,
                        escala=0.47
                    )

                    escribir(
                        pantalla,
                        f"Detector: {detector.estado}",
                        82,
                        escala=0.45
                    )

                    escribir(
                        pantalla,
                        f"Temporal: {temporal.estado}",
                        110,
                        escala=0.46
                    )

                    escribir(
                        pantalla,
                        f"Pendiente: {temporal.pendiente or '--'}",
                        140,
                        (0, 255, 255),
                        0.50
                    )

                    escribir(
                        pantalla,
                        f"EVENTO FINAL: {temporal.ultimo}",
                        173,
                        (0, 255, 0),
                        0.61
                    )

                    # Barra 1: gesto/rearme.
                    dibujar_barra(
                        pantalla,
                        12, 222,
                        min(w - 24, 615),
                        progreso_1,
                        "1. GESTO / REARME",
                        detalle_1,
                        (255, 170, 50)
                    )

                    # Barra 2: tiempo para repetir.
                    dibujar_barra(
                        pantalla,
                        12, 281,
                        min(w - 24, 615),
                        progreso_2,
                        "2. SEGUNDA REPETICION",
                        detalle_2,
                        (0, 200, 255)
                    )

                    if temporal.estado == "ESPERANDO_REARME":
                        mensaje = "RELAJA LA CARA / VUELVE A NEUTRO"
                    elif temporal.estado == "VENTANA_SEGUNDO":
                        mensaje = "REPITE EL MISMO GESTO AHORA"
                    elif temporal.estado == "SEGUNDO_EN_VALIDACION":
                        mensaje = "MANTEN EL SEGUNDO GESTO"
                    elif temporal.estado == "DOBLE_CONFIRMADO":
                        mensaje = "GESTO DOBLE CONFIRMADO"
                    elif temporal.estado == "SIMPLE_CONFIRMADO":
                        mensaje = "GESTO SIMPLE CONFIRMADO"
                    else:
                        mensaje = "REALIZA UN GESTO"

                    escribir(
                        pantalla,
                        mensaje,
                        325,
                        (255, 255, 255),
                        0.44
                    )

                    escribir(
                        pantalla,
                        "L: CSV  R: RESET  Q: SALIR",
                        h - 15,
                        (255, 255, 255),
                        0.48
                    )

                    # -----------------------------
                    # CSV
                    # -----------------------------

                    if grabando:

                        desde_primero = (
                            ahora - temporal.t_primero
                            if temporal.t_primero is not None
                            else None
                        )

                        desde_rearme = (
                            ahora - temporal.t_rearme
                            if temporal.t_rearme is not None
                            else None
                        )

                        writer.writerow([
                            round(tiempo_s, 4),
                            evento_base or "",
                            "|".join(x[0] for x in finales),
                            "|".join(x[1] for x in finales),
                            temporal.estado,
                            temporal.pendiente or "",
                            (
                                round(desde_primero, 4)
                                if desde_primero is not None
                                else ""
                            ),
                            (
                                round(desde_rearme, 4)
                                if desde_rearme is not None
                                else ""
                            ),
                            (
                                round(restante, 4)
                                if restante is not None
                                else ""
                            ),
                            detector.estado,
                            int(detector.bloqueado),
                            boca or "",
                            ojos or "",
                            int(detector.ocular is not None),
                            (
                                round(
                                    detector.ultimo_inicio_candidato
                                    - inicio_programa, 4
                                )
                                if evento_base
                                and detector.ultimo_inicio_candidato
                                is not None
                                else ""
                            ),
                            (
                                round(detector.ultima_latencia, 4)
                                if evento_base
                                and detector.ultima_latencia is not None
                                else ""
                            ),
                            *(
                                [round(s[k], 5) for k in CLAVES]
                                if s else [""] * 4
                            ),
                            *(
                                [
                                    round(metricas[k], 5)
                                    for k in (
                                        "WN", "MAR",
                                        "HN_ext", "A_D_corr"
                                    )
                                ]
                                if metricas else [""] * 4
                            ),
                            round(progreso_1, 4),
                            round(progreso_2, 4),
                        ])

                    # -----------------------------
                    # MOSTRAR VENTANA
                    # -----------------------------

                    cv2.imshow(
                        "VEXA - Dobles despues del rearme",
                        pantalla
                    )

                    tecla = cv2.waitKey(1) & 255

                    if tecla in (ord("q"), 27):
                        break

                    elif tecla == ord("r"):
                        detector.reiniciar()
                        temporal.reiniciar()
                        print("Detectores reiniciados.")

                    elif tecla == ord("l"):
                        grabando = not grabando
                        print(
                            "CSV:",
                            "ACTIVO" if grabando else "PAUSADO"
                        )

    finally:
        cap.release()
        cv2.destroyAllWindows()

    print("=" * 55)
    print("PRUEBA FINALIZADA")
    print("CSV:", salida)


if __name__ == "__main__":
    main()
