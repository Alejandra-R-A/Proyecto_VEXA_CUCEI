# Guía corta para integrar MediaPipe en VEXA

**No reemplazar tu `main.py` ni tu `database.py`.** Copia la carpeta `reconocimiento_vexa/` a tu proyecto e instala las dependencias de `requirements.txt` en el mismo entorno virtual de tu interfaz.

## 1. Mostrar el módulo de calibración en tu pantalla

```python
from reconocimiento_vexa.calibracion.ventana import VentanaCalibracion

calibracion = VentanaCalibracion(id_perfil='ID_PERSISTENTE_DE_TU_PERFIL')
stack.addWidget(calibracion)  # Tu QStackedWidget real
calibracion.calibracion_finalizada.connect(funcion_que_navega_al_siguiente_paso)
calibracion.calibracion_no_valida.connect(funcion_que_muestra_aviso)
calibracion.calibracion_cancelada.connect(funcion_para_regresar)
```

La ventana **ya contiene todo**: vídeo espejado, landmarks, instrucciones por gesto, pausa, repetición, sonidos, cálculo y guardado de umbrales. Al salir de ella, llama `calibracion.detener()`; no abras reconocimiento mientras la cámara de calibración esté activa.

## 2. Detectar eventos finales

```python
from reconocimiento_vexa.servicios.reconocimiento import ServicioReconocimiento

facial = ServicioReconocimiento(id_perfil='ID_PERSISTENTE_DE_TU_PERFIL')
facial.evento_final.connect(tu_funcion_para_recibir_un_gesto)
facial.error.connect(tu_funcion_para_mostrar_error)

facial.iniciar('CATEGORIAS')
# o facial.iniciar('FRASES')
# o facial.iniciar('CONFIRMAR_APAGADO')
```

Cada vez se entrega **una única cadena**, como `G3F`, `G6F`, `GE1_DF` o `GE2F`. Tras emitirla, la cámara se cierra. La interfaz decide la acción y vuelve a llamar `facial.iniciar(...)` cuando esté lista.

- **Categorías:** G1F–G4F, G6F–G9F y GE2F.
- **Frases:** G1F–G5F, GE1_DF, GE1_IF y GE2F.
- **Confirmación de apagado:** solo un **segundo GE2F**, después de regresar a neutro y completar rearme. Puedes conectar `facial.neutro_sostenido.connect(callback_segundos_neutros)` para controlar cancelación por neutro prolongado, según la duración que decidan.

Para vista previa compacta:

```python
from reconocimiento_vexa.widgets.vista_previa import VistaPreviaReconocimiento

preview = VistaPreviaReconocimiento()
preview.vincular(facial)
# Añade 'preview' a tu barra lateral o panel y muéstralo al iniciar un ciclo.
```

**Pruebas con perfil experimental:** si todavía no has hecho la calibración, usa explícitamente `ServicioReconocimiento(id_perfil=..., modo_experimental=True)`; nunca se activa como respaldo silencioso de un perfil sin calibrar.

Lee `LEEME_PRIMERO.md` para requisitos, parámetros, almacenamiento y límites de la validación. Se incluye `face_landmarker.task` y los sonidos; no hacen falta descargas adicionales de esos recursos.
