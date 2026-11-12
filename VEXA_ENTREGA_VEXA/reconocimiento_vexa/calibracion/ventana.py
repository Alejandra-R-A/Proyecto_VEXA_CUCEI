"""Ventana completa de calibración facial para integrar en el QStackedWidget de Val.

Esta clase es un QWidget autónomo: se ocupa de la cámara, el protocolo,
las instrucciones, los sonidos, las repeticiones y el almacenamiento.
Val solo crea este widget con el ID de perfil y escucha sus señales.
"""
from collections import defaultdict
from pathlib import Path
import threading
import time
from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox, QFrame,
)
from reconocimiento_vexa.facial.camara import CamaraFacial, imagen_espejo, muestra_numerica
from reconocimiento_vexa.calibracion.umbrales import CONDICIONES, ETIQUETAS, calcular_calibracion, CalibracionInvalida
from reconocimiento_vexa.calibracion.perfiles import guardar_calibracion

try:
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:
    QSoundEffect=None


# Segundos: se conserva el protocolo experimental propuesto.
DURACIONES={'PREPARACION':3.0,'TRANSICION':0.5,'CAPTURA':2.0,'DESCANSO':1.5}
ETAPAS=['PREPARACION','TRANSICION','CAPTURA','DESCANSO']
REPETICIONES=10
MIN_FRAMES_VALIDOS=10
MIN_COBERTURA_S=1.0
REINTENTOS_AUTOMATICOS=2


class _HiloCamaraCalibracion(QThread):
    fotograma = Signal(object)
    muestra = Signal(object)
    error = Signal(str)

    def __init__(self,indice=0):
        super().__init__()
        self.indice=indice
        self._detener=threading.Event()
        self._lock=threading.Lock()
        self._condicion=None

    def establecer_gesto(self,gesto):
        with self._lock:self._condicion=gesto

    def detener(self):
        self._detener.set()

    def run(self):
        try:
            with CamaraFacial(self.indice) as camara:
                while not self._detener.is_set():
                    ahora,frame,lm,scores=camara.leer()
                    with self._lock:condicion=self._condicion
                    self.fotograma.emit(imagen_espejo(frame,lm,condicion))
                    self.muestra.emit(muestra_numerica(lm,scores,frame,ahora))
        except Exception as exc:
            self.error.emit(f'Error durante calibración: {exc}')


class VentanaCalibracion(QWidget):
    calibracion_finalizada = Signal(str, object)  # ID de perfil, ruta del JSON guardado
    calibracion_no_valida = Signal(str)            # Resumen del error
    calibracion_cancelada = Signal()
    error = Signal(str)

    def __init__(self,id_perfil,indice_camara=0,carpeta_calibraciones=None,parent=None):
        super().__init__(parent)
        self.id_perfil=id_perfil
        self.indice_camara=indice_camara
        self.carpeta_calibraciones=carpeta_calibraciones
        self.plan=list(ETIQUETAS)
        self.capturas=defaultdict(list)
        self.posicion=0
        self.repeticion=0
        self.reintentos=0
        self.buffer=[]
        self.fase='SIN_INICIAR'
        self._fase_antes_pausa=None
        self.t_inicio=0.
        self.hilo=None
        self.sonidos={}
        self._construir_ui()
        self._preparar_sonidos()
        self.timer=QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self._mostrar_estado('Presiona Iniciar para comenzar. Colócate de frente a la cámara.')

    def _construir_ui(self):
        self.setMinimumWidth(680)
        principal=QVBoxLayout(self)
        titulo=QLabel('Calibración facial individual — VEXA')
        titulo.setStyleSheet('font-size:21px;font-weight:600;')
        principal.addWidget(titulo)
        self.gesto=QLabel('Mantén la cabeza centrada y con iluminación uniforme.')
        self.gesto.setStyleSheet('font-size:17px;')
        self.gesto.setWordWrap(True)
        principal.addWidget(self.gesto)
        cuerpo=QHBoxLayout()
        self.video=QLabel('La cámara aparecerá aquí.')
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(440,315)
        self.video.setStyleSheet('background:#1e2930;color:#eee;border-radius:7px;')
        cuerpo.addWidget(self.video,3)
        lado=QVBoxLayout()
        self.contador=QLabel('Repetición 0 de 10')
        self.etapa=QLabel('SIN INICIAR')
        self.instruccion=QLabel('Inicia cuando estés listo.')
        self.instruccion.setWordWrap(True)
        self.condicion_barra=QProgressBar()
        self.condicion_barra.setRange(0,100)
        for v in (self.contador,self.etapa,self.instruccion,self.condicion_barra):lado.addWidget(v)
        lado.addStretch()
        cuerpo.addLayout(lado,1)
        principal.addLayout(cuerpo)
        self.progreso_total=QProgressBar()
        self.progreso_total.setRange(0,100)
        principal.addWidget(QLabel('Avance general del protocolo'))
        principal.addWidget(self.progreso_total)
        self.estado=QLabel('')
        self.estado.setWordWrap(True)
        principal.addWidget(self.estado)
        botones=QHBoxLayout()
        self.b_iniciar=QPushButton('Iniciar / Continuar')
        self.b_pausar=QPushButton('Pausar')
        self.b_repetir=QPushButton('Repetir captura')
        self.b_cancelar=QPushButton('Cancelar')
        for b in [self.b_iniciar,self.b_pausar,self.b_repetir,self.b_cancelar]:botones.addWidget(b)
        principal.addLayout(botones)
        self.b_iniciar.clicked.connect(self.iniciar_o_continuar)
        self.b_pausar.clicked.connect(self.pausar)
        self.b_repetir.clicked.connect(self.repetir)
        self.b_cancelar.clicked.connect(self.cancelar)
        self.b_pausar.setEnabled(False)
        self.b_repetir.setEnabled(False)

    def _preparar_sonidos(self):
        if QSoundEffect is None:return
        carpeta=Path(__file__).resolve().parents[1] / 'sonidos'
        for fase,archivo in [('PREPARACION','inicio_600hz.wav'),
                              ('CAPTURA','captura_950hz.wav'),
                              ('DESCANSO','descanso_450hz.wav')]:
            ruta=carpeta/archivo
            if ruta.exists():
                audio=QSoundEffect(self)
                audio.setSource(QUrl.fromLocalFile(str(ruta)))
                audio.setVolume(0.45)
                self.sonidos[fase]=audio

    def _sonar(self,fase):
        audio=self.sonidos.get(fase)
        if audio and audio.isLoaded():audio.play()
        else:QApplication.beep()

    def _actual(self):
        return self.plan[self.posicion]

    def _mostrar_estado(self,texto):
        self.estado.setText(texto)

    def _iniciar_hilo(self):
        if self.hilo is None or not self.hilo.isRunning():
            self.hilo=_HiloCamaraCalibracion(self.indice_camara)
            self.hilo.fotograma.connect(self._fotograma)
            self.hilo.muestra.connect(self._muestra)
            self.hilo.error.connect(self._error_camara)
            self.hilo.start()

    def iniciar_o_continuar(self):
        if self.fase in {'TERMINADO','CANCELADO'}:return
        if self.fase=='PAUSADO':
            anterior=self._fase_antes_pausa
            self._fase_antes_pausa=None
            if anterior=='DESCANSO':
                # La repetición ya se guardó; no duplicar capturas al reanudar.
                self._avanzar()
            else:
                self._establecer_fase('PREPARACION')
            return
        if self.fase in {'SIN_INICIAR','ESPERA_GESTO'}:
            self._iniciar_hilo()
            self.b_pausar.setEnabled(True)
            self.b_repetir.setEnabled(True)
            self._establecer_fase('PREPARACION')

    def _establecer_fase(self,fase):
        self.fase=fase
        self.t_inicio=time.monotonic()
        if fase=='CAPTURA':self.buffer=[]
        if fase in ('PREPARACION','CAPTURA','DESCANSO'):self._sonar(fase)
        if self.hilo is not None:
            self.hilo.establecer_gesto(self._actual() if fase not in {'TERMINADO','CANCELADO'} else None)
        self._refrescar_etiquetas()
        self.timer.start()

    def _refrescar_etiquetas(self):
        condicion=self._actual()
        descripcion=dict(CONDICIONES)[condicion]
        self.gesto.setText(f'{condicion}: {descripcion}')
        self.contador.setText(f'Repetición {self.repeticion+1} de {REPETICIONES}  ·  Condición {self.posicion+1}/{len(self.plan)}')
        self.etapa.setText(self.fase.replace('_',' '))
        mensajes={
            'PREPARACION':'Adopta una postura frontal, prepara el gesto.',
            'TRANSICION':'Realiza el gesto ahora.',
            'CAPTURA':'Mantén la expresión. Para PARPADEO, parpadea una vez de forma natural.',
            'DESCANSO':'Relaja los músculos y vuelve a neutro.',
            'ESPERA_GESTO':'Puedes descansar. Presiona Continuar para pasar al siguiente gesto.',
            'PAUSADO':'Protocolo pausado. Continuar reinicia la preparación de esta repetición.',
        }
        self.instruccion.setText(mensajes.get(self.fase,self.fase))

    def _tick(self):
        if self.fase not in DURACIONES:return
        lapso=time.monotonic()-self.t_inicio
        total=DURACIONES[self.fase]
        self.condicion_barra.setValue(int(min(1.,lapso/total)*100))
        completadas=sum(len(self.capturas[g]) for g in ETIQUETAS)
        self.progreso_total.setValue(int(completadas/(len(ETIQUETAS)*REPETICIONES)*100))
        if lapso>=total:
            if self.fase=='PREPARACION':self._establecer_fase('TRANSICION')
            elif self.fase=='TRANSICION':self._establecer_fase('CAPTURA')
            elif self.fase=='CAPTURA':self._terminar_captura()
            elif self.fase=='DESCANSO':self._avanzar()

    def _fotograma(self,imagen):
        pix=QPixmap.fromImage(imagen)
        self.video.setPixmap(pix.scaled(self.video.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))

    def _muestra(self,datos):
        if (self.fase=='CAPTURA' and datos is not None
                and self.t_inicio <= datos['tiempo_monotonico'] <= self.t_inicio+DURACIONES['CAPTURA']):
            self.buffer.append(datos)

    def _terminar_captura(self):
        valido=len(self.buffer)>=MIN_FRAMES_VALIDOS
        if valido:
            valido=(self.buffer[-1]['tiempo_monotonico']-self.buffer[0]['tiempo_monotonico'] >= MIN_COBERTURA_S)
        if valido:
            self.capturas[self._actual()].append(list(self.buffer))
            self.reintentos=0
            self._mostrar_estado('Captura registrada correctamente.')
            self._establecer_fase('DESCANSO')
        else:
            self.reintentos+=1
            self._mostrar_estado('Captura incompleta (rostro perdido o muy pocos fotogramas). Repetiremos.')
            if self.reintentos>REINTENTOS_AUTOMATICOS:
                self.fase='PAUSADO'
                self.timer.stop()
                self._refrescar_etiquetas()
                self._mostrar_estado('No se pudo capturar. Revisa iluminación y cámara; presiona Continuar para reintentar.')
            else:self._establecer_fase('PREPARACION')

    def _avanzar(self):
        self.repeticion+=1
        if self.repeticion<REPETICIONES:
            self._establecer_fase('PREPARACION')
            return
        self.repeticion=0
        self.posicion+=1
        if self.posicion>=len(self.plan):
            self._calcular_y_guardar()
            return
        self.fase='ESPERA_GESTO'
        self.timer.stop()
        self._refrescar_etiquetas()
        self._mostrar_estado('Condición completada. Descansa el tiempo que necesites antes de continuar.')

    def pausar(self):
        if self.fase in DURACIONES:
            self._fase_antes_pausa=self.fase
            self.timer.stop()
            self.fase='PAUSADO'
            self.buffer=[]
            self._refrescar_etiquetas()

    def repetir(self):
        if self.fase in DURACIONES or self.fase in {'PAUSADO','ESPERA_GESTO'}:
            if (self.fase=='DESCANSO' or (self.fase=='PAUSADO'
                    and self._fase_antes_pausa=='DESCANSO')) and self.capturas[self._actual()]:
                # La repetición que terminó hace un momento debe reemplazarse.
                self.capturas[self._actual()].pop()
            self.buffer=[]
            self._fase_antes_pausa=None
            self.reintentos=0
            # No elimina la repetición previa ya aceptada; repite la pendiente.
            self._establecer_fase('PREPARACION')

    def _calcular_y_guardar(self):
        self.timer.stop()
        self.fase='CALCULANDO'
        self._mostrar_estado('Calculando y verificando umbrales faciales...')
        QApplication.processEvents()
        try:
            parametros,informe=calcular_calibracion(self.capturas)
            if not informe['valida']:
                fallos=[k for k,v in informe['evaluacion_por_condicion'].items()
                        if v['aciertos']<(2 if k in {'G1','G2','G3','G4','G5','GE1_D','GE1_I','GE2'} else 3)]
                self._preparar_repeticion_condiciones(fallos)
                msg='Calibración no aprobada. Repetir condiciones: '+', '.join(fallos)
                self._mostrar_estado(msg)
                self.calibracion_no_valida.emit(msg)
                return
            ruta=guardar_calibracion(self.id_perfil,parametros,informe,self.carpeta_calibraciones)
            self.fase='TERMINADO'
            self.b_iniciar.setEnabled(False)
            self.b_pausar.setEnabled(False)
            self.b_repetir.setEnabled(False)
            self._detener_camara()
            self.progreso_total.setValue(100)
            self._mostrar_estado(f'Calibración válida y guardada. Archivo: {ruta}')
            self.calibracion_finalizada.emit(self.id_perfil,str(ruta))
        except (CalibracionInvalida,ValueError,OSError) as exc:
            # Error general: no asumimos que podamos aprovechar datos incompletos.
            # Dejar la interfaz en un estado recuperable para repetir protocolo.
            self.plan=list(ETIQUETAS)
            self.posicion=0
            self.repeticion=0
            self.capturas=defaultdict(list)
            self.fase='ESPERA_GESTO'
            self._refrescar_etiquetas()
            self._mostrar_estado(f'No se ha guardado la calibración: {exc}. Presiona Continuar para reiniciar.')
            self.calibracion_no_valida.emit(str(exc))

    def _preparar_repeticion_condiciones(self,fallos):
        if not fallos:
            self.fase='PAUSADO'
            return
        self.plan=fallos
        self.posicion=0
        self.repeticion=0
        for g in fallos:self.capturas[g]=[]
        self.fase='ESPERA_GESTO'
        self._refrescar_etiquetas()

    def _error_camara(self,mensaje):
        self.timer.stop()
        self.fase='PAUSADO'
        self._mostrar_estado(mensaje)
        self.error.emit(mensaje)

    def _detener_camara(self):
        if self.hilo is not None and self.hilo.isRunning():
            self.hilo.detener()
            if not self.hilo.wait(5000):
                raise RuntimeError('La cámara sigue cerrándose; no destruyas el widget todavía.')
        self.hilo=None

    def cancelar(self):
        if self.fase in {'TERMINADO','CANCELADO'}:return
        self.timer.stop()
        self.fase='CANCELADO'
        self._detener_camara()
        self._mostrar_estado('Calibración cancelada. No se han guardado datos nuevos.')
        self.calibracion_cancelada.emit()

    def detener(self):
        """Para Val: llamar al retirar este widget de la pantalla."""
        self.timer.stop()
        self._detener_camara()

    def closeEvent(self,event):
        self.detener()
        super().closeEvent(event)
