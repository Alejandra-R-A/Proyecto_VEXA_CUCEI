"""VEXA | Integración experimental G1-G5 + GE1/GE2.
Una cámara, un Face Landmarker, arbitraje conservador de eventos.
No modifica los detectores anteriores. No conectado a la interfaz ni EMG.
Q/ESC salir, R reiniciar, L grabar/detener CSV.
"""
import csv
import math
import time
from pathlib import Path
from datetime import datetime
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
from reconocimiento_vexa.parametros import ParametrosFaciales

CAMARA = 0
MODELO = Path(__file__).resolve().parents[1] / "modelos" / "face_landmarker.task"
# Boca: exactamente los umbrales del detector G1-G5 funcional.
UMBRAL_G5_WN = 0.52
UMBRAL_G4_MAR = 0.16
UMBRAL_G3_HN_EXT = 0.20
UMBRAL_G1_ASIMETRIA = 0.030
UMBRAL_G2_ASIMETRIA = -0.030
VENTANA_SUAVIZADO = 5
TIEMPO_ESTABILIDAD = 0.35
# Ojos: ajustes de la última sesión satisfactoria.
UMBRAL_PARPADEO = 0.48
UMBRAL_GUINO_D = 0.44
DIFERENCIA_GUINO = 0.22
DIFERENCIA_GUINO_D = 0.10
UMBRAL_BILATERAL = 0.54
SEG_GE1 = 0.70 #0.40
SEG_GE2 = 1.00 #0.70
SEG_REARME = 0.35
MARGEN_HISTERESIS_BLINK = 0.05
MARGEN_HISTERESIS_DIF = 0.05
TOLERANCIA_PERDIDA_S = 0.12
VENTANA = 5
CLAVES = ("eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "eyeSquintRight")
# Un candidato bucal espera a que los ojos puedan confirmarse o descartarse.
# Es una medida experimental de arbitraje; aumenta la latencia bucal.
RETENCION_BUCAL = 0.30
REARME_GLOBAL = 0.40
BLINK_NEUTRAL_MAX = 0.40


class LandmarkEspejado:
    """Adapta coordenadas al espejo del detector bucal original.
    No intercambia IDs: conserva su correspondencia anatómica."""
    def __init__(self, landmark):
        self.x = 1.0 - landmark.x
        self.y = landmark.y
        self.z = landmark.z


def escribir(img, msg, y, color=(255,255,255), escala=0.52):
    cv2.putText(img, msg, (12,y), cv2.FONT_HERSHEY_SIMPLEX,
                escala, (0,0,0), 4, cv2.LINE_AA)
    cv2.putText(img, msg, (12,y), cv2.FONT_HERSHEY_SIMPLEX,
                escala, color, 1, cv2.LINE_AA)

def calcular_metricas(landmarks, ancho, alto):

    def punto(indice):
        return np.array(
            [
                landmarks[indice].x * ancho,
                landmarks[indice].y * alto
            ],
            dtype=float
        )

    def distancia(a, b):
        return float(np.linalg.norm(a - b))

    # Ojos
    p33 = punto(33)
    p263 = punto(263)

    # Comisuras
    p61 = punto(61)
    p291 = punto(291)

    # Labios internos
    p13 = punto(13)
    p14 = punto(14)

    # Labios externos
    p0 = punto(0)
    p17 = punto(17)

    # Distancia interocular
    dio = distancia(p33, p263)

    # Ancho de boca
    ancho_boca = distancia(p61, p291)

    if dio < 1e-6 or ancho_boca < 1e-6:
        return None

    # Alturas labiales
    altura_interna = distancia(p13, p14)
    altura_externa = distancia(p0, p17)

    # Metricas normalizadas
    wn = ancho_boca / dio
    hn_int = altura_interna / dio
    hn_ext = altura_externa / dio

    mar = altura_interna / ancho_boca

    h_lip_ratio = altura_externa / ancho_boca

    delta_h = hn_ext - hn_int

    # --------------------------------------------------------
    # ASIMETRIA CORREGIDA POR INCLINACION
    # --------------------------------------------------------

    vector_ojos = p263 - p33

    theta = math.atan2(
        vector_ojos[1],
        vector_ojos[0]
    )

    vector_boca = p291 - p61

    ad_corr = (
        vector_boca[0] * math.sin(theta)
        - vector_boca[1] * math.cos(theta)
    ) / dio

    an_corr = abs(ad_corr)

    # Asimetria sin corregir
    ad_raw = (
        p61[1] - p291[1]
    ) / dio

    roll = math.degrees(theta)

    # --------------------------------------------------------
    # PROTRUSION
    # --------------------------------------------------------

    z_labios = (
        landmarks[13].z + landmarks[14].z
    ) / 2.0

    z_comisuras = (
        landmarks[61].z + landmarks[291].z
    ) / 2.0

    dio_x_norm = dio / ancho

    zn = (
        z_labios - z_comisuras
    ) / dio_x_norm

    return {
        "DIO": dio,
        "WN": wn,
        "HN_int": hn_int,
        "HN_ext": hn_ext,
        "MAR": mar,
        "H_lip_ratio": h_lip_ratio,
        "Delta_H": delta_h,
        "A_D_raw": ad_raw,
        "A_D_corr": ad_corr,
        "AN_corr": an_corr,
        "ZN": zn,
        "Roll": roll
    }

class SuavizadorMetricas:

    def __init__(self, ventana=5):
        self.ventana = ventana
        self.historial = {}

    def actualizar(self, metricas):

        if not self.historial:
            for nombre in metricas:
                self.historial[nombre] = deque(
                    maxlen=self.ventana
                )

        for nombre, valor in metricas.items():
            self.historial[nombre].append(valor)

        return {
            nombre: float(np.median(valores))
            for nombre, valores in self.historial.items()
        }

    def reiniciar(self):
        self.historial.clear()

def clasificar_gesto(metricas, parametros=None):
    p = parametros or ParametrosFaciales()

    wn = metricas["WN"]
    mar = metricas["MAR"]
    hn_ext = metricas["HN_ext"]
    ad_corr = metricas["A_D_corr"]

    # PASO 1: G5
    if wn < p.umbral_g5_wn:
        return "G5", "WN debajo del umbral"

    # PASO 2: G4
    if mar > p.umbral_g4_mar:
        return "G4", "MAR encima del umbral"

    # PASO 3: G3
    if hn_ext < p.umbral_g3_hn_ext:
        return "G3", "HN_ext debajo del umbral"

    # PASO 4: G1
    if ad_corr > p.umbral_g1_asimetria:
        return "G1", "Asimetria positiva"

    # PASO 5: G2
    if ad_corr < p.umbral_g2_asimetria:
        return "G2", "Asimetria negativa"

    # PASO 6: NEUTRO
    return "NEUTRO", "Sin gesto reconocido"

def clasificar(blink_i, blink_d, umbral, diferencia, bilateral, umbral_d, dif_d=DIFERENCIA_GUINO_D, dif_bilateral=None):
    dif_bilateral = diferencia if dif_bilateral is None else dif_bilateral
    # GE2 solo cuando los DOS valores blink son elevados y semejantes.
    if min(blink_i, blink_d) >= bilateral and abs(blink_i - blink_d) < dif_bilateral:
        return "GE2"
    # GE1: permitir que el ojo contrario se cierre un poco, pero exigir asimetria.
    if blink_d >= umbral_d and blink_d - blink_i >= dif_d:
        return "GE1_D"
    if blink_i >= umbral and blink_i - blink_d >= diferencia:
        return "GE1_I"
    return "NEUTRO/INCIERTO"

def mantener_candidato(candidato, blink_i, blink_d, umbral, diferencia, bilateral, umbral_d, dif_d=DIFERENCIA_GUINO_D, dif_bilateral=None):
    dif_bilateral = diferencia if dif_bilateral is None else dif_bilateral
    """Sostiene un candidato GE1 sin relajar el umbral para INICIARLO.

    GE2 conserva su criterio original. Nunca convierte un guiño en GE2
    mientras existan indicios asimétricos de un guiño.
    """
    dif_relajada = max(0.01, diferencia - MARGEN_HISTERESIS_DIF)
    blink_relajado = max(0.01, umbral - MARGEN_HISTERESIS_BLINK)
    blink_d_relajado = max(0.01, umbral_d - MARGEN_HISTERESIS_BLINK)
    if candidato == 'GE1_D':
        return (blink_d >= blink_d_relajado and
                blink_d - blink_i >= max(0.01, dif_d - MARGEN_HISTERESIS_DIF))
    if candidato == 'GE1_I':
        return blink_i >= blink_relajado and blink_i - blink_d >= dif_relajada
    if candidato == 'GE2':
        return min(blink_i, blink_d) >= bilateral and abs(blink_i - blink_d) < dif_bilateral
    return False


class Integrador:
    def __init__(self, parametros=None):
        self.parametros = parametros or ParametrosFaciales()
        self.boca_suav = SuavizadorMetricas(VENTANA_SUAVIZADO)
        self.ojos_suav = {k: deque(maxlen=VENTANA) for k in CLAVES}
        self.boca_raw = "NEUTRO"
        self.boca_inicio = None
        self.boca_listo = None
        self.ocular = None
        self.ocular_inicio = None
        self.ocular_ultimo = None
        self.bloqueado = False
        self.neutro_inicio = None
        self.ultimo = "--"
        self.estado = "LISTO"
        self.ultimo_inicio_candidato = None
        self.ultima_latencia = None
        self.ultimo_origen = None

    def reiniciar(self):
        self.__init__(self.parametros)

    def actualizar(self, lm, scores, w, h, ahora):
        if lm is None or scores is None:
            self.boca_raw = "NEUTRO"
            self.boca_inicio = None
            self.boca_listo = None
            self.ocular = None
            self.ocular_inicio = None
            self.ocular_ultimo = None
            self.neutro_inicio = None
            self.boca_suav.reiniciar()
            for cola in self.ojos_suav.values():
                cola.clear()
            self.estado = "SIN ROSTRO"
            return None, None, None, None, "SIN_ROSTRO"

        for k in CLAVES:
            self.ojos_suav[k].append(scores[k])
        s = {k: float(np.median(self.ojos_suav[k])) for k in CLAVES}
        bi, bd = s["eyeBlinkLeft"], s["eyeBlinkRight"]
        ojos_raw = clasificar(bi, bd, self.parametros.umbral_ge1_i,
                            self.parametros.diferencia_ge1_i, self.parametros.umbral_ge2,
                            self.parametros.umbral_ge1_d, self.parametros.diferencia_ge1_d,
                            self.parametros.diferencia_ge2)
        m = calcular_metricas([LandmarkEspejado(x) for x in lm], w, h)
        if m is None:
            return None, s, None, None, ojos_raw
        metricas = self.boca_suav.actualizar(m)
        boca, _ = clasificar_gesto(metricas, self.parametros)
        if boca != self.boca_raw:
            self.boca_raw = boca
            self.boca_inicio = ahora
            self.boca_listo = None
        if boca != "NEUTRO" and self.boca_inicio is not None:
            if ahora-self.boca_inicio >= TIEMPO_ESTABILIDAD and self.boca_listo is None:
                self.boca_listo = ahora
        else:
            self.boca_listo = None

        ambos_neutros = (
            boca == "NEUTRO" and ojos_raw == "NEUTRO/INCIERTO"
            and max(bi,bd) < self.parametros.blink_neutral_max
        )
        if self.bloqueado:
            if ambos_neutros:
                if self.neutro_inicio is None:
                    self.neutro_inicio = ahora
                elif ahora-self.neutro_inicio >= REARME_GLOBAL:
                    self.bloqueado = False
            else:
                self.neutro_inicio = None
            self.estado = "ESPERANDO NEUTRO" if self.bloqueado else "REARMADO"
            return None, s, metricas, boca, ojos_raw

        # Primera prioridad: candidatura ocular.
        if self.ocular is None:
            if ojos_raw.startswith("GE"):
                self.ocular = ojos_raw
                self.ocular_inicio = ahora
                self.ocular_ultimo = ahora
        else:
            sostiene = mantener_candidato(
                self.ocular, bi, bd, self.parametros.umbral_ge1_i,
                self.parametros.diferencia_ge1_i, self.parametros.umbral_ge2,
                self.parametros.umbral_ge1_d, self.parametros.diferencia_ge1_d,
                self.parametros.diferencia_ge2)
            if sostiene:
                self.ocular_ultimo = ahora
            elif ojos_raw.startswith("GE") and ojos_raw != self.ocular:
                self.ocular = None
                self.ocular_inicio = None
                self.ocular_ultimo = None
            elif self.ocular_ultimo is None or ahora-self.ocular_ultimo > TOLERANCIA_PERDIDA_S:
                self.ocular = None
                self.ocular_inicio = None
                self.ocular_ultimo = None

        if self.ocular is not None:
            # Cualquier candidato ocular invalida la confirmación bucal pendiente.
            # Si el ojo deja de ser candidato, la boca deberá estabilizarse otra vez.
            self.boca_listo = None
            self.boca_inicio = ahora
            self.estado = "PRIORIDAD OCULAR: " + self.ocular
            minimo = SEG_GE2 if self.ocular=="GE2" else SEG_GE1
            sostiene_ahora = mantener_candidato(
                self.ocular, bi, bd, self.parametros.umbral_ge1_i,
                self.parametros.diferencia_ge1_i, self.parametros.umbral_ge2,
                self.parametros.umbral_ge1_d, self.parametros.diferencia_ge1_d,
                self.parametros.diferencia_ge2)
            if sostiene_ahora and ahora-self.ocular_inicio >= minimo:
                return self.emitir(self.ocular, self.ocular_inicio, ahora, "OCULAR"), s, metricas, boca, ojos_raw
            return None, s, metricas, boca, ojos_raw

        # Retención bucal: un candidato de ojos que aparece en la misma
        # ventana tiene prioridad; nunca confirmamos boca mientras hay
        # evidencia ocular vigente.
        if self.boca_listo is not None and boca != "NEUTRO":
            if ahora-self.boca_listo >= RETENCION_BUCAL:
                self.estado = "BOCA CONFIRMADA"
                return self.emitir(boca, self.boca_inicio, ahora, "BOCA"), s, metricas, boca, ojos_raw
            self.estado = "RETENCION BUCAL"
        else:
            self.estado = "SIN CANDIDATO"
        return None, s, metricas, boca, ojos_raw

    def emitir(self, evento, inicio_candidato, ahora, origen):
        self.ultimo = evento
        self.ultimo_inicio_candidato = inicio_candidato
        self.ultima_latencia = (ahora - inicio_candidato if inicio_candidato is not None else None)
        self.ultimo_origen = origen
        self.bloqueado = True
        self.neutro_inicio = None
        self.ocular = None
        self.ocular_inicio = None
        self.ocular_ultimo = None
        self.boca_listo = None
        self.estado = "EVENTO: " + evento
        return evento

