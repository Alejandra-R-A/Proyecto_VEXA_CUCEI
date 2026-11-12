# Verificaciones realizadas antes de empaquetar

1. **Compilación sintáctica:** ejecutada con `python -m compileall` sobre todos los módulos y ejemplos. Resultado: correcta.
2. **Paridad de comportamiento con scripts de referencia:** se reprodujeron las secuencias de registros `vexa_integracion_20261024_161001.csv` (7,531 filas) y `vexa_dobles_rearme_20261024_200929.csv` (691 filas), inyectando las métricas ya registradas a ambos `Integrador` y a ambos `InterpretadorTemporal`. Se compararon evento base, candidatura, estado, bloqueo y eventos finales por fila. **Coincidencia exacta con los parámetros experimentales.**
3. **Cálculo individual:** se ejecutó `calcular_calibracion()` con una colección sintética de 10 repeticiones por cada una de las 11 condiciones. Generó y comprobó un perfil coherente. **Esta prueba es únicamente de consistencia lógica; las muestras sintéticas NO validan precisión sobre otros rostros.**
4. **No probado físicamente:** adquisición desde webcam, MediaPipe y visualización PySide6, porque esas dos dependencias no estaban instaladas en el entorno de empaquetado y no estaba disponible la cámara real. Tampoco se verificó el funcionamiento conectado al proyecto real de Val. Se necesita **una prueba integral**, no pruebas exhaustivas por módulo.

**Importante:** la prueba de paridad utiliza métricas numéricas almacenadas en CSV; no reconstruye la extracción original desde video ni constituye prueba de nuevas calibraciones individuales. Los umbrales calculados automáticamente todavía no han sido validados con sujetos adicionales.
