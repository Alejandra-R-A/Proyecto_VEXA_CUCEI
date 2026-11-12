"""Validaci?n EMG para gestos faciales de VEXA.

M?dulo independiente: no abre puertos ni modifica la interfaz.
Las muestras tienen formato (tiempo_monotonic, rms1, rms2, ok1, ok2).
"""

GESTOS_BUCALES = {
    "G1F", "G2F", "G3F", "G4F", "G5F",
    "G6F", "G7F", "G8F", "G9F", "G10F",
}

DURACION_MINIMA = 0.12


def validar_gesto_emg(
    gesto,
    muestras,
    umbrales,
    inicio,
    fin,
):
    """Devuelve (autorizado, motivo).

    Los gestos oculares se autorizan sin EMG.
    Para los bucales basta un episodio v?lido en cualquiera
    de los dos canales, dentro de la ventana indicada.
    """
    if not isinstance(gesto, str):
        return False, "Gesto desconocido"

    gesto = gesto.upper()

    if gesto.startswith("GE"):
        return True, "OCULAR_SIN_EMG"

    if gesto not in GESTOS_BUCALES:
        return False, "GESTO_DESCONOCIDO"

    if len(umbrales) != 2 or any(
        not isinstance(u, (int, float)) or u <= 0
        for u in umbrales
    ):
        return False, "UMBRALES_INVALIDOS"

    if fin <= inicio:
        return False, "VENTANA_INVALIDA"

    seleccion = sorted(
        (m for m in muestras if inicio <= m[0] <= fin),
        key=lambda m: m[0],
    )

    if not seleccion:
        return False, "SIN_DATOS_EMG"

    for canal in (0, 1):
        comienzo = None
        anterior = None

        for t, rms1, rms2, ok1, ok2 in seleccion:
            rms = (rms1, rms2)[canal]
            valido = (ok1, ok2)[canal]

            if (
                not valido
                or rms is None
                or rms < umbrales[canal]
                or (
                    anterior is not None
                    and t - anterior > 0.05
                )
            ):
                comienzo = None
                anterior = None
                continue

            if comienzo is None:
                comienzo = t

            anterior = t

            if t - comienzo >= DURACION_MINIMA:
                return True, f"EMG_VALIDADO_CANAL_{canal + 1}"

    return False, "EMG_NO_VALIDADO"
