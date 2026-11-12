"""Servicio PySide6 de una sola salida, consumible por la interfaz de Val.

Tres políticas: CATEGORIAS / FRASES / CONFIRMAR_APAGADO. Después del evento
el hilo finaliza, liberando la cámara, y la interfaz decide la navegación.
"""
import threading
import time
from PySide6.QtCore import QThread, QObject, Signal, Slot
from reconocimiento_vexa.parametros import ParametrosFaciales, EVENTOS_PUBLICOS, MODOS
from reconocimiento_vexa.calibracion.perfiles import cargar_calibracion
from reconocimiento_vexa.facial.camara import CamaraFacial, imagen_espejo
from reconocimiento_vexa.facial.motor import Integrador, TIEMPO_ESTABILIDAD, RETENCION_BUCAL, REARME_GLOBAL, SEG_GE1, SEG_GE2
from reconocimiento_vexa.facial.dobles import InterpretadorTemporal, VENTANA_SEGUNDO, GRACIA_CONFIRMACION


class _HiloReconocimiento(QThread):
    fotograma = Signal(object)
    progreso = Signal(str, float, str)
    evento_final = Signal(str)
    neutro_sostenido = Signal(float)
    error = Signal(str)

    def __init__(self, modo, parametros, indice_camara=0):
        super().__init__()
        self.modo=modo
        self.parametros=parametros
        self.indice_camara=indice_camara
        self._stop=threading.Event()

    def detener(self):
        self._stop.set()

    def _progreso(self,integ,inter,boca,ahora):
        if integ.ocular is not None and integ.ocular_inicio is not None:
            total=SEG_GE2 if integ.ocular=='GE2' else SEG_GE1
            return (f'Candidato {integ.ocular}', min(1.,(ahora-integ.ocular_inicio)/total),
                    f'Mantener {integ.ocular}')
        if integ.bloqueado:
            fraccion=0. if integ.neutro_inicio is None else (ahora-integ.neutro_inicio)/REARME_GLOBAL
            return ('Rearme',min(1.,fraccion),'Volver a expresión neutra')
        if self.modo=='CATEGORIAS' and inter.pendiente:
            if inter.t_rearme is None:
                return ('Rearme',0.,'Relajar la cara antes de repetir')
            restante=inter.restante(ahora)
            if inter.estado=='SEGUNDO_EN_VALIDACION':
                return ('Segundo gesto',min(1.,(ahora-inter.t_rearme)/(VENTANA_SEGUNDO+GRACIA_CONFIRMACION)),'Confirmando segundo gesto')
            return ('Segundo gesto',min(1.,1.-restante/VENTANA_SEGUNDO),'Repetir el mismo gesto')
        if boca in {'G1','G2','G3','G4','G5'} and integ.boca_inicio is not None:
            completo=TIEMPO_ESTABILIDAD+RETENCION_BUCAL
            lapso=ahora-integ.boca_inicio
            return (f'Candidato {boca}',min(1.,max(0.,lapso)/completo),'Mantener gesto')
        return ('Disponible',0.,'Realizar un gesto')

    def run(self):
        try:
            integ=Integrador(self.parametros)
            inter=InterpretadorTemporal() if self.modo=='CATEGORIAS' else None
            # Todos los ciclos exigen volver a neutro, para evitar acciones
            # repetidas si el usuario mantiene el gesto al cambiar de pantalla.
            # Es especialmente importante al confirmar apagado por segundo GE2.
            integ.bloqueado=True
            integ.neutro_inicio=None
            inicio_neutro_confirmacion=None
            with CamaraFacial(self.indice_camara) as camara:
                while not self._stop.is_set():
                    ahora,frame,lm,scores=camara.leer()
                    evento,s,metricas,boca,ojos=integ.actualizar(
                        lm,scores,frame.shape[1],frame.shape[0],ahora)
                    if self.modo=='CONFIRMAR_APAGADO':
                        en_neutro=(not integ.bloqueado and boca=='NEUTRO'
                            and ojos=='NEUTRO/INCIERTO' and s is not None
                            and max(s['eyeBlinkLeft'],s['eyeBlinkRight'])<self.parametros.blink_neutral_max)
                        if en_neutro:
                            if inicio_neutro_confirmacion is None:
                                inicio_neutro_confirmacion=ahora
                            self.neutro_sostenido.emit(ahora-inicio_neutro_confirmacion)
                        else:
                            inicio_neutro_confirmacion=None
                    finales=[]
                    if self.modo=='CATEGORIAS':
                        # G5 y G10 no existen en las ocho categorías; excluir
                        # el evento antes de la interpretación de dobles.
                        base=evento if evento in {'G1','G2','G3','G4','GE2'} else None
                        b=boca if boca in {'G1','G2','G3','G4'} else 'NEUTRO'
                        finales=[g for g,_ in inter.actualizar(base,ahora,integ,b)]
                    else:
                        finales=[evento] if evento else []
                    permitidos=MODOS[self.modo]
                    validos=[g for g in finales if g in permitidos]
                    if validos and not self._stop.is_set():
                        self.evento_final.emit(EVENTOS_PUBLICOS[validos[0]])
                        break
                    titulo,frac,detalle=self._progreso(integ,inter,boca,ahora)
                    self.progreso.emit(titulo,float(frac),detalle)
                    self.fotograma.emit(imagen_espejo(frame))
        except Exception as exc:
            self.error.emit(f'Error de reconocimiento facial: {exc}')


class ServicioReconocimiento(QObject):
    """Val puede crear uno y reutilizarlo durante la navegación de VEXA.

    iniciar(modo) inicia la detección; al confirmar una acción se emite
    evento_final("G6F"), etc. Si Val cambia de modo antes del cierre del
    hilo anterior, se espera su liberación y luego comienza el modo nuevo.
    """
    fotograma = Signal(object)
    progreso = Signal(str,float,str)
    evento_final = Signal(str)
    neutro_sostenido = Signal(float)
    error = Signal(str)
    terminado = Signal()

    def __init__(self,id_perfil,indice_camara=0,modo_experimental=False,carpeta_calibraciones=None,parent=None):
        super().__init__(parent)
        self.id_perfil=id_perfil
        self.indice_camara=indice_camara
        self.modo_experimental=modo_experimental
        self.carpeta_calibraciones=carpeta_calibraciones
        self.hilo=None
        self._pendiente=None

    def iniciar(self,modo):
        if modo not in MODOS: raise ValueError(f'Modo de VEXA desconocido: {modo}')
        if self.hilo is not None and not self.hilo.isFinished():
            self._pendiente=modo
            self.hilo.detener()
            return
        self._iniciar_hilo(modo)

    def _iniciar_hilo(self,modo):
        try:
            parametros=(ParametrosFaciales() if self.modo_experimental
                        else cargar_calibracion(self.id_perfil,self.carpeta_calibraciones))
        except Exception as exc:
            self.error.emit(str(exc))
            return
        hilo=_HiloReconocimiento(modo,parametros,self.indice_camara)
        self.hilo=hilo
        hilo.fotograma.connect(self.fotograma)
        hilo.progreso.connect(self.progreso)
        hilo.evento_final.connect(self.evento_final)
        hilo.neutro_sostenido.connect(self.neutro_sostenido)
        hilo.error.connect(self.error)
        hilo.finished.connect(self._al_terminar)
        hilo.start()

    @Slot()
    def _al_terminar(self):
        self.terminado.emit()
        siguiente=self._pendiente
        self._pendiente=None
        if siguiente:
            self._iniciar_hilo(siguiente)

    def detener(self):
        self._pendiente=None
        if self.hilo is not None and self.hilo.isRunning():
            self.hilo.detener()

    def cerrar(self):
        """Llamar al salir de VEXA; espera liberación de webcam."""
        self.detener()
        if self.hilo is not None and self.hilo.isRunning():
            self.hilo.wait(2500)
