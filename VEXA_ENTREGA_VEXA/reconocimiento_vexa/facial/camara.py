"""Acceso compartido al mismo Face Landmarker para calibración y reconocimiento.

El fotograma se procesa SIN invertirlo en MediaPipe (igual que en las pruebas).
La transformación de espejo se aplica exclusivamente al mostrarlo y al
calcular las métricas bucales, exactamente como en Integrador.
"""
from pathlib import Path
import time
import cv2
import mediapipe as mp
import numpy as np
from reconocimiento_vexa.facial.motor import calcular_metricas, LandmarkEspejado, CLAVES

MODELO = Path(__file__).resolve().parents[1] / 'modelos' / 'face_landmarker.task'
PUNTOS_BOCA = (33,263,61,291,13,14,0,17)
PUNTOS_OJOS = (33,133,159,145,263,362,386,374)


class CamaraFacial:
    def __init__(self, indice=0):
        self.indice=indice
        self.cap=None
        self.modelo=None
        self.inicio=None
        self.ultimo_ms=-1

    def __enter__(self):
        if not MODELO.exists():
            raise FileNotFoundError(f'Falta el modelo Face Landmarker: {MODELO}')
        try:
            opciones=mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(MODELO)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_faces=1, output_face_blendshapes=True,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5)
            self.modelo=mp.tasks.vision.FaceLandmarker.create_from_options(opciones)
            # CAP_DSHOW solamente se usa en Windows, como en el script validado.
            self.cap=cv2.VideoCapture(self.indice, cv2.CAP_DSHOW) if __import__('sys').platform=='win32' else cv2.VideoCapture(self.indice)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap=cv2.VideoCapture(self.indice)
            if not self.cap.isOpened():
                raise RuntimeError('No se pudo abrir la cámara. Revisa conexión y permisos.')
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
            self.inicio=time.monotonic()
            self.ultimo_ms=-1
            return self
        except BaseException:
            self.__exit__(None,None,None)
            raise

    def __exit__(self,exc_tipo,exc,trace):
        if self.cap:
            self.cap.release()
            self.cap=None
        if self.modelo:
            self.modelo.close()
            self.modelo=None

    def leer(self):
        ok,frame=self.cap.read()
        if not ok: raise RuntimeError('No se pudo obtener un fotograma de la cámara.')
        ahora=time.monotonic()
        ms=max(self.ultimo_ms+1,int((ahora-self.inicio)*1000))
        self.ultimo_ms=ms
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        imagen=mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb))
        r=self.modelo.detect_for_video(imagen,ms)
        lm=r.face_landmarks[0] if r.face_landmarks else None
        scores=({x.category_name:float(x.score) for x in r.face_blendshapes[0]}
                if r.face_blendshapes else None)
        if scores is not None and not all(k in scores for k in CLAVES): scores=None
        return ahora,frame,lm,scores


def muestra_numerica(lm,scores,frame,ahora):
    if lm is None or scores is None:return None
    alto,ancho=frame.shape[:2]
    m=calcular_metricas([LandmarkEspejado(x) for x in lm],ancho,alto)
    if m is None: return None
    return {**m, **{k:float(scores[k]) for k in CLAVES}, 'tiempo_monotonico':ahora}


def imagen_espejo(frame,lm=None,condicion=None):
    """Devuelve QImage autocontenida. QPixmap se construye EN el hilo Qt principal."""
    from PySide6.QtGui import QImage
    bgr=cv2.flip(frame,1)
    if lm and condicion:
        if condicion in ('GE1_D','GE1_I','GE2','PARPADEO'):
            indices=PUNTOS_OJOS
        elif condicion.startswith('NEUTRAL'):
            indices=PUNTOS_BOCA+PUNTOS_OJOS
        else: indices=PUNTOS_BOCA
        h,w=frame.shape[:2]
        for i in indices:
            p=lm[i]
            cv2.circle(bgr,(int((1.0-p.x)*w),int(p.y*h)),2,(65,240,140),-1)
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    h,w=rgb.shape[:2]
    return QImage(rgb.data,w,h,rgb.strides[0],QImage.Format_RGB888).copy()
