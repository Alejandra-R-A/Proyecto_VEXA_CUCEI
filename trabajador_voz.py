from PySide6.QtCore import QObject, Signal, Slot

from voz_vexa import sintetizar_frase


class TrabajadorVoz(QObject):
    audio_listo = Signal(bytes)
    error = Signal(str)
    terminado = Signal()

    def __init__(self, texto, tipo_voz="Femenina"):
        super().__init__()
        self.texto = texto
        self.tipo_voz = tipo_voz

    @Slot()
    def ejecutar(self):
        try:
            audio = sintetizar_frase(
                self.texto,
                self.tipo_voz
            )

            self.audio_listo.emit(audio)

        except Exception as exc:
            self.error.emit(str(exc))

        finally:
            self.terminado.emit()