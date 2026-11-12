"""Ejecutar: python ejemplos/demo_reconocimiento.py --experimental

Por defecto se requiere calibración de PERFIL_EXPERIMENTAL. La opción
--experimental activa explícitamente los umbrales fijos de referencia.
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QPushButton,QLabel
from reconocimiento_vexa.servicios.reconocimiento import ServicioReconocimiento
from reconocimiento_vexa.widgets.vista_previa import VistaPreviaReconocimiento


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--experimental',action='store_true',help='Usar umbrales originales sin calibración')
    args=parser.parse_args()
    app=QApplication(sys.argv)
    ventana=QWidget()
    ventana.setWindowTitle('VEXA — Demostración de los 3 modos')
    dis=QVBoxLayout(ventana)
    salida=QLabel('Selecciona un modo; se emitirá un solo gesto y se cerrará la cámara.')
    dis.addWidget(salida)
    servicio=ServicioReconocimiento(id_perfil='PERFIL_EXPERIMENTAL',modo_experimental=args.experimental)
    vista=VistaPreviaReconocimiento()
    vista.setMaximumWidth(380)
    vista.vincular(servicio)
    dis.addWidget(vista)
    for modo in ('CATEGORIAS','FRASES','CONFIRMAR_APAGADO'):
        btn=QPushButton('Iniciar modo '+modo)
        btn.clicked.connect(lambda checked=False,m=modo: (vista.show(),servicio.iniciar(m)))
        dis.addWidget(btn)
    servicio.evento_final.connect(lambda evento: salida.setText('EVENTO FINAL: '+evento))
    servicio.error.connect(lambda msg: salida.setText('ERROR: '+msg))
    ventana.resize(430,470)
    app.aboutToQuit.connect(servicio.cerrar)
    ventana.show()
    sys.exit(app.exec())

if __name__=='__main__':main()
