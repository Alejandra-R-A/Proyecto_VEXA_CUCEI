"""Parámetros faciales de VEXA y sus valores experimentales de referencia.

Los once valores son los utilizados por el detector integrado validado. Una
calibración individual genera otra instancia; no altera estas constantes.
"""
from dataclasses import dataclass, asdict, fields
import math


@dataclass(frozen=True)
class ParametrosFaciales:
    # Boca, orden exacto de las reglas del detector experimental.
    umbral_g5_wn: float = 0.52
    umbral_g4_mar: float = 0.16
    umbral_g3_hn_ext: float = 0.20
    umbral_g1_asimetria: float = 0.030
    umbral_g2_asimetria: float = -0.030

    # Ojos; antes, la diferencia del guiño izquierdo y la de GE2
    # compartían el mismo valor (0.22). Son parámetros independientes.
    umbral_ge1_d: float = 0.44
    diferencia_ge1_d: float = 0.10
    umbral_ge1_i: float = 0.48
    diferencia_ge1_i: float = 0.22
    umbral_ge2: float = 0.54
    diferencia_ge2: float = 0.22

    # Umbral de neutralidad ocular: se conserva como valor experimental.
    blink_neutral_max: float = 0.40

    def validar(self):
        datos = asdict(self)
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in datos.values()):
            raise ValueError('Los umbrales deben ser números finitos.')
        if not 0 < self.umbral_g5_wn < 2: raise ValueError('WN fuera de rango.')
        if not 0 < self.umbral_g4_mar < 1.5: raise ValueError('MAR fuera de rango.')
        if not 0 < self.umbral_g3_hn_ext < 1.5: raise ValueError('HN_ext fuera de rango.')
        if not 0 < self.umbral_g1_asimetria < 0.5: raise ValueError('G1 debe tener asimetría positiva.')
        if not -0.5 < self.umbral_g2_asimetria < 0: raise ValueError('G2 debe tener asimetría negativa.')
        for clave in ('umbral_ge1_d','diferencia_ge1_d','umbral_ge1_i',
                      'diferencia_ge1_i','umbral_ge2','diferencia_ge2','blink_neutral_max'):
            if not 0 < datos[clave] < 1:
                raise ValueError(f'Parámetro ocular fuera de rango: {clave}')
        return self

    def a_dict(self):
        return asdict(self)

    @classmethod
    def desde_dict(cls, datos):
        campos = {f.name for f in fields(cls)}
        faltantes = campos - set(datos)
        if faltantes:
            raise ValueError(f'Faltan parámetros de calibración: {sorted(faltantes)}')
        return cls(**{k: datos[k] for k in campos}).validar()


EVENTOS_PUBLICOS = {
    **{f'G{i}': f'G{i}F' for i in range(1, 11)},
    'GE1_D': 'GE1_DF', 'GE1_I': 'GE1_IF', 'GE2': 'GE2F',
}

MODOS = {
    'CATEGORIAS': {'G1','G2','G3','G4','G6','G7','G8','G9','GE2'},
    'FRASES': {'G1','G2','G3','G4','G5','GE1_D','GE1_I','GE2'},
    'CONFIRMAR_APAGADO': {'GE2'},
}
