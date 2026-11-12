import sqlite3
from pathlib import Path
from contextlib import closing

DB_PATH = Path(__file__).resolve().parent / "vexa_pruebas.db"


def inicializar_base_datos():
    with closing(sqlite3.connect(DB_PATH)) as conexion:
        with conexion:

            conexion.execute("""
                CREATE TABLE IF NOT EXISTS participantes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT NOT NULL UNIQUE,
                    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            columnas_participantes = [
                fila[1]
                for fila in conexion.execute(
                    "PRAGMA table_info(participantes)"
                )
            ]

            if "puntuacion_sus" not in columnas_participantes:
                conexion.execute(
                    "ALTER TABLE participantes "
                    "ADD COLUMN puntuacion_sus REAL"
                )
            columnas_participantes = [
                fila[1]
                for fila in conexion.execute(
                    "PRAGMA table_info(participantes)"
                ).fetchall()
            ]

            if "consentimiento_verificado" not in columnas_participantes:
                conexion.execute("""
                    ALTER TABLE participantes
                    ADD COLUMN consentimiento_verificado INTEGER
                    NOT NULL DEFAULT 0
                """)

            if "fecha_verificacion_consentimiento" not in columnas_participantes:
                conexion.execute("""
                    ALTER TABLE participantes
                    ADD COLUMN fecha_verificacion_consentimiento TEXT
                """)

            # Guardar la voz pref de cada participante
            if "voz_seleccionada" not in columnas_participantes:
                conexion.execute("""
                    ALTER TABLE participantes
                    ADD COLUMN voz_seleccionada TEXT
                """)

            conexion.execute("""
                CREATE TABLE IF NOT EXISTS sesiones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participante_id INTEGER NOT NULL,
                    numero_sesion INTEGER NOT NULL,
                    fecha_inicio TEXT DEFAULT CURRENT_TIMESTAMP,
                    estado TEXT NOT NULL DEFAULT 'pendiente',
                    motivo_repeticion TEXT,
                    FOREIGN KEY (participante_id)
                        REFERENCES participantes(id),
                    UNIQUE (participante_id, numero_sesion)
                )
            """)
            columnas = [
                fila[1]
                for fila in conexion.execute("PRAGMA table_info(sesiones)")
            ]

            if "puntuacion_sus" not in columnas:
                conexion.execute(
                    "ALTER TABLE sesiones "
                    "ADD COLUMN puntuacion_sus REAL"
                )
            columnas_sesiones = [
                fila[1]
                for fila in conexion.execute(
                    "PRAGMA table_info(sesiones)"
                ).fetchall()
            ]

            if "es_depuracion" not in columnas_sesiones:
                conexion.execute("""
                    ALTER TABLE sesiones
                    ADD COLUMN es_depuracion INTEGER
                    NOT NULL DEFAULT 0
                """)
            conexion.execute("""
                CREATE TABLE IF NOT EXISTS iteraciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id INTEGER NOT NULL,
                    numero_iteracion INTEGER NOT NULL,
                    gesto_solicitado TEXT NOT NULL,
                    gesto_detectado TEXT,
                    gesto_real TEXT,
                    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                    estado_revision TEXT NOT NULL DEFAULT 'pendiente',
                    FOREIGN KEY (sesion_id)
                        REFERENCES sesiones(id),
                    UNIQUE (sesion_id, numero_iteracion)
                )
            """)
            columnas = [
                fila[1]
                for fila in conexion.execute(
                    "PRAGMA table_info(iteraciones)"
                ).fetchall()
            ]

            if "tiempo_deteccion" not in columnas:
                conexion.execute("""
                    ALTER TABLE iteraciones
                    ADD COLUMN tiempo_deteccion REAL
                """)

            if "tiempo_inicio_audio" not in columnas:
                conexion.execute("""
                    ALTER TABLE iteraciones
                    ADD COLUMN tiempo_inicio_audio REAL
                """)
            if "tipo_prueba" not in columnas:
                conexion.execute("""
                    ALTER TABLE iteraciones
                    ADD COLUMN tipo_prueba TEXT
                    DEFAULT 'reconocimiento'
                """)
            if "tiempo_inicio_seleccion" not in columnas:
                conexion.execute("""
                    ALTER TABLE iteraciones
                    ADD COLUMN tiempo_inicio_seleccion REAL
                """)

            if "tiempo_fin_seleccion" not in columnas:
                conexion.execute("""
                    ALTER TABLE iteraciones
                    ADD COLUMN tiempo_fin_seleccion REAL
                """)
            conexion.execute("""
                CREATE TABLE IF NOT EXISTS interacciones_completas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id INTEGER NOT NULL,
                    numero_interaccion INTEGER NOT NULL,
                    categoria_objetivo TEXT,
                    frase_objetivo TEXT,
                    tiempo_inicio REAL,
                    tiempo_fin REAL,
                    estado TEXT NOT NULL DEFAULT 'pendiente',
                    FOREIGN KEY (sesion_id)
                        REFERENCES sesiones(id),
                    UNIQUE (sesion_id, numero_interaccion)
                )
            """)

def guardar_verificacion_consentimiento(participante_id):
    with closing(sqlite3.connect(DB_PATH)) as conexion:
        with conexion:
            cursor = conexion.execute(
                """
                UPDATE participantes
                SET consentimiento_verificado = 1,
                    fecha_verificacion_consentimiento = CURRENT_TIMESTAMP
                WHERE id = ?
                AND consentimiento_verificado = 0
                """,
                (participante_id,)
            )

            if cursor.rowcount == 0:
                participante = conexion.execute(
                    """
                    SELECT id
                    FROM participantes
                    WHERE id = ?
                    """,
                    (participante_id,)
                ).fetchone()

                if participante is None:
                    raise ValueError(
                        "El participante no existe."
                    )

def consentimiento_esta_verificado(participante_id):
    with closing(sqlite3.connect(DB_PATH)) as conexion:
        resultado = conexion.execute(
            """
            SELECT consentimiento_verificado
            FROM participantes
            WHERE id = ?
            """,
            (participante_id,)
        ).fetchone()

        return resultado is not None and resultado[0] == 1

def registrar_participante(codigo):
    codigo = codigo.strip().upper()

    if not codigo:
        raise ValueError("El código del participante no puede estar vacío.")

    with sqlite3.connect(DB_PATH) as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO participantes (codigo)
            VALUES (?)
            """,
            (codigo,)
        )

        return cursor.lastrowid
    
def obtener_participantes():
    with closing(sqlite3.connect(DB_PATH)) as conexion:
        conexion.row_factory = sqlite3.Row

        resultados = conexion.execute(
            """
            SELECT
                id,
                codigo,
                fecha_registro
            FROM participantes
            ORDER BY id
            """
        ).fetchall()

        return [dict(fila) for fila in resultados]

def crear_sesion(participante_id, motivo_repeticion=None):
    if not consentimiento_esta_verificado(participante_id):
        raise ValueError(
            "No se puede crear una sesión experimental "
            "sin la verificación del consentimiento informado."
        )
    with sqlite3.connect(DB_PATH) as conexion:

        cursor = conexion.execute(
            """
            SELECT COALESCE(MAX(numero_sesion), 0)
            FROM sesiones
            WHERE participante_id = ?
            """,
            (participante_id,)
        )

        ultimo_numero = cursor.fetchone()[0]
        nuevo_numero = ultimo_numero + 1

        cursor = conexion.execute(
            """
            INSERT INTO sesiones (
                participante_id,
                numero_sesion,
                motivo_repeticion
            )
            VALUES (?, ?, ?)
            """,
            (
                participante_id,
                nuevo_numero,
                motivo_repeticion
            )
        )

        return cursor.lastrowid

def registrar_iteracion(sesion_id, numero_iteracion, gesto_solicitado):
    with sqlite3.connect(DB_PATH) as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO iteraciones (
                sesion_id,
                numero_iteracion,
                gesto_solicitado
            )
            VALUES (?, ?, ?)
            """,
            (
                sesion_id,
                numero_iteracion,
                gesto_solicitado
            )
        )

        return cursor.lastrowid
    
def guardar_gesto_detectado(iteracion_id, gesto_detectado):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            UPDATE iteraciones
            SET gesto_detectado = ?
            WHERE id = ?
            """,
            (
                gesto_detectado,
                iteracion_id
            )
        )

def guardar_gesto_real(iteracion_id, gesto_real):
    gestos_validos = {
        "G1", "G2", "G3", "G4",
        "G5", "G6", "G7", "Ninguno"
    }

    if gesto_real not in gestos_validos:
        raise ValueError(
            f"Gesto real no válido: {gesto_real}"
        )

    with sqlite3.connect(DB_PATH) as conexion:
        cursor = conexion.execute(
            """
            UPDATE iteraciones
            SET gesto_real = ?,
                estado_revision = 'revisado'
            WHERE id = ?
            """,
            (gesto_real, iteracion_id)
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe el ensayo con ID {iteracion_id}"
            )
        
def guardar_tiempos_respuesta(iteracion_id, tiempo_deteccion, tiempo_inicio_audio):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            UPDATE iteraciones
            SET tiempo_deteccion = ?,
                tiempo_inicio_audio = ?
            WHERE id = ?
            """,
            (
                tiempo_deteccion,
                tiempo_inicio_audio,
                iteracion_id
            )
        )

def guardar_tiempo_deteccion_experimental(iteracion_id, tiempo_segundos):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            UPDATE iteraciones
            SET tiempo_deteccion = ?
            WHERE id = ?
            """,
            (tiempo_segundos, iteracion_id)
        )

def calcular_tiempo_respuesta(iteracion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        resultado = conexion.execute(
            """
            SELECT tiempo_deteccion, tiempo_inicio_audio
            FROM iteraciones
            WHERE id = ?
            """,
            (iteracion_id,)
        ).fetchone()

    if resultado is None:
        return None

    tiempo_deteccion, tiempo_inicio_audio = resultado

    if tiempo_deteccion is None or tiempo_inicio_audio is None:
        return None

    if tiempo_inicio_audio < tiempo_deteccion:
        return None

    return (tiempo_inicio_audio - tiempo_deteccion) * 1000

def guardar_tiempos_seleccion(
    iteracion_id,
    tiempo_inicio_seleccion,
    tiempo_fin_seleccion
):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            UPDATE iteraciones
            SET tiempo_inicio_seleccion = ?,
                tiempo_fin_seleccion = ?
            WHERE id = ?
            """,
            (
                tiempo_inicio_seleccion,
                tiempo_fin_seleccion,
                iteracion_id
            )
        )
def calcular_tiempo_seleccion(iteracion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        resultado = conexion.execute(
            """
            SELECT
                tiempo_inicio_seleccion,
                tiempo_fin_seleccion
            FROM iteraciones
            WHERE id = ?
            """,
            (iteracion_id,)
        ).fetchone()

    if resultado is None:
        return None

    tiempo_inicio, tiempo_fin = resultado

    if tiempo_inicio is None or tiempo_fin is None:
        return None

    if tiempo_fin < tiempo_inicio:
        return None

    return tiempo_fin - tiempo_inicio

def registrar_interaccion_completa(
    sesion_id,
    numero_interaccion,
    categoria_objetivo,
    frase_objetivo
):
    with sqlite3.connect(DB_PATH) as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO interacciones_completas (
                sesion_id,
                numero_interaccion,
                categoria_objetivo,
                frase_objetivo
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                sesion_id,
                numero_interaccion,
                categoria_objetivo,
                frase_objetivo
            )
        )

        return cursor.lastrowid
    
def guardar_tiempos_interaccion(
    interaccion_id,
    tiempo_inicio,
    tiempo_fin
):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            UPDATE interacciones_completas
            SET tiempo_inicio = ?,
                tiempo_fin = ?
            WHERE id = ?
            """,
            (
                tiempo_inicio,
                tiempo_fin,
                interaccion_id
            )
        )

def calcular_tiempo_interaccion(interaccion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        resultado = conexion.execute(
            """
            SELECT tiempo_inicio, tiempo_fin
            FROM interacciones_completas
            WHERE id = ?
            """,
            (interaccion_id,)
        ).fetchone()

    if resultado is None:
        return None

    tiempo_inicio, tiempo_fin = resultado

    if tiempo_inicio is None or tiempo_fin is None:
        return None

    if tiempo_fin < tiempo_inicio:
        return None

    return tiempo_fin - tiempo_inicio

def actualizar_estado_interaccion(interaccion_id, estado):
    estados_validos = (
        "pendiente",
        "completada",
        "fallida",
        "cancelada"
    )

    if estado not in estados_validos:
        raise ValueError("Estado de interacción no válido.")

    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            UPDATE interacciones_completas
            SET estado = ?
            WHERE id = ?
            """,
            (estado, interaccion_id)
        )

def obtener_interacciones_sesion(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row

        resultados = conexion.execute(
            """
            SELECT
                id,
                numero_interaccion,
                categoria_objetivo,
                frase_objetivo,
                tiempo_inicio,
                tiempo_fin,
                estado
            FROM interacciones_completas
            WHERE sesion_id = ?
            ORDER BY numero_interaccion
            """,
            (sesion_id,)
        ).fetchall()

        return [dict(fila) for fila in resultados]

def obtener_iteraciones_pendientes(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row

        resultados = conexion.execute(
            """
            SELECT
                id,
                numero_iteracion,
                gesto_solicitado,
                gesto_detectado,
                gesto_real,
                estado_revision
            FROM iteraciones
            WHERE sesion_id = ?
              AND estado_revision = 'pendiente'
            ORDER BY numero_iteracion
            """,
            (sesion_id,)
        ).fetchall()

        return [dict(fila) for fila in resultados]

def calcular_conteos_gesto(sesion_id, gesto):
    conteos = {
        "VP": 0,
        "VN": 0,
        "FP": 0,
        "FN": 0
    }

    with sqlite3.connect(DB_PATH) as conexion:
        registros = conexion.execute(
            """
            SELECT gesto_real, gesto_detectado
            FROM iteraciones
            WHERE sesion_id = ?
            AND estado_revision = 'revisado'
            AND gesto_real IS NOT NULL
            AND gesto_detectado IS NOT NULL
            """,
            (sesion_id,)
        ).fetchall()

    for gesto_real, gesto_detectado in registros:
        if gesto_real == gesto and gesto_detectado == gesto:
            conteos["VP"] += 1

        elif gesto_real != gesto and gesto_detectado != gesto:
            conteos["VN"] += 1

        elif gesto_real != gesto and gesto_detectado == gesto:
            conteos["FP"] += 1

        elif gesto_real == gesto and gesto_detectado != gesto:
            conteos["FN"] += 1

    return conteos

def calcular_metricas_gesto(sesion_id, gesto):
    conteos = calcular_conteos_gesto(sesion_id, gesto)

    vp = conteos["VP"]
    vn = conteos["VN"]
    fp = conteos["FP"]
    fn = conteos["FN"]

    total = vp + vn + fp + fn

    exactitud = (
        (vp + vn) / total
        if total > 0 else None
    )

    precision = (
        vp / (vp + fp)
        if (vp + fp) > 0 else None
    )

    sensibilidad = (
        vp / (vp + fn)
        if (vp + fn) > 0 else None
    )

    return {
        "exactitud": exactitud,
        "precision": precision,
        "sensibilidad": sensibilidad
    }

def obtener_datos_matriz_confusion(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        resultados = conexion.execute(
            """
            SELECT gesto_real, gesto_detectado
            FROM iteraciones
            WHERE sesion_id = ?
              AND estado_revision = 'revisado'
              AND gesto_real IS NOT NULL
              AND gesto_detectado IS NOT NULL
            ORDER BY numero_iteracion
            """,
            (sesion_id,)
        ).fetchall()

    return resultados

def construir_matriz_confusion(sesion_id):
    gestos = [
        "G1", "G2", "G3", "G4",
        "G5", "G6", "G7", "ninguno"
    ]

    matriz = {
        real: {detectado: 0 for detectado in gestos}
        for real in gestos
    }

    datos = obtener_datos_matriz_confusion(sesion_id)

    for gesto_real, gesto_detectado in datos:
        if gesto_real in matriz and gesto_detectado in matriz[gesto_real]:
            matriz[gesto_real][gesto_detectado] += 1

    return matriz

def obtener_resumen_iteraciones(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        resultado = conexion.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN estado_revision = 'revisado'
                         AND gesto_real IS NOT NULL
                         AND gesto_detectado IS NOT NULL
                        THEN 1 ELSE 0
                    END
                ) AS validas
            FROM iteraciones
            WHERE sesion_id = ?
            """,
            (sesion_id,)
        ).fetchone()

    total, validas = resultado
    validas = validas or 0
    return {
        "total": total,
        "validas": validas,
        "excluidas": total - validas
    }

def obtener_sesiones_participante(participante_id):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row

        resultados = conexion.execute(
            """
            SELECT
                id,
                numero_sesion,
                fecha_inicio,
                estado,
                motivo_repeticion
            FROM sesiones
            WHERE participante_id = ?
            ORDER BY numero_sesion
            """,
            (participante_id,)
        ).fetchall()

        return [dict(fila) for fila in resultados]

def obtener_sesiones_completadas(participante_id):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row

        resultados = conexion.execute(
            """
            SELECT
                id,
                numero_sesion,
                fecha_inicio,
                estado,
                motivo_repeticion
            FROM sesiones
            WHERE participante_id = ?
              AND estado = 'completada'
            ORDER BY numero_sesion
            """,
            (participante_id,)
        ).fetchall()

        return [dict(fila) for fila in resultados]

def verificar_distribucion_experimental(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        resultados = conexion.execute(
            """
            SELECT gesto_solicitado, COUNT(*)
            FROM iteraciones
            WHERE sesion_id = ?
              AND tipo_prueba = 'reconocimiento'
            GROUP BY gesto_solicitado
            """,
            (sesion_id,)
        ).fetchall()

    conteos = dict(resultados)

    return all(
        conteos.get(gesto, 0) == REPETICIONES_POR_GESTO
        for gesto in GESTOS_EXPERIMENTALES
    ) and len(conteos) == len(GESTOS_EXPERIMENTALES)

def verificar_sesion_para_analisis(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        resultado = conexion.execute(
            """
            SELECT estado, es_depuracion, motivo_repeticion
            FROM sesiones
            WHERE id = ?
            """,
            (sesion_id,)
        ).fetchone()

    if resultado is None:
        return {
            "apta": False,
            "motivo": "La sesión no existe."
        }

    if resultado[0] != "completada":
        return {
            "apta": False,
            "motivo": "La sesión no está completada."
        }
    if resultado[1] == 1 or resultado[2] == "DEPURACION_F9":
        return {
            "apta": False,
            "motivo": "La sesión contiene pruebas de depuración F9."
        }

    resumen = obtener_resumen_iteraciones(sesion_id)

    if resumen["total"] == 0:
        return {
            "apta": False,
            "motivo": "La sesión no tiene iteraciones registradas."
        }
    
    if resumen["total"] != 24:
        return {
            "apta": False,
            "motivo": (
                "La sesión debe tener exactamente 24 ensayos. "
                f"Se encontraron {resumen['total']}."
            )
        }

    if not verificar_distribucion_experimental(sesion_id):
        return {
            "apta": False,
            "motivo": (
                "La sesión no tiene exactamente tres ensayos "
                "de cada condición experimental."
            )
        }

    if resumen["excluidas"] > 0:
        return {
            "apta": False,
            "motivo": "La sesión tiene iteraciones incompletas o sin revisar."
        }

    etiquetas = verificar_etiquetas_gestos(sesion_id)

    if not etiquetas["validas"]:
        return {
            "apta": False,
            "motivo": "La sesión contiene etiquetas de gestos incorrectas."
        }

    return {
        "apta": True,
        "motivo": "La sesión tiene sus iteraciones registradas, revisadas y con etiquetas válidas."
    }

def obtener_sesiones_aptas_para_analisis():
    with sqlite3.connect(DB_PATH) as conexion:
        sesiones = conexion.execute(
            """
            SELECT id
            FROM sesiones
            ORDER BY id
            """
        ).fetchall()

    sesiones_aptas = []

    for (sesion_id,) in sesiones:
        verificacion = verificar_sesion_para_analisis(
            sesion_id
        )

        if verificacion["apta"]:
            sesiones_aptas.append(sesion_id)

    return sesiones_aptas

def calcular_conteos_globales_gesto(gesto):
    conteos_globales = {
        "VP": 0,
        "VN": 0,
        "FP": 0,
        "FN": 0
    }

    sesiones_aptas = obtener_sesiones_aptas_globales()
    for sesion_id in sesiones_aptas:
        conteos_sesion = calcular_conteos_gesto(
            sesion_id, gesto
        )

        for categoria in conteos_globales:
            conteos_globales[categoria] += conteos_sesion[categoria]

    return conteos_globales

def calcular_metricas_globales_gesto(gesto):
    conteos = calcular_conteos_globales_gesto(gesto)

    vp = conteos["VP"]
    vn = conteos["VN"]
    fp = conteos["FP"]
    fn = conteos["FN"]

    total = vp + vn + fp + fn

    exactitud = (
        (vp + vn) / total
        if total > 0 else None
    )

    precision = (
        vp / (vp + fp)
        if (vp + fp) > 0 else None
    )

    sensibilidad = (
        vp / (vp + fn)
        if (vp + fn) > 0 else None
    )

    return {
        "exactitud": exactitud,
        "precision": precision,
        "sensibilidad": sensibilidad
    }

def calcular_metricas_globales_vexa():
    gestos = [
        "G1", "G2", "G3", "G4",
        "G5", "G6", "G7", "ninguno"
    ]

    resultados = {
        "exactitud": [],
        "precision": [],
        "sensibilidad": []
    }

    sesiones_aptas = obtener_sesiones_aptas_globales()
    if not sesiones_aptas:
        return {
            "exactitud": None,
            "precision": None,
            "sensibilidad": None
        }

    for gesto in gestos:
        metricas = calcular_metricas_globales_gesto(gesto)

        for nombre in resultados:
            valor = metricas[nombre]

            if valor is not None:
                resultados[nombre].append(valor)

    return {
        nombre: (
            sum(valores) / len(valores)
            if valores else None
        )
        for nombre, valores in resultados.items()
    }

def obtener_sesiones_aptas_para_analisis(participante_id):
    sesiones = obtener_sesiones_completadas(participante_id)

    sesiones_aptas = []

    for sesion in sesiones:
        verificacion = verificar_sesion_para_analisis(sesion["id"])

        if verificacion["apta"]:
            sesiones_aptas.append(sesion)

    return sesiones_aptas

def obtener_sesiones_aptas_globales():
    with sqlite3.connect(DB_PATH) as conexion:
        filas = conexion.execute(
            "SELECT id FROM sesiones ORDER BY id"
        ).fetchall()

    sesiones_aptas = []

    for (sesion_id,) in filas:
        verificacion = verificar_sesion_para_analisis(sesion_id)

        if verificacion["apta"]:
            sesiones_aptas.append(sesion_id)

    return sesiones_aptas

def verificar_etiquetas_gestos(sesion_id):
    gestos_validos = {
        "G1", "G2", "G3", "G4",
        "G5", "G6", "G7", "ninguno"
    }

    with sqlite3.connect(DB_PATH) as conexion:
        iteraciones = conexion.execute(
            """
            SELECT
                numero_iteracion,
                gesto_solicitado,
                gesto_detectado,
                gesto_real
            FROM iteraciones
            WHERE sesion_id = ?
            ORDER BY numero_iteracion
            """,
            (sesion_id,)
        ).fetchall()

    errores = []

    for numero, solicitado, detectado, real in iteraciones:
        for campo, valor in (
            ("gesto_solicitado", solicitado),
            ("gesto_detectado", detectado),
            ("gesto_real", real)
        ):
            if valor is not None and valor not in gestos_validos:
                errores.append(
                    f"Iteración {numero}: {campo} = {valor}"
                )

    return {
        "validas": len(errores) == 0,
        "errores": errores
    }

GESTOS_EXPERIMENTALES = (
    "G1",
    "G2",
    "G3",
    "G4",
    "G5",
    "G6",
    "G7",
    "ninguno"
)

REPETICIONES_POR_GESTO = 3

def generar_secuencia_experimental():
    secuencia = []

    for repeticion in range(REPETICIONES_POR_GESTO):
        for gesto in GESTOS_EXPERIMENTALES:
            secuencia.append({
                "numero_iteracion": len(secuencia) + 1,
                "gesto_solicitado": gesto
            })

    return secuencia

import random


def generar_secuencia_experimental_aleatoria():
    secuencia_original = generar_secuencia_experimental()

    gestos = [
        ensayo["gesto_solicitado"]
        for ensayo in secuencia_original
    ]

    random.shuffle(gestos)

    secuencia_aleatoria = []

    for numero, gesto in enumerate(gestos, start=1):
        secuencia_aleatoria.append({
            "numero_iteracion": numero,
            "gesto_solicitado": gesto
        })

    return secuencia_aleatoria

def preparar_iteraciones_experimentales(sesion_id):
    secuencia = generar_secuencia_experimental_aleatoria()

    with closing(sqlite3.connect(DB_PATH)) as conexion:
        with conexion:
            conexion.execute("BEGIN IMMEDIATE")

            sesion = conexion.execute(
                """
                SELECT estado
                FROM sesiones
                WHERE id = ?
                """,
                (sesion_id,)
            ).fetchone()

            if sesion is None:
                raise ValueError("La sesión no existe.")

            if sesion[0] != "pendiente":
                raise ValueError(
                    "Solo se pueden preparar sesiones pendientes."
                )

            cantidad = conexion.execute(
                """
                SELECT COUNT(*)
                FROM iteraciones
                WHERE sesion_id = ?
                """,
                (sesion_id,)
            ).fetchone()[0]

            if cantidad > 0:
                raise ValueError(
                    "Esta sesión ya tiene iteraciones registradas."
                )

            conexion.executemany(
                """
                INSERT INTO iteraciones (
                    sesion_id,
                    numero_iteracion,
                    gesto_solicitado,
                    tipo_prueba
                )
                VALUES (?, ?, ?, 'reconocimiento')
                """,
                [
                    (
                        sesion_id,
                        ensayo["numero_iteracion"],
                        ensayo["gesto_solicitado"]
                    )
                    for ensayo in secuencia
                ]
            )

    return secuencia

def obtener_secuencia_experimental(sesion_id):
    with closing(sqlite3.connect(DB_PATH)) as conexion:
        conexion.row_factory = sqlite3.Row

        registros = conexion.execute(
            """
            SELECT
                id,
                numero_iteracion,
                gesto_solicitado
            FROM iteraciones
            WHERE sesion_id = ?
              AND tipo_prueba = 'reconocimiento'
            ORDER BY numero_iteracion
            """,
            (sesion_id,)
        ).fetchall()
        total = conexion.execute(
            """
            SELECT COUNT(*)
            FROM iteraciones
            WHERE sesion_id = ?
            """,
            (sesion_id,)
        ).fetchone()[0]

        print(
            f"DIAGNÓSTICO VEXA | sesión={sesion_id} | "
            f"ensayos totales={total} | "
            f"ensayos de reconocimiento={len(registros)}",
            flush=True
        )
        return [dict(registro) for registro in registros]

def obtener_instruccion_experimental(gesto_solicitado):
    if gesto_solicitado == "ninguno":
        return (
            "Mantén el rostro en posición neutral. "
            "No realices ningún gesto."
        )

    if gesto_solicitado in GESTOS_EXPERIMENTALES:
        return f"Realiza el gesto {gesto_solicitado}."

    raise ValueError(
        f"Gesto experimental no válido: {gesto_solicitado}"
    )

def actualizar_estado_sesion(sesion_id, estado):
    estados_permitidos = {
        "pendiente",
        "en_curso",
        "completada",
        "interrumpida",
        "invalidada"
    }

    if estado not in estados_permitidos:
        raise ValueError(
            f"Estado de sesión no válido: {estado}"
        )

    with sqlite3.connect(DB_PATH) as conexion:
        cursor = conexion.execute(
            """
            UPDATE sesiones
            SET estado = ?
            WHERE id = ?
            """,
            (estado, sesion_id)
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe la sesión {sesion_id}"
            )

def marcar_sesion_depuracion(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.execute(
            """
            UPDATE sesiones
            SET es_depuracion = 1
            WHERE id = ?
            """,
            (sesion_id,)
        )

def calcular_tiempo_respuesta_promedio_global():
    sesiones_aptas = obtener_sesiones_aptas_globales()

    if not sesiones_aptas:
        return None

    tiempos_validos = []

    with sqlite3.connect(DB_PATH) as conexion:
        for sesion_id in sesiones_aptas:
            filas = conexion.execute(
                """
                SELECT tiempo_deteccion, tiempo_inicio_audio
                FROM iteraciones
                WHERE sesion_id = ?
                """,
                (sesion_id,)
            ).fetchall()

            for tiempo_deteccion, tiempo_inicio_audio in filas:
                if (
                    tiempo_deteccion is None
                    or tiempo_inicio_audio is None
                ):
                    continue

                diferencia = tiempo_inicio_audio - tiempo_deteccion

                if diferencia >= 0:
                    tiempos_validos.append(diferencia * 1000)

    if not tiempos_validos:
        return None

    return sum(tiempos_validos) / len(tiempos_validos)

def calcular_tiempo_seleccion_promedio_global():
    sesiones_aptas = obtener_sesiones_aptas_globales()

    if not sesiones_aptas:
        return None

    tiempos_validos = []

    with sqlite3.connect(DB_PATH) as conexion:
        for sesion_id in sesiones_aptas:
            filas = conexion.execute(
                """
                SELECT
                    tiempo_inicio_seleccion,
                    tiempo_fin_seleccion
                FROM iteraciones
                WHERE sesion_id = ?
                """,
                (sesion_id,)
            ).fetchall()

            for tiempo_inicio, tiempo_fin in filas:
                if tiempo_inicio is None or tiempo_fin is None:
                    continue

                diferencia = tiempo_fin - tiempo_inicio

                if diferencia >= 0:
                    tiempos_validos.append(diferencia)

    if not tiempos_validos:
        return None

    return sum(tiempos_validos) / len(tiempos_validos)

def calcular_tiempo_interaccion_promedio_global():
    sesiones_aptas = obtener_sesiones_aptas_globales()

    if not sesiones_aptas:
        return None

    tiempos_validos = []

    with sqlite3.connect(DB_PATH) as conexion:
        for sesion_id in sesiones_aptas:
            filas = conexion.execute(
                """
                SELECT tiempo_inicio, tiempo_fin
                FROM interacciones_completas
                WHERE sesion_id = ?
                """,
                (sesion_id,)
            ).fetchall()

            for tiempo_inicio, tiempo_fin in filas:
                if tiempo_inicio is None or tiempo_fin is None:
                    continue

                diferencia = tiempo_fin - tiempo_inicio

                if diferencia >= 0:
                    tiempos_validos.append(diferencia)

    if not tiempos_validos:
        return None

    return sum(tiempos_validos) / len(tiempos_validos)

def guardar_puntuacion_sus(participante_id, puntuacion):
    puntuacion = float(puntuacion)

    if not 0 <= puntuacion <= 100:
        raise ValueError(
            "La puntuación SUS debe estar entre 0 y 100."
        )

    with sqlite3.connect(DB_PATH) as conexion:
        cursor = conexion.execute(
            """
            UPDATE participantes
            SET puntuacion_sus = ?
            WHERE id = ?
            """,
            (puntuacion, participante_id)
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "No se encontró el participante."
            )

def calcular_sus_promedio_global():
    sesiones_aptas = obtener_sesiones_aptas_globales()

    if not sesiones_aptas:
        return None

    ids_sesiones = sesiones_aptas

    marcadores = ",".join("?" for _ in ids_sesiones)

    with sqlite3.connect(DB_PATH) as conexion:
        cursor = conexion.execute(
            f"""
            SELECT AVG(p.puntuacion_sus)
            FROM participantes p
            WHERE p.puntuacion_sus BETWEEN 0 AND 100
              AND EXISTS (
                  SELECT 1
                  FROM sesiones s
                  WHERE s.participante_id = p.id
                    AND s.id IN ({marcadores})
              )
            """,
            ids_sesiones
        )

        promedio = cursor.fetchone()[0]

    return promedio

def calcular_efectividad_global():
    sesiones_aptas = obtener_sesiones_aptas_globales()

    if not sesiones_aptas:
        return None

    total_intentos = 0
    intentos_exitosos = 0

    with sqlite3.connect(DB_PATH) as conexion:
        for sesion_id in sesiones_aptas:
            registros = conexion.execute(
                """
                SELECT gesto_solicitado, gesto_detectado
                FROM iteraciones
                WHERE sesion_id = ?
                  AND estado_revision = 'revisado'
                  AND gesto_real IS NOT NULL
                  AND gesto_detectado IS NOT NULL
                  AND tipo_prueba = 'reconocimiento'
                """,
                (sesion_id,)
            ).fetchall()

            for gesto_solicitado, gesto_detectado in registros:
                total_intentos += 1

                if gesto_solicitado == gesto_detectado:
                    intentos_exitosos += 1

    if total_intentos == 0:
        return None

    return (intentos_exitosos / total_intentos) * 100

def calcular_eficiencia_global():
    sesiones_aptas = obtener_sesiones_aptas_globales()

    if not sesiones_aptas:
        return None

    total_aciertos = 0
    tiempo_total = 0.0

    with sqlite3.connect(DB_PATH) as conexion:
        for sesion_id in sesiones_aptas:
            registros = conexion.execute(
                """
                SELECT
                    gesto_solicitado,
                    gesto_detectado,
                    tiempo_deteccion
                FROM iteraciones
                WHERE sesion_id = ?
                  AND tipo_prueba = 'reconocimiento'
                  AND estado_revision = 'revisado'
                  AND gesto_real IS NOT NULL
                  AND gesto_detectado IS NOT NULL
                """,
                (sesion_id,)
            ).fetchall()

            for solicitado, detectado, tiempo in registros:
                if tiempo is None or tiempo <= 0:
                    return None

                tiempo_total += tiempo

                if solicitado == detectado:
                    total_aciertos += 1

    if tiempo_total <= 0:
        return None

    return total_aciertos / tiempo_total

def obtener_ensayos_para_revision(sesion_id):
    with sqlite3.connect(DB_PATH) as conexion:
        conexion.row_factory = sqlite3.Row

        filas = conexion.execute(
            """
            SELECT
                id,
                numero_iteracion,
                gesto_solicitado,
                gesto_detectado,
                gesto_real,
                estado_revision
            FROM iteraciones
            WHERE sesion_id = ?
              AND tipo_prueba = 'reconocimiento'
            ORDER BY numero_iteracion
            """,
            (sesion_id,)
        ).fetchall()

    return [dict(fila) for fila in filas]

def guardar_revision_completa(sesion_id, gestos_reales):
    gestos_validos = {
        "G1", "G2", "G3", "G4",
        "G5", "G6", "G7", "Ninguno"
    }

    if len(gestos_reales) != 24:
        raise ValueError(
            "La revisión debe contener exactamente 24 ensayos."
        )

    if any(
        gesto not in gestos_validos
        for gesto in gestos_reales.values()
    ):
        raise ValueError("Hay gestos reales no válidos.")

    with sqlite3.connect(DB_PATH) as conexion:
        filas = conexion.execute(
            """
            SELECT id
            FROM iteraciones
            WHERE sesion_id = ?
              AND tipo_prueba = 'reconocimiento'
            """,
            (sesion_id,)
        ).fetchall()

        ids_sesion = {fila[0] for fila in filas}

        if len(ids_sesion) != 24:
            raise ValueError(
                "La sesión no contiene exactamente 24 ensayos."
            )

        if set(gestos_reales.keys()) != ids_sesion:
            raise ValueError(
                "Los ensayos seleccionados no corresponden "
                "a la sesión completa."
            )

        for ensayo_id, gesto_real in gestos_reales.items():
            conexion.execute(
                """
                UPDATE iteraciones
                SET gesto_real = ?,
                    estado_revision = 'revisado'
                WHERE id = ?
                  AND sesion_id = ?
                """,
                (gesto_real, ensayo_id, sesion_id)
            )