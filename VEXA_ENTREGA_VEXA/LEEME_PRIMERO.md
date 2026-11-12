# VEXA — Entrega integral de reconocimiento facial

**Versión de integración experimental, 25 de octubre de 2026.**

Este paquete contiene una **ventana completa de calibración individual**, el cálculo y guardado de **11 umbrales faciales**, tres modos de reconocimiento para VEXA, modelo Face Landmarker, archivos de sonido, vista previa compacta y dos aplicaciones de demostración. **No modifica** los archivos `main.py` ni `database.py` de la interfaz.

## 1. Requisitos y puesta en marcha (Windows)

Mantén tu entorno virtual `mpenv` de Python 3.10 y abre PowerShell desde la carpeta `VEXA_ENTREGA_VAL`.

```powershell
# Si aún no tienes un entorno virtual:
py -3.10 -m venv mpenv
.\mpenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Con el mismo entorno activo:

```powershell
python ejemplos/demo_calibracion.py
python ejemplos/demo_reconocimiento.py
# Solo para una prueba controlada, sin calibración individual:
python ejemplos/demo_reconocimiento.py --experimental
```

Ejecuta los ejemplos **desde la raíz del paquete**. Puede requerirse permiso de cámara en Windows. No abras a la vez otro programa que esté usando la webcam.

> **Estado de verificación:** en el entorno donde se preparó la entrega no estaban disponibles `mediapipe` ni `PySide6`, y no hay webcam de usuario. Se pudo revisar/compilar el código y probar por separado el cálculo numérico; **no se ha ejecutado la GUI ni probado físicamente la adquisición o la integración en el equipo de Val**. Esta entrega es para realizar la **prueba integral** solicitada, no un sistema clínicamente validado.

## 2. Integración dentro de la interfaz PySide6 de Val

Se debe copiar la carpeta `reconocimiento_vexa/` junto a su aplicación o dejarla en una ruta importable. No debe integrar los dos archivos de la carpeta `referencias_validadas`; sirven solamente como respaldo de los scripts originales.

### Calibración: insertar nuestro QWidget completo en su pantalla

```python
from reconocimiento_vexa.calibracion.ventana import VentanaCalibracion

# id_perfil debe ser el identificador persistente que ya usa la interfaz.
self.calibrador = VentanaCalibracion(id_perfil=id_perfil)
self.stack.addWidget(self.calibrador)  # Cambiar 'stack' al QStackedWidget real de Val
self.calibrador.calibracion_finalizada.connect(self.al_terminar_calibracion)
self.calibrador.calibracion_no_valida.connect(self.mostrar_error_calibracion)
self.calibrador.calibracion_cancelada.connect(self.volver)
self.calibrador.error.connect(self.mostrar_error_calibracion)
```

La ventana tiene sus **propias instrucciones, imagen espejada con landmarks por gesto, temporizadores, 10 repeticiones por condición, descansos, señales acústicas de tres frecuencias, botones, captura, cálculo de parámetros y guardado**. Val no necesita recrear sus controles. Al salir de esa pantalla debe llamar `self.calibrador.detener()` para liberar la cámara. Un error o cancelación **no sobrescribe** una calibración guardada previamente.

La calibración individual captura: `NEUTRAL_CERRADO`, `NEUTRAL_SEPARADO`, G1–G5, `GE1_D`, `GE1_I`, `GE2` y `PARPADEO`. Para la fase de parpadeo se pide parpadear una vez normalmente durante los dos segundos de captura. Entre condiciones hay una pausa manual sin límite. La duración mínima automática es aproximadamente **12 min 50 s** más las pausas manuales, si no hace falta repetir capturas.

### Reconocimiento: servicio reutilizable

```python
from reconocimiento_vexa.servicios.reconocimiento import ServicioReconocimiento
from reconocimiento_vexa.widgets.vista_previa import VistaPreviaReconocimiento

self.facial = ServicioReconocimiento(id_perfil=id_perfil)
self.facial.evento_final.connect(self.recibir_gesto_facial)
self.facial.error.connect(self.mostrar_error_reconocimiento)

self.preview_facial = VistaPreviaReconocimiento()
self.preview_facial.vincular(self.facial)
# Insertar self.preview_facial en la región que Val prefiera.

# Al entrar a una pantalla:
self.preview_facial.show()
self.facial.iniciar('CATEGORIAS')
# O bien:
self.facial.iniciar('FRASES')
# Tras GE2F, Val muestra su cuadro de confirmación:
self.facial.iniciar('CONFIRMAR_APAGADO')

# Al cambiar a una pantalla sin reconocimiento:
self.facial.detener()
# Al cerrar la aplicación:
self.facial.cerrar()
```

`evento_final` se emite **una sola vez por ciclo**. El hilo deja de leer la cámara y la libera. Al comenzar **cualquier** nuevo ciclo, exige primero 0.40 s de expresión neutra para evitar repetir un gesto que el usuario todavía mantiene de la pantalla anterior. Val ejecuta la acción y, si desea continuar, vuelve a invocar `iniciar` con el modo del nuevo menú. Si solicita otro modo mientras el hilo anterior termina, el servicio espera automáticamente a que finalice el anterior.

El evento se entrega como una **cadena** terminada en `F` (facial), sin nombres de categorías ni frases. Val mapea ese valor a su acción según el menú activo.

| Modo | Eventos finales permitidos | Notas |
|---|---|---|
| `CATEGORIAS` | `G1F`, `G2F`, `G3F`, `G4F`, `G6F`, `G7F`, `G8F`, `G9F`, `GE2F` | Las dobles G6–G9 corresponden a dos ejecuciones de G1–G4, con rearme y ventana de 1.50 s. G5/G10 se excluyen. |
| `FRASES` | `G1F` a `G5F`, `GE1_DF`, `GE1_IF`, `GE2F` | Selección directa de **cinco frases** por categoría; sin esperar segundo gesto. Ambas variantes GE1 significan regresar. |
| `CONFIRMAR_APAGADO` | Solo `GE2F` | Se exige **regreso a neutro y rearme** antes de poder reconocer un segundo cierre bilateral. |

**Apagado:** Val controla el cuadro de confirmación y la cuenta regresiva. Nuestro módulo reconoce exclusivamente el segundo GE2; la temporización/cancelación de la ventana seguirá siendo responsabilidad de la interfaz hasta que se acuerden reglas de producto más precisas. El servicio emite `neutro_sostenido(segundos)` en modo `CONFIRMAR_APAGADO` para que Val pueda cancelar cuando la expresión neutra haya durado el tiempo decidido para su ventana.

### Perfil experimental vs. perfil individual

- Por defecto, `ServicioReconocimiento` **exige una calibración válida para el ID del perfil**.
- Para pruebas con los umbrales que ya funcionaron en el detector experimental, Val puede instanciar `ServicioReconocimiento(..., modo_experimental=True)` **explícitamente**.
- Los datos se guardan fuera del código fuente, en `~/.vexa/calibraciones_faciales/` (en Windows, carpeta de usuario). Puede pasarse `carpeta_calibraciones` a ambos componentes para escoger otra ubicación persistente.
- El nombre del archivo se obtiene de un hash del ID del perfil para evitar rutas inseguras. El JSON conserva el ID, los parámetros, la versión compatible y un resumen de los resultados. La interfaz principal de Val sigue siendo dueña de los perfiles.

## 3. De dónde viene la detección

Se han conservado los scripts exactos suministrados en `reconocimiento_vexa/referencias_validadas/`. El código operativo se encuentra en:

- `facial/motor.py`: versión parametrizable de `Integrador`; conserva fórmulas, prioridades, retención 0.30 s, rearme 0.40 s, confirmación bucal 0.35 s, GE1 0.70 s, GE2 1.00 s y mediana de 5 fotogramas. Se separaron los umbrales `diferencia_ge1_i` y `diferencia_ge2`, ambos inicialmente 0.22.
- `facial/dobles.py`: `InterpretadorTemporal` del script de dobles (ventana de 1.50 s después del rearme y gracia 0.85 s); se invoca solo en categorías.
- `facial/camara.py`: una única cámara, un único Face Landmarker con blendshapes por sesión; métricas en espejo con **la misma convención anatómica original**.
- `calibracion/umbrales.py`: mediana por repetición; **7 repeticiones para ajuste y 3 reservadas** para comprobar etiquetas, con búsqueda de umbrales en caso de solapamiento. Este método es un procedimiento automático de prototipo, **no está aún validado con diferentes sujetos**.
- `calibracion/ventana.py`: ventana PySide6 integrada y autónoma para el protocolo completo.
- `calibracion/perfiles.py`: almacenamiento por ID de perfil sin sobrescribir registros con calibraciones fallidas.

La calibración utiliza `WN`, `MAR`, `HN_ext` y `A_D_corr` (G1–G5), y los blendshapes `eyeBlinkLeft` y `eyeBlinkRight` (GE1/GE2), además de comprobar la expresión neutra y el parpadeo. Los parámetros temporales permanecen constantes. La calibración **no resuelve todavía falsos positivos de G1/G2 por giros de cabeza**: el usuario debe conservar la postura frontal durante uso y calibración.

## 4. Limitaciones que Val debe conocer

1. La prueba integral con cámara, interfaz real y varios perfiles **está pendiente**. La configuración actual se considera un **prototipo experimental**, no un dispositivo médico validado.
2. Los resultados de calibración se aprueban mediante clasificación de medianas reservadas; esto **no sustituye una prueba temporal en tiempo real**. Se solicita una prueba general del sistema integrado, tal como decidió el equipo, pero no se exige una prueba separada por archivo.
3. La calibración de diez repeticiones por once condiciones es larga para algunos usuarios. Se contempla pausa y descansos; una versión futura podrá reducir repeticiones después de evaluarla.
4. El código de validación EMG **no está incluido**: se desarrollará aparte sin cambiar el contrato de eventos que recibe lainterfaz. Los eventos oculares necesitarán tratamiento específico porque los canales sEMG previstos son periorales.
5. La política exacta de cancelación de apagado por neutro prolongado y el tiempo de la cuenta regresiva siguen por acordarse. El reconocimiento del segundo GE2 sí exige rearme.
6. Si se inserta el widget de calibración dentro de una pantalla con tamaño reducido, deberá proporcionar al menos unos 680 px horizontales; puede envolverlo en un contenedor desplazable.

## 5. Signos anatómicos y nomenclatura

- G1: media sonrisa **derecha anatómica**. G2: media sonrisa **izquierda anatómica**.
- G3: labios comprimidos. G4: sonrisa con dientes. G5: beso.
- G6=G1×2, G7=G2×2, G8=G3×2, G9=G4×2, G10=G5×2 (G10 no se usa en los menús actuales).
- GE1_D: guiño derecho; GE1_I: guiño izquierdo; GE2: cierre bilateral.
- Los identificadores internos permanecen G1–G10, GE1_D/I y GE2. **Solo en la salida hacia la interfaz se añade el sufijo `F`**, para evitar colisiones con sus identificadores G6/G7 históricos.

## 6. Entrega y propiedad de archivos

Este paquete **no incluye ni altera** `main.py`, `database.py`, `trabajador_voz.py` ni recursos de la interfaz. Debe incorporarse a su proyecto existente mediante importaciones Python, no reemplazando su aplicación.

Los archivos originales de referencia se conservan para facilitar revisión técnica y evitar perder la versión experimental validada.
