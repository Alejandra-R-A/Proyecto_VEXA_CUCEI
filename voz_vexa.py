import asyncio



VOCES_VEXA = {
    "Femenina": "Sabina",
    "Masculina": "Raul",
}


async def generar_audio_vexa(texto, tipo_voz="Femenina"):
    """
    Genera audio en memoria con una voz de español de México.

    Devuelve los bytes del audio para que PySide6
    pueda reproducirlos.
    """
    from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    from winrt.windows.storage.streams import DataReader

    nombre_voz = VOCES_VEXA.get(tipo_voz)

    if nombre_voz is None:
        raise ValueError(f"Tipo de voz no válido: {tipo_voz}")

    sintetizador = SpeechSynthesizer()

    for voz in SpeechSynthesizer.all_voices:
        if voz.language == "es-MX" and nombre_voz in voz.display_name:
            sintetizador.voice = voz
            break
    else:
        raise RuntimeError(f"No se encontró la voz {nombre_voz}.")

    audio = await sintetizador.synthesize_text_to_stream_async(texto)

    lector = DataReader(audio)
    await lector.load_async(audio.size)

    datos = bytearray(lector.read_buffer(audio.size))

    return bytes(datos)


def sintetizar_frase(texto, tipo_voz="Femenina"):
    """
    Función sencilla para las pruebas independientes.

    Importante: es bloqueante. No llamarla directamente
    desde el hilo principal de la interfaz de VEXA.
    """
    return asyncio.run(generar_audio_vexa(texto, tipo_voz))