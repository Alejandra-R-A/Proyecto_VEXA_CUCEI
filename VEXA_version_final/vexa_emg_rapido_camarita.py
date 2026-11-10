import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "VEXA_ENTREGA_VEXA"))

import main
from reconocimiento_vexa.facial import dobles


VENTANA_ORIGINAL = dobles.VENTANA_SEGUNDO
VENTANA_PRUEBA = 0.90
UMBRALES_EMG = (11.0, 9.0)


def ejecutar():
    if abs(VENTANA_ORIGINAL - 1.20) > 0.000001:
        raise RuntimeError(
            "La ventana original ya no es 1.20 s. "
            "Se cancela la prueba."
        )

    main.inicializar_base_datos()

    app = QApplication(sys.argv)

    dobles.VENTANA_SEGUNDO = VENTANA_PRUEBA

    print("=" * 65)
    print("VEXA - PASO 1192: FACIAL + EMG RAPIDO")
    print("=" * 65)
    print("Ventana facial de prueba:", dobles.VENTANA_SEGUNDO)
    print("Ventana original en disco: SIN CAMBIOS")


    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout

    ClaseOriginal = main.VexaWindow

    class VexaConCamarita(ClaseOriginal):

        def __init__(self):
            self._vexa_vistas = []
            self._vexa_ultimo_frame = None
            self._vexa_error_visual = False
            super().__init__()

            self._vexa_timer = QTimer(self)
            self._vexa_timer.setInterval(83)
            self._vexa_timer.timeout.connect(
                self._vexa_pintar_frame
            )
            self._vexa_timer.start()

        def _vexa_agregar_vista(self, page):
            layout = page.layout()

            etiqueta = QLabel("Esperando c?mara...")
            etiqueta.setFixedSize(192, 144)
            etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
            etiqueta.setStyleSheet(
                "background-color: #101827;"
                "color: #BFDBFE;"
                "border: 2px solid #60A5FA;"
                "border-radius: 9px;"
            )

            fila = QHBoxLayout()
            fila.addStretch()
            fila.addWidget(etiqueta)

            layout.insertLayout(0, fila)
            self._vexa_vistas.append(etiqueta)

        def create_categories_page(self):
            page = super().create_categories_page()
            self._vexa_agregar_vista(page)
            return page

        def create_phrases_page(self):
            page = super().create_phrases_page()
            self._vexa_agregar_vista(page)
            return page

        def preparar_reconocimiento_facial(self):
            resultado = super().preparar_reconocimiento_facial()

            if not resultado:
                return resultado

            servicio = self.servicio_reconocimiento

            if servicio is None:
                return resultado

            servicio.indice_camara = 1

            if not getattr(
                servicio,
                "_vexa_webcam_externa_anunciada",
                False
            ):
                print(
                    "[VEXA CAMARITA] Webcam externa seleccionada: 1"
                )
                servicio._vexa_webcam_externa_anunciada = True

            if not getattr(
                servicio,
                "_vexa_camarita_conectada",
                False
            ):
                servicio.fotograma.connect(
                    self._vexa_recibir_frame
                )
                servicio._vexa_camarita_conectada = True
                print("[CAMARITA] Se?al fotograma conectada.")

            return resultado

        def _vexa_recibir_frame(self, frame):
            if not getattr(self, "_vexa_frame_detectado", False):
                print(
                    "[CAMARITA] Primer fotograma recibido:",
                    type(frame).__name__,
                    getattr(frame, "shape", None)
                )
                self._vexa_frame_detectado = True

            self._vexa_ultimo_frame = frame

        def _vexa_pintar_frame(self):
            frame = self._vexa_ultimo_frame

            if frame is None:
                return

            self._vexa_ultimo_frame = None

            try:
                if isinstance(frame, QImage):
                    imagen = frame
                else:
                    
                    import cv2

                    rgb = cv2.cvtColor(
                        frame,
                        cv2.COLOR_BGR2RGB
                    )

                    alto, ancho, canales = rgb.shape

                    imagen = QImage(
                        rgb.data,
                        ancho,
                        alto,
                        ancho * canales,
                        QImage.Format.Format_RGB888
                    ).copy()

                if imagen.isNull():
                    return

                pixmap = QPixmap.fromImage(imagen)

                if not getattr(self, "_vexa_imagen_detectada", False):
                    print(
                        "[CAMARITA] Imagen Qt creada:",
                        pixmap.width(),
                        "x",
                        pixmap.height()
                    )
                    self._vexa_imagen_detectada = True

                for etiqueta in self._vexa_vistas:
                    etiqueta.setPixmap(
                        pixmap.scaled(
                            etiqueta.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation
                        )
                    )

            except Exception as exc:
                if not self._vexa_error_visual:
                    print(
                        "[VEXA CAMARITA] Error visual:",
                        exc
                    )
                    self._vexa_error_visual = True


    ventana = VexaConCamarita()

    iniciado = ventana.iniciar_emg_vexa(
        puerto="COM10",
        umbrales=UMBRALES_EMG,
    )

    if not iniciado:
        print("[VEXA PRUEBA] EMG no pudo iniciarse.")
        print("[VEXA PRUEBA] Se cancela para evitar prueba sin EMG.")
        ventana.detener_emg_vexa()
        return 1

    app.aboutToQuit.connect(ventana.detener_emg_vexa)

    ventana.show()

    try:
        return app.exec()
    finally:
        ventana.detener_emg_vexa()
        dobles.VENTANA_SEGUNDO = VENTANA_ORIGINAL


if __name__ == "__main__":
    sys.exit(ejecutar())
