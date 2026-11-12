"""Ejecutar desde la raíz del paquete: python ejemplos/demo_calibracion.py"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from reconocimiento_vexa.calibracion.ventana import VentanaCalibracion


def main():
    app=QApplication(sys.argv)
    widget=VentanaCalibracion(id_perfil='PERFIL_EXPERIMENTAL')
    widget.calibracion_finalizada.connect(lambda perfil,ruta: print('CALIBRACIÓN GUARDADA',perfil,ruta))
    widget.calibracion_no_valida.connect(lambda razon: print('REPETIR:',razon))
    widget.error.connect(lambda mensaje: print('ERROR:',mensaje))
    widget.resize(1000,600)
    widget.show()
    sys.exit(app.exec())

if __name__=='__main__':main()
