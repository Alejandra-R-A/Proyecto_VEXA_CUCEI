"""Almacenamiento atómico de calibraciones por ID de perfil de Val."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from reconocimiento_vexa.parametros import ParametrosFaciales

VERSION_FORMATO = 1
VERSION_DETECTOR = 'vexa-facial-retencion030-dobles-rearme-1'
RUTA_PREDETERMINADA = Path.home() / '.vexa' / 'calibraciones_faciales'


def _archivo(id_perfil, carpeta=None):
    if not isinstance(id_perfil, str) or not id_perfil.strip():
        raise ValueError('El ID de perfil proporcionado por Val debe ser un texto no vacío.')
    carpeta = Path(carpeta) if carpeta is not None else RUTA_PREDETERMINADA
    nombre = hashlib.sha256(id_perfil.encode('utf-8')).hexdigest()[:24]
    return carpeta / f'{nombre}.json'


def guardar_calibracion(id_perfil, parametros, informe, carpeta=None):
    """Solo guarda calibraciones aprobadas; nunca sobrescribe con una fallida."""
    if not informe.get('valida', False):
        raise ValueError('Se intentó guardar una calibración no válida.')
    parametros.validar()
    destino = _archivo(id_perfil, carpeta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        'formato': VERSION_FORMATO,
        'version_detector': VERSION_DETECTOR,
        'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'id_perfil': id_perfil,
        'parametros': parametros.a_dict(),
        'informe': informe,
    }
    temporal = destino.with_suffix('.tmp')
    try:
        temporal.write_text(json.dumps(documento, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)
    return destino


def cargar_calibracion(id_perfil, carpeta=None):
    archivo = _archivo(id_perfil, carpeta)
    if not archivo.is_file():
        raise FileNotFoundError('Este perfil no tiene una calibración facial guardada.')
    data = json.loads(archivo.read_text(encoding='utf-8'))
    if data.get('id_perfil') != id_perfil or data.get('formato') != VERSION_FORMATO:
        raise ValueError('El archivo no corresponde al perfil o formato solicitado.')
    if data.get('version_detector') != VERSION_DETECTOR:
        raise ValueError('Calibración incompatible con esta versión del detector.')
    if not data.get('informe', {}).get('valida', False):
        raise ValueError('La calibración guardada no tiene validación aprobada.')
    return ParametrosFaciales.desde_dict(data['parametros'])
