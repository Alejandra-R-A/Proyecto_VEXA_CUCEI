"""Vista compacta para insertar en la barra lateral de la interfaz de Val."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QProgressBar


class VistaPreviaReconocimiento(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setMaximumWidth(230)
        layout=QVBoxLayout(self)
        self.titulo=QLabel('Esperando gesto')
        self.titulo.setAlignment(Qt.AlignCenter)
        self.video=QLabel('Cámara inactiva')
        self.video.setMinimumSize(190,140)
        self.video.setAlignment(Qt.AlignCenter)
        self.barra=QProgressBar()
        self.barra.setRange(0,100)
        self.descripcion=QLabel('')
        self.descripcion.setWordWrap(True)
        self.descripcion.setAlignment(Qt.AlignCenter)
        for widget in [self.titulo,self.video,self.barra,self.descripcion]: layout.addWidget(widget)

    def vincular(self,servicio):
        servicio.fotograma.connect(self.mostrar_fotograma)
        servicio.progreso.connect(self.actualizar_progreso)
        servicio.evento_final.connect(self.al_evento)

    def mostrar_fotograma(self,imagen):
        pix=QPixmap.fromImage(imagen)
        self.video.setPixmap(pix.scaled(self.video.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))

    def actualizar_progreso(self,titulo,fraccion,detalle):
        self.titulo.setText(titulo)
        self.barra.setValue(int(max(0,min(1,fraccion))*100))
        self.descripcion.setText(detalle)

    def al_evento(self,evento):
        self.hide()  # Val puede volver a mostrarla en la siguiente pantalla.
