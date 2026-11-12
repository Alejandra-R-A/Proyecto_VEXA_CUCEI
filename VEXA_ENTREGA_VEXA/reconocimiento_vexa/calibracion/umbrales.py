"""Calibración individual de los 11 umbrales faciales usados por Integrador.

Entrada: dict[condición] -> lista de repeticiones -> lista de métricas por fotograma.
Se conservan las diez repeticiones. Siete se usan para estimación y tres
para comprobación por repetición; la captura de calibración NO es entrenamiento
Machine Learning. Los gestos dobles reutilizan los umbrales de sus gestos base.
"""
from dataclasses import replace
import math
import numpy as np
from reconocimiento_vexa.parametros import ParametrosFaciales

CONDICIONES = [
    ('NEUTRAL_CERRADO', 'Expresión neutra con labios cerrados'),
    ('NEUTRAL_SEPARADO', 'Reposo natural con labios ligeramente separados'),
    ('G1', 'Media sonrisa derecha'),
    ('G2', 'Media sonrisa izquierda'),
    ('G3', 'Labios comprimidos'),
    ('G4', 'Sonrisa con dientes'),
    ('G5', 'Beso o protrusión labial'),
    ('GE1_D', 'Guiño del ojo derecho'),
    ('GE1_I', 'Guiño del ojo izquierdo'),
    ('GE2', 'Cierre de ambos ojos'),
    ('PARPADEO', 'Un parpadeo natural'),
]
ETIQUETAS = [x[0] for x in CONDICIONES]
BOCA = {'G1', 'G2', 'G3', 'G4', 'G5'}
OJOS = {'GE1_D', 'GE1_I', 'GE2'}


class CalibracionInvalida(ValueError):
    """La captura o los umbrales no cumplen las condiciones mínimas."""


def _medianas_repeticiones(capturas):
    resumen = {}
    for gesto in ETIQUETAS:
        reps = capturas.get(gesto, [])
        if len(reps) < 10:
            raise CalibracionInvalida(f'{gesto}: se requieren 10 repeticiones válidas; hay {len(reps)}.')
        resumen[gesto] = []
        for i, rep in enumerate(reps[:10], 1):
            if len(rep) < 10:
                raise CalibracionInvalida(f'{gesto}, repetición {i}: menos de 10 fotogramas.')
            nombres = ('WN','MAR','HN_ext','A_D_corr','eyeBlinkLeft','eyeBlinkRight')
            registro = {}
            for nombre in nombres:
                valores = [float(f[nombre]) for f in rep if nombre in f and f[nombre] is not None]
                if len(valores) < 10 or not all(math.isfinite(v) for v in valores):
                    raise CalibracionInvalida(f'{gesto}, repetición {i}: datos inválidos de {nombre}.')
                registro[nombre] = float(np.median(valores))
            bi, bd = registro['eyeBlinkLeft'], registro['eyeBlinkRight']
            registro.update({'min_blink': min(bi, bd), 'dif_blink': abs(bi-bd),
                             'dif_d': bd-bi,'dif_i': bi-bd})
            resumen[gesto].append(registro)
    return resumen


def _candidatos(datos, valor_defecto):
    valores = sorted(set(round(float(v), 7) for v in datos if math.isfinite(v)))
    if not valores:
        raise CalibracionInvalida('No hay valores para calcular umbrales.')
    candidatos = [(a+b)/2 for a,b in zip(valores, valores[1:])]
    margen = max((valores[-1]-valores[0])*0.1, 0.001)
    candidatos += [valores[0]-margen, valores[-1]+margen, valor_defecto]
    return sorted(set(round(float(v), 7) for v in candidatos))


def _scalar(resumen, objetivo, nombre, menor, base, negativos=None):
    """Busca un umbral por repetición y privilegia rechazo de otras clases."""
    positivos = [r[nombre] for r in resumen[objetivo][:7]]
    negativos = negativos or [k for k in ETIQUETAS if k != objetivo and k != 'PARPADEO']
    # En el protocolo, parpadeo es control de ojos y no se espera que la boca
    # permanezca absolutamente inmóvil en todos sus fotogramas.
    otros = [r[nombre] for k in negativos if k != objetivo for r in resumen[k][:7]]
    valores = positivos + otros
    if not otros: raise CalibracionInvalida(f'{objetivo}: faltan condiciones de comparación.')
    if menor and max(positivos) < min(otros):
        return (max(positivos)+min(otros))/2
    if not menor and min(positivos) > max(otros):
        return (min(positivos)+max(otros))/2
    # Clases solapadas: buscamos un compromiso, sin inventar separación.
    mejor = None
    for t in _candidatos(valores, base):
        if not math.isfinite(t): continue
        tp = sum((x < t) if menor else (x > t) for x in positivos)
        fp = sum((x < t) if menor else (x > t) for x in otros)
        # Sensibilidad y especificidad normalizadas, mayor castigo al FP.
        score = tp/len(positivos) - 2*fp/len(otros)
        orden = (round(score, 8), -abs(t-base))
        if mejor is None or orden > mejor[0]: mejor=(orden,t)
    if mejor is None: raise CalibracionInvalida(f'{objetivo}: no se pudo estimar umbral.')
    return float(mejor[1])


def _ocular_eval(r, p):
    bi, bd = r['eyeBlinkLeft'], r['eyeBlinkRight']
    if min(bi,bd) >= p.umbral_ge2 and abs(bi-bd) < p.diferencia_ge2:
        return 'GE2'
    if bd >= p.umbral_ge1_d and bd-bi >= p.diferencia_ge1_d:
        return 'GE1_D'
    if bi >= p.umbral_ge1_i and bi-bd >= p.diferencia_ge1_i:
        return 'GE1_I'
    return 'NEUTRO'


def _opt_ojos(resumen, p):
    """Optimiza pares umbral/diferencia manteniendo prioridad ocular GE2.

    Se usan medianas de las 7 repeticiones de ajuste y restricciones conservadoras:
    penalización alta a guiños y parpadeos incorrectamente atribuidos a GE2.
    """
    ejemplos=[(k,r) for k in ETIQUETAS for r in resumen[k][:7]]
    # Optimización coordenada de tres parejas; costo pequeño con 11 condiciones.
    parejas=[('umbral_ge2','diferencia_ge2','min_blink','dif_blink'),
             ('umbral_ge1_d','diferencia_ge1_d','eyeBlinkRight','dif_d'),
             ('umbral_ge1_i','diferencia_ge1_i','eyeBlinkLeft','dif_i')]
    for _ in range(2):
        for umbral,diferencia,metrica_umbral,metrica_dif in parejas:
            base_t,base_d=getattr(p,umbral),getattr(p,diferencia)
            cand_t=[v for v in _candidatos([r[metrica_umbral] for _,r in ejemplos],base_t) if 0.001<v<0.999]
            cand_d=[v for v in _candidatos([r[metrica_dif] for _,r in ejemplos],base_d) if 0.001<v<0.999]
            ganador=None
            for t in cand_t:
                for d in cand_d:
                    q=replace(p,**{umbral:t,diferencia:d})
                    penal=0
                    aciertos=0
                    for etiqueta,r in ejemplos:
                        detectado=_ocular_eval(r,q)
                        esperado=etiqueta if etiqueta in OJOS else 'NEUTRO'
                        aciertos+=int(detectado==esperado)
                        if detectado=='GE2' and esperado!='GE2': penal+=5
                        elif detectado!='NEUTRO' and detectado!=esperado: penal+=3
                        elif esperado in OJOS and detectado=='NEUTRO': penal+=2
                    # evitar extremos arbitrarios cuando dos candidatos empatan
                    puntuacion=(-penal,aciertos,-round(abs(t-base_t)+abs(d-base_d),7))
                    if ganador is None or puntuacion>ganador[0]: ganador=(puntuacion,t,d)
            if ganador is None: raise CalibracionInvalida('Sin candidatos oculares viables.')
            p=replace(p,**{umbral:ganador[1], diferencia:ganador[2]})
    return p


def _boca_eval(r,p):
    if r['WN'] < p.umbral_g5_wn: return 'G5'
    if r['MAR'] > p.umbral_g4_mar: return 'G4'
    if r['HN_ext'] < p.umbral_g3_hn_ext: return 'G3'
    if r['A_D_corr'] > p.umbral_g1_asimetria: return 'G1'
    if r['A_D_corr'] < p.umbral_g2_asimetria: return 'G2'
    return 'NEUTRO'


def calcular_calibracion(capturas):
    """Obtiene (parametros, informe) a partir de las 11 condiciones completas.

    La aprobación es una verificación básica para el prototipo, no una garantía
    de precisión clínica. La prueba del sistema real corresponde a Val y al equipo.
    """
    resumen=_medianas_repeticiones(capturas)
    p=ParametrosFaciales()
    p=replace(p,
      umbral_g5_wn=_scalar(resumen,'G5','WN',True,p.umbral_g5_wn),
      umbral_g4_mar=_scalar(resumen,'G4','MAR',False,p.umbral_g4_mar),
      umbral_g3_hn_ext=_scalar(resumen,'G3','HN_ext',True,p.umbral_g3_hn_ext),
      umbral_g1_asimetria=_scalar(resumen,'G1','A_D_corr',False,p.umbral_g1_asimetria),
      umbral_g2_asimetria=_scalar(resumen,'G2','A_D_corr',True,p.umbral_g2_asimetria))
    p=_opt_ojos(resumen,p)
    try: p.validar()
    except ValueError as e: raise CalibracionInvalida(str(e)) from e
    resultados={}
    for gesto in ETIQUETAS:
        errores=[]
        for i,r in enumerate(resumen[gesto][7:10],8):
            esperado=gesto if gesto in BOCA|OJOS else 'NEUTRO'
            pred_o=_ocular_eval(r,p)
            pred_b=_boca_eval(r,p)
            pred=pred_o if pred_o!='NEUTRO' else pred_b
            if pred != esperado:
                errores.append({'repeticion':i,'esperado':esperado,'detectado':pred})
        resultados[gesto]={'aciertos':3-len(errores),'total':3,'errores':errores}
    # Regla de prototipo: por lo menos 2 de 3 repeticiones independientes
    # para cada gesto; 3 de 3 para neutros y parpadeo. Es una comprobación
    # básica, no una validación en múltiples usuarios.
    valida=all(v['aciertos']>=(2 if k in BOCA|OJOS else 3) for k,v in resultados.items())
    informe={'valida':bool(valida),'evaluacion_por_condicion':resultados,
             'metodo':'medianas de 7 repeticiones + evaluación reservada de 3',
             'advertencia':'Evaluación de clasificación de medianas; no sustituye comprobación temporal en VEXA.'}
    return p,informe
