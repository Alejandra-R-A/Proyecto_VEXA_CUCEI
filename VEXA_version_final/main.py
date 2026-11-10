import sys
import time
import sqlite3
from collections import Counter

from database import (
    registrar_participante,
    obtener_participantes,
    obtener_sesiones_participante,
    guardar_verificacion_consentimiento,
    consentimiento_esta_verificado,
    crear_sesion,
    obtener_secuencia_experimental,
    obtener_instruccion_experimental,
    guardar_gesto_detectado,
    guardar_tiempo_deteccion_experimental,
    actualizar_estado_sesion,
    marcar_sesion_depuracion,
    verificar_sesion_para_analisis,
    calcular_conteos_gesto,
    calcular_metricas_gesto,
    calcular_metricas_globales_vexa,
    calcular_metricas_globales_gesto,
    obtener_sesiones_aptas_globales,
    calcular_tiempo_respuesta_promedio_global,
    calcular_tiempo_seleccion_promedio_global,
    calcular_tiempo_interaccion_promedio_global,
    guardar_puntuacion_sus,
    calcular_sus_promedio_global,
    calcular_efectividad_global,
    calcular_eficiencia_global,
    obtener_ensayos_para_revision,
    guardar_revision_completa,
    guardar_gesto_real,
    preparar_iteraciones_experimentales,
    DB_PATH,
)
from database import inicializar_base_datos
from trabajador_voz import TrabajadorVoz
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
    QGridLayout,
    QComboBox,
    QInputDialog,
    QMessageBox,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QFrame,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QDialog,
    QProgressBar,
    QLayout,
)
from PySide6.QtCore import Qt, QSettings, QSize, QTimer, QThread, QBuffer, QByteArray, QIODevice, QRectF
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QIcon, QPixmap, QShortcut, QKeySequence, QPainter, QPen, QColor
from pathlib import Path

CARPETA_MEDIAPIPE = Path(__file__).resolve().parent / "VEXA_ENTREGA_VEXA"

if str(CARPETA_MEDIAPIPE) not in sys.path:
    sys.path.insert(0, str(CARPETA_MEDIAPIPE))

from reconocimiento_vexa.servicios.reconocimiento import ServicioReconocimiento
from reconocimiento_vexa.calibracion.ventana import VentanaCalibracion
from reconocimiento_vexa.calibracion.perfiles import cargar_calibracion

class VexaController:
    def __init__(self):
        self.state = "CATEGORIES"
        self.current_category = None
        self.current_phrase = None
        self.last_gesture = None

    def process_gesture(self, gesture, repetitions):
        self.last_gesture = f"{gesture} x{repetitions}"

        if self.state == "CATEGORIES":
            if gesture == "G1" and repetitions == 1:
                self.current_category = 1
                self.state = "PHRASES"
                return "Abrir Categoría 1"

            elif gesture == "G2" and repetitions == 1:
                self.current_category = 2
                self.state = "PHRASES"
                return "Abrir Categoría 2"

            elif gesture == "G3" and repetitions == 1:
                self.current_category = 3
                self.state = "PHRASES"
                return "Abrir Categoría 3"
            
            elif gesture == "G4" and repetitions == 1:
                self.current_category = 4
                self.state = "PHRASES"
                return "Abrir Categoría 4"
    
            elif gesture == "G1" and repetitions == 2:
                self.current_category = 5
                self.state = "PHRASES"
                return "Abrir Categoría 5"
        
            elif gesture == "G2" and repetitions == 2:
                self.current_category = 6
                self.state = "PHRASES"
                return "Abrir Categoría 6"

            elif gesture == "G3" and repetitions == 2:
                self.current_category = 7
                self.state = "PHRASES"
                return "Abrir Categoría 7"
            
            elif gesture == "G4" and repetitions == 2:
                self.current_category = 8
                self.state = "PHRASES"
                return "Abrir Categoría 8"

        if self.state == "PHRASES":
            if gesture == "G1" and repetitions == 1:
                self.current_phrase = 1
                return "Seleccionar Frase 1"

            elif gesture == "G2" and repetitions == 1:
                self.current_phrase = 2
                return "Seleccionar Frase 2"

            elif gesture == "G3" and repetitions == 1:
                self.current_phrase = 3
                return "Seleccionar Frase 3"

            elif gesture == "G4" and repetitions == 1:
                self.current_phrase = 4
                return "Seleccionar Frase 4"

            elif gesture == "G5" and repetitions == 1:
                self.current_phrase = 5
                return "Seleccionar Frase 5"    

            elif gesture == "G1" and repetitions == 2:
                self.current_phrase = 6
                return "Seleccionar Frase 6"
                        
            elif gesture == "G2" and repetitions == 2:
                self.current_phrase = 7
                return "Seleccionar Frase 7"

            elif gesture == "G3" and repetitions == 2:
                self.current_phrase = 8
                return "Seleccionar Frase 8"

            elif gesture == "G4" and repetitions == 2:
                self.current_phrase = 9
                return "Seleccionar Frase 9"

            elif gesture == "G5" and repetitions == 2:
                self.current_phrase = 10
                return "Seleccionar Frase 10"
            
        return "Gesto no definido"

class GestureButton(QPushButton):

    def __init__(self, texto, ruta_imagen, parent=None):
        super().__init__(parent)

        self.setMinimumSize(250, 225)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Diseño vertical dentro del botón
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(2)

        # Identificador visual del gesto
        self.identificador = QLabel()
        self.identificador.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.identificador.setStyleSheet("""
            QLabel {
                color: #BFDBFE;
                background-color: #26364A;
                border: 1px solid #60A5FA;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                padding: 5px 18px;
            }
        """)

        self.identificador.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self.identificador.hide()

        layout.addWidget(self.identificador)

        # Fotografía del gesto
        imagen = QLabel()
        imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        imagen.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed
        )

        pixmap = QPixmap(str(ruta_imagen))

        if not pixmap.isNull():
            imagen.setPixmap(
                pixmap.scaled(
                    250,
                    210,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

        layout.addWidget(imagen, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Nombre de la categoría y gesto
        self.etiqueta = QLabel(texto)
        etiqueta = self.etiqueta
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiqueta.setWordWrap(True)
        etiqueta.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed
        )
        etiqueta.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        imagen.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        layout.addWidget(etiqueta, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        self.setStyleSheet("""
            QPushButton {
                background-color: #202938;
                border: 1px solid #4B5563;
                border-radius: 14px;
                color: white;
            }

            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                background: transparent;
            }
        """)
        # Guardar el diseño original de la tarjeta
        self.estilo_normal = self.styleSheet()
        
    def resaltar(self, activo):
        """Activa o desactiva el borde verde de la tarjeta."""

        if activo:
            estilo_verde = self.estilo_normal.replace(
                "border: 1px solid #4B5563;",
                "border: 4px solid #39D98A;"
            )
            self.setStyleSheet(estilo_verde)
        else:
            self.setStyleSheet(self.estilo_normal)

class SidebarGestureButton(QPushButton):
    def __init__(self, texto, ruta_imagen, parent=None):
        super().__init__(parent)

        self.setFixedHeight(215)

        self.setStyleSheet("""
            QPushButton {
                background-color: #202938;
                border: 1px solid #4B5563;
                border-radius: 12px;
            }

            QPushButton:hover {
                background-color: #2D3A4F;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 18, 8, 18)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Identificador del gesto especial
        numero_gesto = Path(ruta_imagen).stem.upper()

        identificador = QLabel(numero_gesto)
        identificador.setAlignment(Qt.AlignmentFlag.AlignCenter)

        identificador.setStyleSheet("""
            QLabel {
                color: #BFDBFE;
                background-color: #26364A;
                border: 1px solid #60A5FA;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                padding: 5px 12px;
            }
        """)

        identificador.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        layout.addWidget(identificador)

        imagen = QLabel()
        imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        imagen.setStyleSheet("background: transparent; border: none;")

        pixmap = QPixmap(str(ruta_imagen))
        imagen.setPixmap(
            pixmap.scaled(
                150,150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

        layout.addWidget(imagen, alignment=Qt.AlignmentFlag.AlignCenter)

        self.etiqueta = QLabel(texto)
        self.etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta.setWordWrap(True)

        self.etiqueta.setStyleSheet("""
            color: white;
            font-size: 17px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)

        layout.addWidget(self.etiqueta, alignment=Qt.AlignmentFlag.AlignCenter)

class GraficaDona(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.porcentaje = None
        self.seleccionada = False
        self.al_hacer_clic = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(180, 180)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        lado = min(self.width(), self.height())
        margen = 18

        rectangulo = QRectF(
            (self.width() - lado) / 2 + margen,
            (self.height() - lado) / 2 + margen,
            lado - 2 * margen,
            lado - 2 * margen
        )

        fondo = QPen(QColor("#334155"), 18)
        painter.setPen(fondo)
        painter.drawEllipse(rectangulo)

        progreso = QPen(QColor("#818CF8"), 18)
        progreso.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progreso)

        if self.porcentaje is not None:
            painter.drawArc(
                rectangulo,
                90 * 16,
                -round(360 * 16 * self.porcentaje / 100)
            )

        fuente = painter.font()
        fuente.setPointSize(22)
        fuente.setBold(True)
        painter.setFont(fuente)

        texto_central = (
            f"{self.porcentaje}%"
            if self.porcentaje is not None
            else "N/D"
        )

        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            texto_central
        )
        # Borde de resaltado para la dona seleccionada
        if self.seleccionada:
            borde = QPen(QColor("#A5B4FC"), 2)
            painter.setPen(borde)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.drawRoundedRect(
                self.rect().adjusted(2, 2, -2, -2),
                15,
                15
            )

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.al_hacer_clic is not None:
                self.al_hacer_clic()

        super().mousePressEvent(event)

class VexaWindow(QMainWindow):
    ADMIN_PASSWORD = "1234"
    PHRASES = {
        categoria: {
            frase: f"Texto de prueba: categoría {categoria}, frase {frase}"
            for frase in range(1, 11)
        }
        for categoria in range(1, 9)
    }

    def __init__(self):
        super().__init__()
        self.controller = VexaController() 
        # Reconocimiento facial para usuarios normales
        # El servicio se creará cuando sea necesario.
        self.servicio_reconocimiento = None
        self.reconocimiento_facial_activo = False 
        self.modo_reconocimiento_actual = None 
        self.reconocimiento_facial_habilitado = False
        self.detencion_facial_solicitada = False
        # Evitar selecciones repetidas durante el destello
        self.transicion_categoria_activa = False
                # Impedir seleccionar otra frase mientras se prepara o reproduce audio
        self.reproduccion_frase_activa = False
        
        # Reproductor de voz de VEXA
        self.reproductor_voz = QMediaPlayer(self)
        self.salida_audio_voz = QAudioOutput(self)
        # Recuperar VEXA si falla la reproducción del audio
        self.reproductor_voz.errorOccurred.connect(
            self.manejar_error_reproduccion
        )
        # Detectar cuándo termina la reproducción de una frase
        self.reproductor_voz.mediaStatusChanged.connect(
            self.verificar_fin_audio_voz
        )

        self.reproductor_voz.setAudioOutput(
            self.salida_audio_voz
        )

        self.salida_audio_voz.setVolume(1.0)

        # Mantener el audio disponible en memoria
        self.buffer_voz = QBuffer(self)     
        # Referencias para la síntesis de voz en segundo plano
        self.hilo_voz = None
        self.trabajador_voz = None
        # Última demostración de voz solicitada
        self.demostracion_voz_pendiente = None
        self.settings_store = QSettings("VEXA", "VEXA")
        
        # Estado del modo experimental
        self.experimental_mode_enabled = self.settings_store.value(
            "experimental_mode_enabled",
            False,
            type=bool
        )
        self.experimental_participant_id = None
        self.experimental_session_id = None
        self.experimental_trial_index = 0
        self.experimental_sequence = []
        self.experimental_ready_confirmed = False
        self.experimental_start_time = None
        self.experimental_response_time = None
        self.experimental_trial_completed = False
        self.experimental_session_started = False
        self.experimental_active_trial_id = None
        self.experimental_detected_gesture = None
        self.experimental_detection_time = None
        self.experimental_neutral_duration = 3.0
        self.experimental_neutral_timer = QTimer(self)
        self.experimental_neutral_timer.setSingleShot(True)
        self.experimental_neutral_timer.timeout.connect(
            self.comprobar_fin_intervalo_neutral
        )
        self.experimental_transition_timer = QTimer(self)
        self.experimental_transition_timer.setSingleShot(True)
        self.experimental_transition_timer.timeout.connect(
            self.avanzar_ensayo_experimental
        )
        # Perfiles creados y guardados por VEXA
        self.profiles = self.settings_store.value(
            "profiles", [], type=list
        )

        # Recuperar el último perfil utilizado
        self.current_profile = self.settings_store.value(
            "last_profile", ""
        )

        # Si el perfil guardado ya no existe, no seleccionar ninguno
        if self.current_profile not in self.profiles:
            self.current_profile = ""

        # Voz seleccionada para el perfil activo
        self.voz_seleccionada = None

        if self.current_profile:
            self.voz_seleccionada = self.settings_store.value(
                f"voz_perfil/{self.current_profile}",
                None
            )

        # Convertir pr4 en Perfil experimental
        self.migrate_experimental_profile()

        # -----------------------------
        # Configuración de la ventana
        # -----------------------------

        self.setWindowTitle("VEXA")
        self.resize(1100, 700)

        # -----------------------------
        # Widget principal
        # -----------------------------

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal:
        # izquierda = menú
        # derecha = contenido

        main_layout = QHBoxLayout(central_widget)

        # -----------------------------
        # Menú lateral
        # -----------------------------

        sidebar = QWidget()
        sidebar.setFixedWidth(220)

        sidebar.setObjectName("vexaSidebar")

        sidebar.setStyleSheet("""
            QWidget#vexaSidebar {
                background-color: #141C29;
            }
        """)

        sidebar_layout = QVBoxLayout(sidebar)

        self.sidebar = sidebar
        self.sidebar.hide()

        # Título

        title = QLabel("VEXA")
        title.setAlignment(Qt.AlignCenter)

        sidebar_layout.addWidget(title)

        # Espacio

        sidebar_layout.addSpacing(30)

        # ----------------------------------
        # Botones del menú lateral
        # ----------------------------------

        self.btn_inicio = QPushButton("⌂  Inicio")
        self.btn_ajustes = QPushButton("⚙  Configuración")
        self.btn_categorias = SidebarGestureButton(
            "\nVolver a categorías\n",
            Path(__file__).resolve().parent / "imagenes_gestos" / "G6.png"
        )

        self.btn_apagar = SidebarGestureButton(
            "\nSalir del sistema\n",
            Path(__file__).resolve().parent / "imagenes_gestos" / "G7.png"
        )

        # ----------------------------------
        # SECCIÓN 1: CONTROLES MANUALES
        # ----------------------------------

        manual_title = QLabel("CONTROLES MANUALES")
        manual_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        manual_title.setStyleSheet("""
            color: #9CA3AF;
            font-size: 12px;
            font-weight: bold;
            background: transparent;
        """)

        sidebar_layout.addWidget(manual_title)
        sidebar_layout.addSpacing(10)

        sidebar_layout.addWidget(self.btn_inicio)
        sidebar_layout.addWidget(self.btn_ajustes)


        # ----------------------------------
        # LÍNEA DIVISORIA

        sidebar_layout.addSpacing(20)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(2)

        separator.setStyleSheet("""
            background-color: #4B5563;
            border: none;
        """)

        sidebar_layout.addWidget(separator)

        sidebar_layout.addSpacing(20)


        # ----------------------------------
        # SECCIÓN 2: CONTROLES POR GESTOS

        gestures_title = QLabel("CONTROLES POR GESTOS")
        gestures_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gestures_title.setStyleSheet("""
            color: #9CA3AF;
            font-size: 12px;
            font-weight: bold;
            background: transparent;
        """)

        sidebar_layout.addWidget(gestures_title)
        sidebar_layout.addSpacing(10)

        # ----------------------------------
        # Grupo fijo de tarjetas de gestos

        gestos_container = QWidget()
        gestos_container.setFixedHeight(436)

        gestos_layout = QVBoxLayout(gestos_container)
        gestos_layout.setContentsMargins(0, 0, 0, 0)
        gestos_layout.setSpacing(6)

        # Espacio reservado para Volver a categorías
        self.categorias_container = QWidget()
        self.categorias_container.setFixedHeight(215)

        categorias_layout = QVBoxLayout(self.categorias_container)
        categorias_layout.setContentsMargins(0, 0, 0, 0)
        categorias_layout.setSpacing(0)

        categorias_layout.addWidget(self.btn_categorias)

        # Ambas tarjetas mantienen exactamente su altura
        self.btn_categorias.setFixedHeight(215)
        self.btn_apagar.setFixedHeight(215)

        gestos_layout.addWidget(self.categorias_container)
        gestos_layout.addWidget(self.btn_apagar)

        # El espacio sobrante queda fuera del grupo
        sidebar_layout.addWidget(gestos_container)
                
        # ----------------------------------
        # TAMAÑO DE LOS BOTONES

        for boton in [
            self.btn_inicio,
            self.btn_ajustes,
            self.btn_categorias,
            self.btn_apagar
        ]:
            boton.setMinimumHeight(58)
        # Botones manuales más grandes y legibles
        for boton in [self.btn_inicio, self.btn_ajustes]:
            boton.setMinimumHeight(70)
            boton.setStyleSheet("""
                QPushButton {
                    font-size: 21px;
                    font-weight: bold;
                    padding: 8px;
                }
            """)


        # Espacio sobrante debajo de los botones
        sidebar_layout.addStretch()

        # -----------------------------
        # Área de contenido

        self.pages = QStackedWidget()
        self.pages.setStyleSheet("""
            QStackedWidget {
                background-color: #242F40;
            }
        """)

        # Crear páginas

        self.pages.addWidget(self.create_home_page())       # 0
        self.pages.addWidget(self.create_categories_page()) # 1
        self.pages.addWidget(self.create_gestures_page())   # 2
        self.pages.addWidget(self.create_control_page())    # 3
        self.pages.addWidget(self.create_data_page())       # 4
        self.pages.addWidget(self.create_settings_page())   # 5
        self.pages.addWidget(self.create_phrases_page())    # 6
        self.pages.addWidget(self.create_profile_page())    # 7
        self.pages.addWidget(self.create_policies_page())   # 8
        self.pages.addWidget(self.create_setup_page())      # 9
        self.pages.addWidget(self.create_admin_page())      # 10
        self.pages.addWidget(self.create_manage_profiles_page())  # 11
        self.pages.addWidget(self.create_experimental_page())      # 12
        self.pages.addWidget(self.create_experimental_subjects_page())  # 13
        self.pages.addWidget(self.create_voice_selection_page())  # 14
        self.ventana_calibracion = VentanaCalibracion(
            id_perfil="PRUEBA_VISUAL", parent=self
        )
        self.pages.addWidget(self.ventana_calibracion)  # 15

        self.pages.currentChanged.connect(
            self.update_sidebar_visibility
        )
        self.pages.currentChanged.connect(
            self.controlar_salida_calibracion
        )
        self.pages.currentChanged.connect(
            self.controlar_reconocimiento_por_pantalla
        )
        
        # Reservar Espacio para iniciar los ensayos experimentales
        self.experimental_space_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Space),
            self
        )

        self.experimental_space_shortcut.setContext(
            Qt.ShortcutContext.ApplicationShortcut
        )

        self.experimental_space_shortcut.activated.connect(
            self.iniciar_ensayo_con_espacio
        )

        # Atajo temporal de depuración: simular finalización con F9
        self.experimental_test_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_F9),
            self
        )

        self.experimental_test_shortcut.setContext(
            Qt.ShortcutContext.ApplicationShortcut
        )

        self.experimental_test_shortcut.activated.connect(
            self.probar_avance_experimental
        )        
        
        # -----------------------------
        # Conectar botones


# Conectar botones del menú lateral

        self.btn_inicio.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )
        self.btn_categorias.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )

        self.btn_ajustes.clicked.connect(
            lambda: self.pages.setCurrentIndex(5)
        )

        self.btn_apagar.clicked.connect(
            self.close
        )


        # -----------------------------
        # Añadir todo a la ventana
    

        # Contenedor del contenido principal
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Las páginas normales siguen ocupando el espacio principal
        self.content_layout.addWidget(self.pages, 1)

        # Panel informativo del modo experimental
        self.experimental_panel = QWidget()
        self.experimental_panel.setObjectName("experimentalPanel")
        self.experimental_panel.setStyleSheet("""
            QWidget#experimentalPanel {
                background-color: #172334;
                border-top: 2px solid #4B88A2;
            }
        """)

        experimental_panel_layout = QVBoxLayout(self.experimental_panel)
        experimental_panel_layout.setContentsMargins(16, 10, 16, 10)
        experimental_panel_layout.setSpacing(6)

        self.experimental_panel_title = QLabel("VEXA — Modo experimental")
        self.experimental_panel_title.setStyleSheet(
            "font-size: 14px; border: none;"
        )

        self.experimental_panel_instruction = QLabel(
            "Esperando instrucciones del ensayo..."
        )
        self.experimental_panel_instruction.setWordWrap(True)
        self.experimental_panel_instruction.setStyleSheet(
            "font-size: 15px; border: none;"
        )

        self.experimental_panel_camera = QLabel(
            "📷 Vista de cámara — pendiente de conectar MediaPipe"
        )
        self.experimental_panel_camera.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.experimental_panel_camera.setMinimumHeight(90)
        self.experimental_panel_camera.setStyleSheet("""
            background-color: #242F40;
            border: 1px dashed #4B88A2;
            border-radius: 8px;
            padding: 12px;
        """)

        experimental_panel_layout.addWidget(self.experimental_panel_title)

        self.btn_salir_experimento = QPushButton("Salir del experimento")

        self.btn_salir_experimento.setStyleSheet("""
            QPushButton {
                background-color: #394B63;
                color: white;
                font-size: 13px;
                padding: 8px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #526783;
            }
        """)

        self.btn_salir_experimento.clicked.connect(
            self.confirmar_salida_experimental
        )
        self.btn_salir_experimento.setFixedWidth(175)
        
        experimental_panel_layout.addWidget(
            self.btn_salir_experimento,
            alignment=Qt.AlignmentFlag.AlignRight
        )

        self.experimental_panel_instruction.hide()
        # cámara en  panel lateral experimental
        self.experimental_panel_camera.hide()
        self.content_layout.addWidget(self.experimental_panel)

        # Oculto hasta activar el modo exp
        self.experimental_panel.hide()

        # menú lateral y contenido principal
        self.experimental_camera_sidebar = QWidget()
        self.experimental_camera_sidebar.setFixedWidth(260)
        self.experimental_camera_sidebar.setStyleSheet("""
            background-color: #172334;
            border-right: 2px solid #4B88A2;
        """)

        camera_layout = QVBoxLayout(self.experimental_camera_sidebar)
        camera_layout.setContentsMargins(12, 16, 12, 16)

        self.experimental_camera_label = QLabel(
            "Cámara experimental\n\nEsperando MediaPipe..."
        )
        self.experimental_camera_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.experimental_camera_label.setWordWrap(True)
        self.experimental_camera_label.setMinimumHeight(300)
        self.experimental_camera_label.setStyleSheet("""
            background-color: #242F40;
            border: 1px dashed #4B88A2;
            border-radius: 8px;
            font-size: 15px;
        """)

        camera_layout.addWidget(self.experimental_camera_label)
        
        # Fotps los gestos especiales
        for numero, descripcion in [
            (6, "G6 — Volver a categorías"),
            (7, "G7 — Salir del sistema")
        ]:
            referencia = QLabel()

            ruta = (
                Path(__file__).resolve().parent
                / "imagenes_gestos"
                / f"G{numero}.png"
            )

            imagen = QPixmap(str(ruta))

            if not imagen.isNull():
                referencia.setPixmap(
                    imagen.scaled(
                        190,
                        140,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )

            referencia.setAlignment(Qt.AlignmentFlag.AlignCenter)

            texto = QLabel(descripcion)
            texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
            texto.setWordWrap(True)

            camera_layout.addWidget(referencia)
            camera_layout.addWidget(texto)       
        
        camera_layout.addStretch()

        self.experimental_camera_sidebar.hide()
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.experimental_camera_sidebar)
        main_layout.addLayout(self.content_layout)        

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.sidebar = sidebar
        self.sidebar.hide()

    def manejar_error_reproduccion(self, error, mensaje):
        """Recupera VEXA si falla el reproductor de audio."""

        if error == QMediaPlayer.Error.NoError:
            return

        self.manejar_error_voz(
            f"Error de reproducción: {mensaje}"
        )

    def reproducir_audio_voz(self, datos):
        """Reproduce el audio generado en memoria."""
        self.reproductor_voz.stop()
        self.reproductor_voz.setSourceDevice(None)

        self.buffer_voz.close()
        self.buffer_voz.setData(QByteArray(datos))
        self.buffer_voz.open(QIODevice.OpenModeFlag.ReadOnly)

        self.reproductor_voz.setSourceDevice(self.buffer_voz)

        # Tiempo preparación de audio
        QTimer.singleShot(
            150,
            self.reproductor_voz.play
        )

    def verificar_fin_audio_voz(self, estado):
        if estado == QMediaPlayer.MediaStatus.EndOfMedia:

            # Quitar el resaltado frase 
            if getattr(self, "tarjeta_frase_activa", None) is not None:
                self.tarjeta_frase_activa.resaltar(False)
                self.tarjeta_frase_activa = None

            # Regresar a categorías después de frase
            if self.reproduccion_frase_activa:
                self.pages.setCurrentIndex(1)

            # Seleccionar una nva frase
            self.reproduccion_frase_activa = False
            # Reconocer categor después de voz
            if (
                self.reconocimiento_facial_habilitado
                and not self.detencion_facial_solicitada
                and not self.experimental_mode_enabled
            ):
                QTimer.singleShot(
                    0,
                    self.reanudar_reconocimiento_facial_normal
                )
    
    def audio_voz_listo(self, datos):
        """Recibe el audio sintetizado y lo reproduce."""
        self.reproducir_audio_voz(datos)

    def manejar_error_voz(self, mensaje):
        """Recupera VEXA si falla la síntesis de una frase."""

        print("Error de voz VEXA:", mensaje)

        # Quitar el borde verde de frase
        if getattr(self, "tarjeta_frase_activa", None) is not None:
            self.tarjeta_frase_activa.resaltar(False)
            self.tarjeta_frase_activa = None

        # Regresar a categorías
        self.pages.setCurrentIndex(1)

        # Permitir nuevas selecciones
        self.reproduccion_frase_activa = False
        # Nvas categorías después de voz
        if (
                self.reconocimiento_facial_habilitado
                and not self.detencion_facial_solicitada
                and not self.experimental_mode_enabled
            ):
                QTimer.singleShot(
                    0,
                    self.reanudar_reconocimiento_facial_normal
                )

    def abrir_seleccion_voz(self):
        self.origen_seleccion_voz = self.pages.currentIndex()
        self.btn_female_voice.setChecked(
            self.voz_seleccionada == "Femenina"
        )

        self.btn_male_voice.setChecked(
            self.voz_seleccionada == "Masculina"
        )

        self.pages.setCurrentIndex(14)

    def regresar_desde_seleccion_voz(self):
        """Detiene la demostración y regresa a Configuración."""

        # Cancelar cualquier demostración que esté esperando su turno
        self.demostracion_voz_pendiente = None

        # Detener audio sonando
        self.reproductor_voz.stop()

        # Regresar a Configuración
        if self.get_profile_progress()["setup_step"] == 2:
            # Usuario llega desde la preparación inicial
            if self.voz_seleccionada:
                # Guardar voz elegida
                self.settings_store.setValue(
                    f"voz_perfil/{self.current_profile}",
                    self.voz_seleccionada
                )
                # Confirmar selección de voz completada
                self.update_profile_progress(
                    setup_step=3
                )
                QMessageBox.information(
                    self,
                    "Preparación completada",
                    "La preparación de este perfil ha terminado."
                )

                # Continuar hacia Categorías
                self.route_after_policies()

            else:
                QMessageBox.information(
                    self,
                    "Selecciona una voz",
                    "Elige una voz antes de continuar."
                )

        else:
            # El usuario llegó desde Configuración
            if self.voz_seleccionada and self.current_profile:
                self.settings_store.setValue(
                    f"voz_perfil/{self.current_profile}",
                    self.voz_seleccionada
                )

            self.pages.setCurrentIndex(5)

    def guardar_voz_perfil(self, tipo_voz):
        # Mantener seleccionada una sola voz
        self.btn_female_voice.setChecked(
            tipo_voz == "Femenina"
        )

        self.btn_male_voice.setChecked(
            tipo_voz == "Masculina"
        )
        # Actualizar voz seleccionada en memoria
        self.voz_seleccionada = tipo_voz
    
    
    def demostrar_voz_vexa(self, tipo_voz):
        """Solicita una demostración de voz sin crear hilos simultáneos."""

        texto = f"Hola, esta es la voz {tipo_voz.lower()} de VEXA."

        # Detener el audio anterior si está reproduciéndose
        self.reproductor_voz.stop()

        if self.hilo_voz is not None:
            # Recordar solamente la última voz solicitada
            self.demostracion_voz_pendiente = (
                texto,
                tipo_voz
            )
            return

        self.demostracion_voz_pendiente = None
        self.hablar_vexa(texto, tipo_voz)

    def hablar_vexa(self, texto, tipo_voz="Femenina"):
        """Inicia la síntesis de una frase sin bloquear VEXA."""

        if self.hilo_voz is not None:
            print("VEXA: hay una frase en preparación.")
            return

        self.hilo_voz = QThread(self)

        self.trabajador_voz = TrabajadorVoz(
            texto,
            tipo_voz
        )

        self.trabajador_voz.moveToThread(self.hilo_voz)
           
        # Iniciar la síntesis cuando arranque el hilo
        self.hilo_voz.started.connect(
            self.trabajador_voz.ejecutar
        )

        # Reproducir el audio cuando esté listo
        self.trabajador_voz.audio_listo.connect(
            self.audio_voz_listo
        )

        # Recuperar VEXA si falla la síntesis de voz
        self.trabajador_voz.error.connect(
            self.manejar_error_voz
        )

        # Detener el hilo cuando termine la síntesis
        self.trabajador_voz.terminado.connect(
            self.hilo_voz.quit
        )
        # Liberar el trabajador cuando termine
        self.trabajador_voz.terminado.connect(
            self.trabajador_voz.deleteLater
        )

        # Avisar cuando el hilo haya finalizado
        self.hilo_voz.finished.connect(
            self.limpiar_hilo_voz
        )
        # Comenzar la síntesis de voz en segundo plano
        self.hilo_voz.start()

    def limpiar_hilo_voz(self):
        """Libera las referencias cuando finaliza el hilo."""
        hilo = self.hilo_voz

        self.hilo_voz = None
        self.trabajador_voz = None

        if hilo is not None:
            hilo.deleteLater()
        
        # Atender la última demostración solicitada
        if self.demostracion_voz_pendiente is not None:
            texto, tipo_voz = self.demostracion_voz_pendiente
            self.demostracion_voz_pendiente = None
            self.hablar_vexa(texto, tipo_voz)

    # ==================================================
    # PÁGINAS


    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addStretch()

        title = QLabel("Bienvenido a VEXA")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 38px;
            font-weight: bold;
            padding: 15px;
        """)

        subtitle = QLabel(
            "Tu comunicación, a tu manera."
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 20px;
            color: #D1D5DB;
            padding: 10px;
        """)

        description = QLabel(
            "Haz clic en Iniciar para comenzar."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("font-size: 16px;")

        start_button = QPushButton("Iniciar")
        start_button.setMinimumSize(240, 65)
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                border-radius: 12px;
                font-size: 20px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #6366F1;
            }
        """)

        admin_button = QPushButton( #Botón de acceso admin
            "Modo administrador"
        )

        admin_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9CA3AF;
                border: none;
                font-size: 12px;
                padding: 6px;
            }
            QPushButton:hover {
                color: #F9FAFB;
            }
        """)

        admin_button.clicked.connect(
            self.open_admin_login
        )

        start_button.clicked.connect(
            self.open_profile_from_home
        )

        layout.addSpacing(12)
        layout.addWidget(
            admin_button,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(15)
        layout.addWidget(description)
        layout.addSpacing(25)
        layout.addWidget(
            start_button,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        layout.addStretch()

        return page

    def migrate_experimental_profile(self):
        old_name = "pr4"
        new_name = "Perfil experimental"

        profiles = self.settings_store.value(
            "profiles", [], type=list
        )

        # Comprobar que pr4 ocupa el cuarto espacio
        if len(profiles) != 4:
            return

        if profiles[3] != old_name:
            return

        # Evitar conflictos con nombres existentes
        if any(
            name.casefold() == new_name.casefold()
            for name in profiles[:3]
        ):
            return

        all_progress = self.settings_store.value(
            "profile_progress", {}
        )

        if not isinstance(all_progress, dict):
            all_progress = {}

        # No sobrescribir datos que ya existan
        if new_name in all_progress:
            QMessageBox.warning(
                self,
                "Migración pendiente",
                "Ya existen datos asociados a "
                "'Perfil experimental'. "
                "No se realizó ningún cambio."
            )
            return

        # Trasladar el progreso anterior
        if old_name in all_progress:
            all_progress[new_name] = all_progress.pop(
                old_name
            )

        # Actualizar la lista de perfiles
        profiles[3] = new_name

        # Actualizar el último perfil seleccionado
        last_profile = self.settings_store.value(
            "last_profile", ""
        )

        if last_profile == old_name:
            self.settings_store.setValue(
                "last_profile", new_name
            )

        # Actualizar el perfil activo
        if self.current_profile == old_name:
            self.current_profile = new_name

        self.settings_store.setValue(
            "profile_progress", all_progress
        )

        self.settings_store.setValue(
            "profiles", profiles
        )

        self.profiles = profiles
        self.settings_store.sync()

    def save_profile(self, profile_name):
        self.current_profile = profile_name
        self.settings_store.setValue(
            "last_profile", profile_name
        )
        self.settings_store.sync()
        self.update_active_profile_label()

    def get_profile_progress(self, profile_name=None):
        if profile_name is None:
            profile_name = self.current_profile

        all_progress = self.settings_store.value(
            "profile_progress", {}
        )

        if not isinstance(all_progress, dict):
            all_progress = {}

        progress = all_progress.get(profile_name, {})

        if not isinstance(progress, dict):
            progress = {}

        return {
            "policies_accepted": progress.get(
                "policies_accepted", False
            ),
            "setup_step": progress.get("setup_step", 0),
        }
    
    def update_profile_progress(self, **updates):
        if not self.current_profile:
            return

        all_progress = self.settings_store.value(
            "profile_progress", {}
        )

        if not isinstance(all_progress, dict):
            all_progress = {}

        progress = all_progress.get(
            self.current_profile, {}
        )

        if not isinstance(progress, dict):
            progress = {}

        progress.update(updates)
        all_progress[self.current_profile] = progress

        self.settings_store.setValue(
            "profile_progress", all_progress
        )
        self.settings_store.sync()

    def route_after_policies(self):
        progress = self.get_profile_progress()

        if not progress["policies_accepted"]:
            self.pages.setCurrentIndex(8)

        elif progress["setup_step"] >= 3:
            if (
                self.current_profile == "Perfil experimental"
                and self.experimental_mode_enabled
            ):
                self.pages.setCurrentIndex(13)
            else:
                self.pages.setCurrentIndex(1)

        else:
            if progress["setup_step"] == 2:
                self.abrir_seleccion_voz()
            elif progress["setup_step"] == 1:
                self.abrir_calibracion_perfil()
            else:
                self.update_setup_page()
                self.pages.setCurrentIndex(9)

    def closeEvent(self, event):
        ventana = getattr(self, "ventana_calibracion", None)

        if ventana is not None:
            try:
                ventana.detener()
            except RuntimeError as error:
                event.ignore()
                QMessageBox.warning(
                    self,
                    "Cámara de calibración",
                    "La cámara todavía se está cerrando.\n"
                    "Por seguridad, VEXA permanecerá abierta.\n\n"
                    f"{error}"
                )
                return

        # Detener el reconocimiento facial antes de cerrar VEXA.
        servicio = getattr(self, "servicio_reconocimiento", None)

        if servicio is not None:
            servicio.cerrar()

            hilo = getattr(servicio, "hilo", None)

            if hilo is not None and hilo.isRunning():
                event.ignore()
                QMessageBox.warning(
                    self,
                    "Reconocimiento facial",
                    "La cámara de reconocimiento todavía se está cerrando.\n"
                    "Por seguridad, VEXA permanecerá abierta.\n"
                    "Intenta cerrar nuevamente en unos segundos."
                )
                return

        super().closeEvent(event)
        

    def controlar_salida_calibracion(self, index):
        ventana = getattr(self, "ventana_calibracion", None)

        if ventana is None:
            return

        if self.pages.currentWidget() is ventana:
            return

        hilo = getattr(ventana, "hilo", None)

        if hilo is None or not hilo.isRunning():
            return

        try:
            ventana.detener()
        except RuntimeError as error:
            QMessageBox.warning(
                self,
                "Cámara de calibración",
                "La cámara todavía se está cerrando.\n"
                "Volveremos a la pantalla de calibración "
                "para proteger la captura.\n\n"
                f"{error}"
            )

            # Regresar a la ventana existente, sin crear otra.
            if self.pages.currentWidget() is not ventana:
                self.pages.setCurrentWidget(ventana)
    
    def abrir_calibracion_perfil(self):
        perfil = self.current_profile

        if not perfil:
            QMessageBox.warning(
                self,
                "Calibración",
                "Primero selecciona un perfil."
            )
            return

        if perfil == "Perfil experimental":
            QMessageBox.warning(
                self,
                "Calibración",
                "Esta calibración corresponde a perfiles normales."
            )
            return

        anterior = self.ventana_calibracion

        try:
            anterior.detener()
        except RuntimeError as error:
            QMessageBox.warning(
                self,
                "Cámara ocupada",
                str(error)
            )
            return

        nueva = VentanaCalibracion(
            id_perfil=perfil,
            parent=self
        )

        nueva.calibracion_finalizada.connect(
            self.calibracion_perfil_finalizada
        )
        nueva.calibracion_cancelada.connect(
            self.calibracion_perfil_cancelada
        )

        nueva.calibracion_no_valida.connect(
            self.calibracion_perfil_error
        )
        nueva.error.connect(
            self.calibracion_perfil_error
        )

        self.pages.addWidget(nueva)
        self.pages.removeWidget(anterior)
        anterior.deleteLater()

        self.ventana_calibracion = nueva
        self.pages.setCurrentWidget(nueva)


    def calibracion_perfil_error(self, mensaje):
        ventana = getattr(self, "ventana_calibracion", None)

        if ventana is None:
            return

        # Un error no debe completar la preparación.
        QMessageBox.warning(
            self,
            "Calibración facial",
            "La calibración no pudo completarse.\n"
            "El progreso de este perfil se conservará.\n\n"
            f"{mensaje}"
        )

    def calibracion_perfil_finalizada(self, id_perfil, ruta):
        ventana = getattr(self, "ventana_calibracion", None)

        # La señal debe proceder de la ventana del perfil activo.
        if (
            not id_perfil
            or id_perfil != self.current_profile
            or ventana is None
            or ventana.id_perfil != id_perfil
            or self.pages.currentWidget() is not ventana
        ):
            QMessageBox.warning(
                self,
                "Calibración",
                "La calibración no corresponde al perfil activo."
            )
            return

        if self.get_profile_progress()["setup_step"] != 1:
            return

        # Verificar el archivo mediante el validador oficial de Ale.
        try:
            cargar_calibracion(
                id_perfil,
                carpeta=ventana.carpeta_calibraciones
            )
        except (OSError, ValueError, KeyError, TypeError) as error:
            QMessageBox.warning(
                self,
                "Calibración no válida",
                "No se pudo validar la calibración guardada.\n"
                "La preparación seguirá pendiente.\n\n"
                f"{error}"
            )
            return

        self.update_profile_progress(setup_step=2)
        self.abrir_seleccion_voz()


    def calibracion_perfil_cancelada(self):
        self.update_setup_page()
        self.pages.setCurrentIndex(9)
        
    def update_sidebar_visibility(self, index):

        # Durante el experimento, ocultar el menú manual
        en_experimento = (
            index in [1, 6]
            and self.experimental_panel.isVisible()
            and self.experimental_session_id is not None
        )

        # Restaurar el texto y estilo normal fuera del experimento
        if not en_experimento and index == 1:
            self.categories_description.setText(
                "Selecciona una categoría para consultar sus frases."
            )

            self.categories_description.setAlignment(
                Qt.AlignmentFlag.AlignLeft
            )

            self.categories_description.setMinimumHeight(0)

            self.categories_description.setStyleSheet("""
                font-size: 15px;
                background: transparent;
                border: none;
            """)

        if en_experimento:
            self.sidebar.hide()
            return

        # Funcionamiento normal de VEXA
        if index in [1, 5, 6]:
            self.sidebar.show()
        else:
            self.sidebar.hide()

        # Botones habituales del menú lateral
        self.btn_categorias.setVisible(index in [5, 6])
        self.btn_ajustes.setVisible(index in [1, 6])
        self.btn_apagar.setVisible(index in [1, 5, 6])

    def create_gestures_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        title = QLabel("Gestos")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")

        description = QLabel(
            "Aquí podrás consultar los gestos disponibles "
            "para controlar VEXA."
        )

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(description)

        layout.addStretch()

        return page

    def create_control_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        title = QLabel("Control y reconocimiento")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")

        status = QLabel(
            "Gesto detectado: Ninguno\n"
            "Confianza: --"
        )

        status.setStyleSheet(
            "font-size: 20px; padding: 20px;"
        )

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(status)

        layout.addStretch()

        return page
    
    def get_vexa_categories(self):
        return {
            1: {
                "nombre": "Respuestas",
                "frases": [
                    "Sí",
                    "No",
                    "Tal vez",
                    "No sé",
                    "No entiendo"
                ]
            },

            2: {
                "nombre": "Cortesía",
                "frases": [
                    "Hola",
                    "Adiós",
                    "Gracias",
                    "Por favor",
                    "De nada"
                ]
            },

            3: {
                "nombre": "Estado",
                "frases": [
                    "Bien",
                    "Mal",
                    "Tengo frío",
                    "Tengo calor",
                    "Más o menos"
                ]
            },

            4: {
                "nombre": "Emergencia",
                "frases": [
                    "Es una emergencia",
                    "Llama al médico",
                    "Llama a mi familia",
                    "No puedo respirar bien",
                    "Necesito ayuda ahora"
                ]
            },

            5: {
                "nombre": "Necesidades básicas",
                "frases": [
                    "Tengo sed",
                    "Tengo hambre",
                    "Quiero ir al baño",
                    "Quiero descansar",
                    "Necesito mi medicamento"
                ]
            },

            6: {
                "nombre": "Salud/ Comodidad",
                "frases": [
                    "Tengo dolor",
                    "Me siento mal",
                    "Quiero cambiar de posición",
                    "Quiero cambiar de ropa",
                    "Quiero ir a casa"
                ]
            },

            7: {
                "nombre": "Afecto y emociones",
                "frases": [
                    "Te quiero",
                    "Te extraño",
                    "Estoy feliz",
                    "Estoy triste",
                    "Lo siento"
                ]
            },

            8: {
                "nombre": "Ocio y entretenimiento",
                "frases": [
                    "Quiero ver televisión",
                    "Quiero escuchar música",
                    "Quiero ver una película",
                    "Quiero jugar",
                    "Quiero salir"
                ]
            }
        }

    def show_registered_subject_dialog(self):
        participantes = obtener_participantes()

        if not participantes:
            QMessageBox.information(
                self,
                "Sin sujetos registrados",
                "Todavía no hay sujetos de prueba registrados."
            )
            return

        opciones = [
            participante["codigo"]
            for participante in participantes
        ]

        codigo, aceptado = QInputDialog.getItem(
            self,
            "Sujeto registrado",
            "Selecciona un sujeto de prueba:",
            opciones,
            0,
            False
        )

        if not aceptado:
            return
                
        participante = next(
            p for p in participantes
            if p["codigo"] == codigo
        )

        self.experimental_participant_id = participante["id"]
        self.experimental_participant_code = participante["codigo"]
        sesiones = obtener_sesiones_participante(
            self.experimental_participant_id
        )
        if sesiones:
            detalle = "\n".join(
                f"Sesión {sesion['numero_sesion']} — "
                f"{sesion['estado']}"
                for sesion in sesiones
            )
        else:
            detalle = "Este sujeto todavía no tiene sesiones."

        QMessageBox.information(
            self,
            "Sesiones del sujeto",
            f"Sujeto: {self.experimental_participant_code}\n\n"
            f"{detalle}"
        )

        if consentimiento_esta_verificado(
            self.experimental_participant_id
        ):
            mensaje = QMessageBox(self)
            mensaje.setWindowTitle("Consentimiento registrado")
            mensaje.setIcon(QMessageBox.Icon.Information)
            mensaje.setText(
                f"El consentimiento informado físico del sujeto "
                f"{codigo} ya fue verificado anteriormente.\n\n"
                "Puedes continuar con la gestión de sus sesiones."
            )

            btn_nueva_sesion = mensaje.addButton(
                "＋ Nueva sesión",
                QMessageBox.ButtonRole.ActionRole
            )
            btn_ver_sesiones = mensaje.addButton(
                "Ver sesiones existentes",
                QMessageBox.ButtonRole.ActionRole
            )

            mensaje.addButton(
                "Cerrar",
                QMessageBox.ButtonRole.RejectRole
            )

            mensaje.exec()

            if mensaje.clickedButton() == btn_ver_sesiones:
                sesiones = obtener_sesiones_participante(
                    self.experimental_participant_id
                )

                if not sesiones:
                    QMessageBox.information(
                        self,
                        "Sesiones existentes",
                        f"El sujeto {codigo} todavía no tiene sesiones."
                    )
                    return

                opciones_sesiones = [
                    f"Sesión {sesion['numero_sesion']} "
                    f"(ID: {sesion['id']}) — "
                    f"Estado: {sesion['estado']}"
                    for sesion in sesiones
                ]

                opcion, aceptado = QInputDialog.getItem(
                    self,
                    "Seleccionar sesión",
                    f"Selecciona una sesión del sujeto {codigo}:",
                    opciones_sesiones,
                    0,
                    False
                )

                if not aceptado:
                    return

                indice = opciones_sesiones.index(opcion)
                sesion_seleccionada = sesiones[indice]

                if sesion_seleccionada["estado"] != "pendiente":
                    QMessageBox.warning(
                        self,
                        "Sesión no disponible",
                        "Esta sesión no está pendiente y no puede "
                        "ejecutarse nuevamente.\n\n"
                        "Selecciona una sesión pendiente "
                        "o crea una nueva sesión."
                    )
                    return          
            
                self.experimental_session_id = sesion_seleccionada["id"]
            
                secuencia = obtener_secuencia_experimental(
                    self.experimental_session_id
                )
                if not secuencia:
                    QMessageBox.warning(
                        self,
                        "Sesión sin ensayos",
                        "Esta sesión todavía no tiene ensayos "
                        "experimentales preparados.\n\n"
                        "No es posible iniciar la prueba."
                    )
                    return
                
                if len(secuencia) != 24:
                    QMessageBox.warning(
                        self,
                        "Secuencia incompleta",
                        f"Esta sesión tiene {len(secuencia)} ensayos, "
                        "pero el protocolo experimental requiere 24.\n\n"
                        "No es posible iniciar la prueba."
                    )
                    return

                numeros_ensayos = [
                    ensayo["numero_iteracion"]
                    for ensayo in secuencia
                ]

                if numeros_ensayos != list(range(1, 25)):
                    QMessageBox.warning(
                        self,
                        "Orden experimental inválido",
                        "Los ensayos deben estar ordenados "
                        "y numerados consecutivamente del 1 al 24.\n\n"
                        "No es posible iniciar la prueba."
                    )
                    return
                
                conteo_gestos = Counter(
                    ensayo["gesto_solicitado"]
                    for ensayo in secuencia
                )

                gestos_esperados = {
                    "G1", "G2", "G3", "G4",
                    "G5", "G6", "G7", "ninguno"
                }

                if (
                    set(conteo_gestos) != gestos_esperados
                    or any(
                        cantidad != 3
                        for cantidad in conteo_gestos.values()
                    )
                ):
                    QMessageBox.warning(
                        self,
                        "Secuencia experimental inválida",
                        "La sesión no cumple con la distribución "
                        "experimental requerida.\n\n"
                        "Cada gesto, incluido 'ninguno', "
                        "debe aparecer exactamente 3 veces."
                    )
                    return

                self.experimental_transition_timer.stop()
                self.experimental_neutral_timer.stop()
                self.experimental_sequence = secuencia
                self.experimental_trial_index = 0
                self.experimental_ready_confirmed = False
                self.experimental_start_time = None
                self.experimental_response_time = None
                self.experimental_trial_completed = False
                self.experimental_session_started = False
                self.experimental_active_trial_id = None 
                self.experimental_detected_gesture = None  
                self.experimental_detection_time = None             
                self.experimental_ready.setText(
                    "Presiona ESPACIO cuando estés listo"
                )

                QMessageBox.information(
                    self,
                    "Sesión seleccionada",
                    f"Seleccionaste la sesión "
                    f"{sesion_seleccionada['numero_sesion']} "
                    f"del sujeto {codigo}.\n\n"
                    f"ID: {self.experimental_session_id}\n"
                    f"Ensayos preparados: {len(secuencia)}"
                )

                if self.experimental_sequence:
                    self.mostrar_ensayo_experimental()

                    ensayo_actual = self.experimental_sequence[self.experimental_trial_index]

                    instruccion = obtener_instruccion_experimental(
                        ensayo_actual["gesto_solicitado"]
                    )

                    # Mantener la instrucción del panel experimental
                    self.experimental_panel_instruction.setText(instruccion)

                    # Mostrar la instrucción arriba de las categorías
                    self.categories_description.setText(instruccion)
                    self.categories_description.setAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                    self.categories_description.setStyleSheet("""
                        QLabel {
                            font-size: 26px;
                            font-weight: bold;
                            color: #FFFFFF;

                            background-color: #172334;
                            border: 2px solid #4B88A2;
                            border-radius: 14px;

                            padding: 20px;
                        }
                    """)

                    self.categories_description.setMinimumHeight(100)    

                # Mostrar el panel experimental
                self.experimental_panel.show()

                # Mostrar la cámara lateral experimental
                self.experimental_camera_sidebar.show()

                # Comenzar desde las categorías normales
                self.pages.setCurrentIndex(1)
                QApplication.processEvents()
                print(
                    "DIAGNÓSTICO PANEL:",
                    "visible =", self.experimental_panel.isVisible(),
                    "altura panel =", self.experimental_panel.height(),
                    "altura páginas =", self.pages.height(),
                    "altura ventana =", self.height(),
                    "posición Y panel =", self.experimental_panel.mapToGlobal(
                        self.experimental_panel.rect().topLeft()
                    ).y(),
                    "posición Y ventana =", self.mapToGlobal(
                        self.rect().topLeft()
                    ).y(),
                    "altura pantalla =", self.screen().geometry().height(),
                    "altura disponible =", self.screen().availableGeometry().height(),
                    flush=True
                )
                return

            if mensaje.clickedButton() == btn_nueva_sesion:
                try:
                    sesion_id = crear_sesion(
                        self.experimental_participant_id
                    )

                    secuencia = preparar_iteraciones_experimentales(
                        sesion_id
                    )

                    self.experimental_session_id = sesion_id                    
                    QMessageBox.information(
                        self,
                        "Sesión creada",
                        f"Se creó correctamente una sesión "
                        f"experimental para el sujeto {codigo}.\n\n"
                        f"ID: {self.experimental_session_id}\n"
                        f"Ensayos preparados: {len(secuencia)}"
                    )

                except (ValueError, sqlite3.Error) as error:
                    QMessageBox.warning(
                        self,
                        "No se pudo crear la sesión",
                        str(error)
                    )

            return

        confirmacion = QMessageBox(self)
        confirmacion.setWindowTitle("Consentimiento informado")
        confirmacion.setIcon(
            QMessageBox.Icon.Question
        )
        confirmacion.setText(
            f"Sujeto: {codigo}\n\n"
            "Antes de iniciar una sesión experimental, "
            "el investigador debe verificar que este sujeto "
            "haya firmado su consentimiento informado físico."
        )

        confirmacion.setStandardButtons(
            QMessageBox.StandardButton.Ok
            | QMessageBox.StandardButton.Cancel
        )

        casilla_consentimiento = QCheckBox(
            "He verificado el consentimiento informado "
            "físico firmado de este sujeto."
        )

        casilla_consentimiento.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
                spacing: 10px;
            }

            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                background-color: white;
                border: 2px solid #60A5FA;
                border-radius: 5px;
            }

            QCheckBox::indicator:checked {
                background-color: #60A5FA;
                border: 2px solid white;
                image: url(none);
            }
        """)

        texto_consentimiento = (
            "He verificado el consentimiento informado "
            "físico firmado de este sujeto."
        )

        casilla_consentimiento.toggled.connect(
            lambda marcado: casilla_consentimiento.setText(
                ("✓  " if marcado else "") + texto_consentimiento
            )
        )

        confirmacion.setCheckBox(casilla_consentimiento)

        respuesta = confirmacion.exec()

        if respuesta != QMessageBox.StandardButton.Ok:
            return
        
        if not casilla_consentimiento.isChecked():
            QMessageBox.warning(
                self,
                "Consentimiento pendiente",
                "No se ha confirmado la verificación del "
                "consentimiento informado físico.\n\n"
                "No se puede continuar con la sesión experimental."
            )
            return
        guardar_verificacion_consentimiento(
                self.experimental_participant_id
        )

        print("Base de datos utilizada:", DB_PATH)
        print(
            "Participante verificado:",
            self.experimental_participant_id
        )

        QMessageBox.information(
            self,
            "Consentimiento verificado",
            f"Se confirmó la verificación del consentimiento "
            f"informado físico del sujeto {codigo}."
        )
        

    def show_new_subject_dialog(self):
        codigo, aceptado = QInputDialog.getText(
            self,
            "Nuevo sujeto de prueba",
            "Introduce el identificador del sujeto:"
        )

        if not aceptado:
            return

        codigo = codigo.strip().upper()

        if not codigo:
            QMessageBox.warning(
                self,
                "Identificador vacío",
                "Debes introducir un identificador para el sujeto."
            )
            return

        try:
            participante_id = registrar_participante(codigo)

        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "Identificador duplicado",
                f"El sujeto {codigo} ya está registrado."
            )
            return

        QMessageBox.information(
            self,
            "Sujeto registrado",
            f"El sujeto {codigo} se registró correctamente.\n\n"
            f"ID interno: {participante_id}"
        )

    def create_experimental_subjects_page(self):
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(45, 35, 45, 35)
        layout.setSpacing(20)

        titulo = QLabel("Gestión de sujetos de prueba")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("""
            color: white;
            font-size: 30px;
            font-weight: bold;
        """)
        layout.addWidget(titulo)

        descripcion = QLabel(
            "Selecciona cómo deseas comenzar una prueba experimental."
        )
        descripcion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        descripcion.setWordWrap(True)
        descripcion.setStyleSheet("""
            color: #BFDBFE;
            font-size: 25px;
        """)
        layout.addWidget(descripcion)

        layout.addStretch()

        self.btn_new_subject = QPushButton(
            "＋  Nuevo sujeto de prueba"
        )

        self.btn_new_subject.setMinimumSize(350, 85)

        self.btn_new_subject.clicked.connect(
            self.show_new_subject_dialog
        )

        self.btn_registered_subject = QPushButton(
            "♙  Sujeto registrado"
        )
        self.btn_registered_subject.setMinimumSize(350, 85)

        self.btn_registered_subject.clicked.connect(
            self.show_registered_subject_dialog
        )
        
        estilo_botones = """
            QPushButton {
                background-color: #26364A;
                color: #BFDBFE;
                border: 2px solid #60A5FA;
                border-radius: 14px;
                font-size: 21px;
                font-weight: bold;
                padding: 15px;
            }

            QPushButton:hover {
                background-color: #334B66;
            }
        """

        self.btn_new_subject.setStyleSheet(estilo_botones)
        self.btn_registered_subject.setStyleSheet(estilo_botones)

        layout.addWidget(
            self.btn_new_subject,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        layout.addSpacing(15)

        layout.addWidget(
            self.btn_registered_subject,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.btn_registrar_sus = QPushButton(
            "★  Registrar satisfacción SUS"
        )
        self.btn_revisar_ensayos = QPushButton(
            "Gestión de gestos reales"
        )

        self.btn_revisar_ensayos.setMinimumHeight(45)

        self.btn_revisar_ensayos.setStyleSheet("""
            QPushButton {
                background-color: #394B63;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
            }

            QPushButton:hover {
                background-color: #526783;
            }
        """)
        self.btn_revisar_ensayos.clicked.connect(
            self.abrir_revision_ensayos
        )
        self.btn_registrar_sus.clicked.connect(
            self.mostrar_dialogo_registrar_sus
        )

        self.btn_registrar_sus.setMinimumSize(350, 85)
        self.btn_registrar_sus.setStyleSheet(estilo_botones)

        layout.addSpacing(15)

        layout.addWidget(
            self.btn_registrar_sus,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        layout.addWidget(
            self.btn_revisar_ensayos,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        layout.addStretch()

        return page

    def abrir_revision_ensayos(self):
        participantes = obtener_participantes()

        if not participantes:
            QMessageBox.information(
                self,
                "Sin sujetos registrados",
                "Todavía no hay sujetos de prueba registrados."
            )
            return
        
        opciones = [
            participante["codigo"]
            for participante in participantes
        ]

        codigo, aceptado = QInputDialog.getItem(
            self,
            "Gestión de gestos reales",
            "Selecciona el sujeto de prueba:",
            opciones,
            0,
            False
        )

        if not aceptado:
            return

        participante_seleccionado = next(
            participante
            for participante in participantes
            if participante["codigo"] == codigo
        )

        participante_id = participante_seleccionado["id"]
        sesiones = obtener_sesiones_participante(
            participante_id
        )

        if not sesiones:
            QMessageBox.information(
                self,
                "Sin sesiones experimentales",
                f"El sujeto {codigo} todavía no tiene sesiones registradas."
            )
            return
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Revisión de ensayos experimentales")
        dialogo.resize(750, 500)

        layout = QVBoxLayout(dialogo)

        titulo = QLabel("Confirmación de gestos en ensayos experimentales")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(titulo)
        etiqueta_sesion = QLabel("Selecciona la sesión experimental:")

        self.combo_sesion_revision = QComboBox()
        self.combo_sesion_revision.addItem(
            "— Selecciona una sesión —"
        )
        for sesion in sesiones:
            self.combo_sesion_revision.addItem(
                f"Sesión {sesion['numero_sesion']} — "
                f"Estado: {sesion['estado']}",
                sesion["id"]
            )
        layout.addWidget(etiqueta_sesion)
        layout.addWidget(self.combo_sesion_revision)
        btn_ver_ensayos = QPushButton(
            "Ver ensayos de la sesión"
        )

        btn_ver_ensayos.setMinimumHeight(45)

        layout.addWidget(btn_ver_ensayos)
        self.gestos_reales_temporales = {}
        self.sesion_revision_cargada_id = None
        self.tabla_revision_ensayos = QTableWidget()

        self.tabla_revision_ensayos.setColumnCount(4)

        self.tabla_revision_ensayos.setHorizontalHeaderLabels([
            "Ensayo",
            "Solicitado",
            "Detectado",
            "Gesto real"
        ])

        self.tabla_revision_ensayos.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.tabla_revision_ensayos.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.tabla_revision_ensayos.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        self.tabla_revision_ensayos.setStyleSheet("""
            QTableWidget {
                background-color: #172334;
                color: white;
                gridline-color: #394B63;
                border: 1px solid #526783;
                border-radius: 8px;
                selection-background-color: #2563EB;
                selection-color: white;
            }

            QTableWidget::item:selected {
                background-color: #2563EB;
                color: white;
                border-bottom: 3px solid #93C5FD;
            }
        """)

        layout.addWidget(self.tabla_revision_ensayos)
        
        self.combo_gesto_real_revision = QComboBox()

        self.combo_gesto_real_revision.addItems([
            "— Selecciona el gesto real —",
            "G1", "G2", "G3", "G4",
            "G5", "G6", "G7", "Ninguno"
        ])

        self.btn_guardar_revision_completa = QPushButton(
            "Guardar revisión completa (24 ensayos)"
        )

        self.btn_guardar_revision_completa.setMinimumHeight(45)

        self.btn_guardar_revision_completa.setEnabled(False)

        layout.addWidget(self.btn_guardar_revision_completa)

        def confirmar_revision_completa():
            sesion_seleccionada_id = (
                self.combo_sesion_revision.currentData()
            )

            if (
                self.sesion_revision_cargada_id is None
                or sesion_seleccionada_id
                != self.sesion_revision_cargada_id
            ):
                QMessageBox.warning(
                    dialogo,
                    "Sesión diferente",
                    "La sesión seleccionada no corresponde "
                    "a los ensayos mostrados.\n\n"
                    "Pulsa 'Ver ensayos de la sesión' "
                    "antes de guardar."
                )
                return

            gestos_validos = {
                "G1", "G2", "G3", "G4",
                "G5", "G6", "G7", "Ninguno"
            }

            if (
                len(self.gestos_reales_temporales) != 24
                or any(
                    gesto not in gestos_validos
                    for gesto in self.gestos_reales_temporales.values()
                )
            ):
                QMessageBox.warning(
                    dialogo,
                    "Revisión incompleta",
                    "Debes seleccionar un gesto real válido "
                    "para cada uno de los 24 ensayos."
                )
                return

            sesiones_actualizadas = obtener_sesiones_participante(
                participante_id
            )

            sesion_actual = next(
                (
                    sesion
                    for sesion in sesiones_actualizadas
                    if sesion["id"] == self.sesion_revision_cargada_id
                ),
                None
            )

            if sesion_actual is None:
                QMessageBox.warning(
                    dialogo,
                    "Sesión no encontrada",
                    "No se pudo verificar el estado de la sesión."
                )
                return
            if sesion_actual["estado"] != "completada":
                QMessageBox.warning(
                    dialogo,
                    "Sesión no completada",
                    "Esta sesión no está marcada como completada.\n\n"
                    "Solo se pueden guardar revisiones de gestos "
                    "reales correspondientes a sesiones completadas."
                )
                return

            respuesta = QMessageBox.question(
                dialogo,
                "Confirmar revisión experimental",
                "¿Confirmas que revisaste los 24 ensayos "
                "y que los gestos reales seleccionados "
                "corresponden a lo observado?\n\n"
                "Se guardará la revisión completa.",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if respuesta != QMessageBox.StandardButton.Yes:
                return

            try:
                guardar_revision_completa(
                    self.sesion_revision_cargada_id,
                    self.gestos_reales_temporales
                )
            except Exception as error:
                QMessageBox.critical(
                    dialogo,
                    "Error al guardar la revisión",
                    f"No se pudo guardar la revisión completa.\n\n"
                    f"Detalle: {error}"
                )
                return

            QMessageBox.information(
                dialogo,
                "Revisión guardada",
                "Los 24 gestos reales se guardaron "
                "correctamente en la base de datos.\n\n"
                "La revisión de esta sesión está completa."
            ) 
            self.btn_guardar_revision_completa.setEnabled(False)
            self.btn_guardar_revision_completa.clicked.connect(
                confirmar_revision_completa
            )

        def actualizar_estado_guardado():
            gestos_validos = {
                "G1", "G2", "G3", "G4",
                "G5", "G6", "G7", "Ninguno"
            }

            total_filas = self.tabla_revision_ensayos.rowCount()

            revision_completa = (
                total_filas == 24
                and all(
                    self.tabla_revision_ensayos.cellWidget(
                        fila, 3
                    ) is not None
                    and self.tabla_revision_ensayos.cellWidget(
                        fila, 3
                    ).currentText() in gestos_validos
                    for fila in range(total_filas)
                )
            )

            self.btn_guardar_revision_completa.setEnabled(
                revision_completa
            )

        self.tabla_revision_ensayos.itemSelectionChanged.connect(
            actualizar_estado_guardado
        )
        
        def mostrar_gesto_real_seleccionado():
            fila = self.tabla_revision_ensayos.currentRow()

            if fila < 0:
                return

            item = self.tabla_revision_ensayos.item(fila, 3)

            gesto_real = item.text() if item else ""

            indice = self.combo_gesto_real_revision.findText(
                gesto_real
            )

            self.combo_gesto_real_revision.setCurrentIndex(
                indice if indice >= 0 else 0
            )

        self.tabla_revision_ensayos.itemSelectionChanged.connect(
            mostrar_gesto_real_seleccionado
        )

        def ver_ensayos_seleccionados():
            sesion_id = self.combo_sesion_revision.currentData()

            if sesion_id is None:
                QMessageBox.warning(
                    dialogo,
                    "Sesión no seleccionada",
                    "Selecciona una sesión experimental."
                )
                return

            ensayos = obtener_ensayos_para_revision(sesion_id)
            self.sesion_revision_cargada_id = sesion_id
            self.btn_guardar_revision_completa.setEnabled(False)
            self.gestos_reales_temporales = {
                ensayo["id"]: ensayo["gesto_real"]
                for ensayo in ensayos
                if ensayo["gesto_real"] is not None
            }
            self.tabla_revision_ensayos.setRowCount(len(ensayos))

            for fila, ensayo in enumerate(ensayos):
                valores = [
                    ensayo["numero_iteracion"],
                    ensayo["gesto_solicitado"],
                    ensayo["gesto_detectado"],
                    ensayo["gesto_real"]
                ]

                for columna, valor in enumerate(valores):
                    item = QTableWidgetItem(
                        "" if valor is None else str(valor)
                    )

                    self.tabla_revision_ensayos.setItem(
                        fila,
                        columna,
                        item
                    )
                    combo_gesto = QComboBox()

                    combo_gesto.addItems([
                        "Seleccionar",
                        "G1", "G2", "G3", "G4",
                        "G5", "G6", "G7", "Ninguno"
                    ])

                    gesto_guardado = self.gestos_reales_temporales.get(
                        ensayo["id"]
                    )

                    if gesto_guardado:
                        indice = combo_gesto.findText(gesto_guardado)
                        if indice >= 0:
                            combo_gesto.setCurrentIndex(indice)

                    self.tabla_revision_ensayos.setCellWidget(
                        fila,
                        3,
                        combo_gesto
                    )
                    def guardar_seleccion_temporal(
                        indice,
                        ensayo_id=ensayo["id"],
                        combo=combo_gesto
                    ):
                        if indice == 0:
                            self.gestos_reales_temporales.pop(
                                ensayo_id, None
                            )
                        else:
                            self.gestos_reales_temporales[ensayo_id] = (
                                combo.currentText()
                            )

                    combo_gesto.currentIndexChanged.connect(
                        guardar_seleccion_temporal
                    )
                    combo_gesto.currentIndexChanged.connect(
                        lambda indice: actualizar_estado_guardado()
                )
            actualizar_estado_guardado()

            QMessageBox.information(
                dialogo,
                "Ensayos experimentales",
                f"Sesión ID: {sesion_id}\n"
                f"Ensayos encontrados: {len(ensayos)}"
            )
        btn_ver_ensayos.clicked.connect(
            ver_ensayos_seleccionados
        )
        dialogo.exec()
    
    def mostrar_ensayo_experimental(self):
        if (
            not self.experimental_sequence
            or not 0 <= self.experimental_trial_index < len(
                self.experimental_sequence
            )
        ):
            return
        ensayo = self.obtener_ensayo_actual_experimental()

        self.experimental_progress.setText(
            f"Ensayo {ensayo['numero_iteracion']} "
            f"de {len(self.experimental_sequence)}"
        )

        self.experimental_instruction.setText(
            obtener_instruccion_experimental(
                ensayo["gesto_solicitado"]
            )
        )    

    def confirmar_salida_experimental(self):
        respuesta = QMessageBox.question(
            self,
            "Salir del experimento",
            "¿Deseas salir del modo experimental?\n"
            "La sesión actual dejará de estar activa.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            self.salir_modo_experimental()

    def salir_modo_experimental(self):
        # Detener temporizadores pendientes
        self.experimental_neutral_timer.stop()
        self.experimental_transition_timer.stop()
        # Registrar una salida anticipada sin sobreescribir sesión ya completada
        if (
            self.experimental_session_id is not None
            and self.experimental_session_started
            and not (
                self.experimental_trial_completed
                and self.experimental_trial_index
                == len(self.experimental_sequence) - 1
            )
        ):
            actualizar_estado_sesion(
                self.experimental_session_id,
                "interrumpida"
            )

            print(
                "Sesión guardada como interrumpida en SQLite:",
                self.experimental_session_id
            )

        # Restablecer el estado experimental
        self.experimental_session_id = None
        self.experimental_participant_id = None
        self.experimental_sequence = []
        self.experimental_trial_index = 0
        self.experimental_ready_confirmed = False
        self.experimental_trial_completed = False
        self.experimental_session_started = False
        self.experimental_start_time = None
        self.experimental_response_time = None
        self.experimental_active_trial_id = None
        self.experimental_detected_gesture = None
        self.experimental_detection_time = None

        # Ocultar la interfaz experimental
        self.experimental_panel.hide()
        self.experimental_camera_sidebar.hide()

        # Regresar al inicio de VEXA
        self.pages.setCurrentIndex(0)

        print("Modo experimental cerrado. Regreso al inicio.")

    def puede_avanzar_ensayo_experimental(self):
        return (
            self.experimental_session_id is not None
            and bool(self.experimental_sequence)
            and self.experimental_trial_completed
            and self.experimental_start_time is None
            and (
                self.experimental_response_time is not None
                or (
                    self.experimental_detected_gesture == "__SIMULADO__"
                )
            )
        )

    def probar_avance_experimental(self):
        print("DEBUG: F9 ACTIVADO", flush=True)

        if self.experimental_session_id is None:
            return

        if not self.experimental_ready_confirmed:
            return

        if self.experimental_trial_completed:
            return

        if self.es_ensayo_neutral_experimental():
            return

        # Simulación de finalización, no registra un gesto detectado
        self.experimental_trial_completed = True
        self.experimental_start_time = None

        
        self.experimental_detected_gesture = "__SIMULADO__"
        self.experimental_response_time = None
        # Identificar en SQLite la sesión utilizada para pruebas con F9
        marcar_sesion_depuracion(
            self.experimental_session_id
        )

        print(
            "Sesión marcada como depuración F9:",
            self.experimental_session_id
        )

        self.experimental_panel_title.setText(
            "🧪 Ensayo simulado — sin datos de detección"
        )

        self.experimental_transition_timer.start(2000)

    def avanzar_ensayo_experimental(self):
        if not self.puede_avanzar_ensayo_experimental():
            return

        siguiente_indice = self.experimental_trial_index + 1

        print(
            "DIAGNÓSTICO AVANCE:",
            "índice actual =", self.experimental_trial_index,
            "| siguiente índice =", siguiente_indice,
            "| total ensayos =", len(self.experimental_sequence),
            "| sesión =", self.experimental_session_id
        )

        if siguiente_indice >= len(self.experimental_sequence):
            self.experimental_panel_title.setText(
                "🎉 Sesión experimental completada — "
                f"{len(self.experimental_sequence)} de "
                f"{len(self.experimental_sequence)} ensayos"
            )

            actualizar_estado_sesion(
                self.experimental_session_id,
                "completada"
            )

            print(
                "Sesión guardada como completada en SQLite:",
                self.experimental_session_id
            )

            self.experimental_ready.setText(
                "Todos los ensayos han finalizado."
            )

            self.experimental_ready_confirmed = False
            self.experimental_start_time = None
            self.experimental_active_trial_id = None

            # Impedir que Espacio reinicie el último ensayo
            self.experimental_trial_completed = True

            print("Sesión experimental completada.")

            QMessageBox.information(
                self,
                "Prueba finalizada",
                "🎉 ¡Has llegado al final de la prueba!\n\n"
                "Muchas gracias por tu participación.\n\n"
                "Presiona Aceptar para finalizar."
            )
            self.salir_modo_experimental()
            return

        self.experimental_trial_index = siguiente_indice

        self.experimental_ready_confirmed = False
        self.experimental_start_time = None
        self.experimental_response_time = None
        self.experimental_trial_completed = False
        self.experimental_active_trial_id = None
        self.experimental_detected_gesture = None
        self.experimental_detection_time = None

        self.experimental_ready.setText(
            "Presiona ESPACIO cuando estés listo"
        )

        self.mostrar_ensayo_experimental()
        # Indicar que el nuevo ensayo aún no ha comenzado
        self.experimental_panel_title.setText(
            f"⏳ Ensayo {self.experimental_trial_index + 1} "
            f"de {len(self.experimental_sequence)} — "
            "Presiona Espacio"
        )        
        # Actualizar la instrucción visible del nuevo ensayo
        if self.experimental_trial_index < len(self.experimental_sequence):

            ensayo_actual = self.experimental_sequence[
                self.experimental_trial_index
            ]

            instruccion = obtener_instruccion_experimental(
                ensayo_actual["gesto_solicitado"]
            )

            self.categories_description.setText(instruccion)
            self.phrases_description.setText(instruccion)
            self.experimental_panel_instruction.setText(instruccion)

    def volver_a_sujetos_experimentales(self):
        self.experimental_transition_timer.stop()
        
        if self.experimental_start_time is not None:
            self.experimental_neutral_timer.stop()
            self.experimental_start_time = None
            self.experimental_response_time = None
            self.experimental_ready_confirmed = False
            self.experimental_trial_completed = False
            self.experimental_active_trial_id = None
            self.experimental_detected_gesture = None
            self.experimental_detection_time = None
            self.experimental_ready.setText(
                "Medición interrumpida. Presiona ESPACIO "
                "para comenzar nuevamente."
            )
            respuesta = QMessageBox.question(
                self,
                "Abandonar medición",
                "La medición actual será interrumpida.\n\n"
                "Si eliges No, permanecerás en este ensayo "
                "y podrás iniciar una nueva medición "
                "presionando ESPACIO.\n\n"
                "¿Deseas volver a sujetos?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if respuesta != QMessageBox.StandardButton.Yes:
                return

        self.experimental_ready_confirmed = False
        self.experimental_start_time = None
        self.experimental_response_time = None
        self.pages.setCurrentIndex(13)
    
    def registrar_gesto_detectado_experimental(self, gesto):
        if not self.hay_medicion_experimental_activa():
            return
        ensayo = self.obtener_ensayo_actual_experimental()

        if ensayo is None or ensayo["id"] != self.experimental_active_trial_id:
            return
        if self.experimental_detected_gesture is not None:
            return
        if gesto not in {
            "G1", "G2", "G3", "G4", "G5", "G6", "G7"
        }:
            return

        instante_deteccion = time.perf_counter()

        if instante_deteccion < self.experimental_start_time:
            return

        self.experimental_detected_gesture = gesto
        self.experimental_detection_time = instante_deteccion
        guardar_gesto_detectado(
            self.experimental_active_trial_id,
            gesto
        )
        if self.es_ensayo_neutral_experimental():
            return

        self.experimental_response_time = (
            self.experimental_detection_time
            - self.experimental_start_time
        )
        guardar_tiempo_deteccion_experimental(
            self.experimental_active_trial_id,
            self.experimental_response_time
        )

        self.experimental_trial_completed = True
        self.experimental_start_time = None
        self.experimental_panel_title.setText(
            "✅ Ensayo completado"
        )

        self.experimental_ready.setText(
            f"Gesto registrado: {gesto}. "
            "Preparando siguiente ensayo..."
        )

        self.experimental_transition_timer.start(2000)

    def hay_medicion_experimental_activa(self):
        return (
            self.experimental_start_time is not None
            and self.experimental_active_trial_id is not None
            and not self.experimental_trial_completed
        )

    def obtener_ensayo_actual_experimental(self):
        if (
            not self.experimental_sequence
            or not 0 <= self.experimental_trial_index < len(
                self.experimental_sequence
            )
        ):
            return None

        return self.experimental_sequence[
            self.experimental_trial_index
        ]

    def resultado_neutral_experimental(self):
        hubo_gesto = self.hubo_gesto_en_ensayo_neutral()

        if hubo_gesto is None:
            return None

        return not hubo_gesto
    
    def hubo_gesto_en_ensayo_neutral(self):
        if not self.es_ensayo_neutral_experimental():
            return None

        if not self.experimental_trial_completed:
            return None
        if self.experimental_response_time is None:
            return None
        ensayo = self.obtener_ensayo_actual_experimental()

        if ensayo is None or ensayo["id"] != self.experimental_active_trial_id:
            return None

        return self.experimental_detected_gesture is not None

    def comprobar_fin_intervalo_neutral(self):
        print("Aviso del temporizador neutral recibido")
        print(
            "Tiempo al recibir aviso:",
            self.obtener_tiempo_experimental()
        )
        tiempo = self.obtener_tiempo_experimental()

        if (
            tiempo is not None
            and self.hay_medicion_experimental_activa()
            and self.es_ensayo_neutral_experimental()
            and tiempo < self.experimental_neutral_duration
        ):
            restante = self.experimental_neutral_duration - tiempo
            self.experimental_neutral_timer.start(
                max(1, int(restante * 1000) + 1)
            )
            return
        if self.intervalo_neutral_completado():
            print("Intervalo neutral completado")
            self.finalizar_medicion_experimental()

            if self.experimental_response_time is None:
                return
            guardar_tiempo_deteccion_experimental(
                self.experimental_active_trial_id,
                self.experimental_response_time
            )
            print(
                "Duración real del ensayo neutral:",
                round(self.experimental_response_time, 3),
                "segundos"
            )

            self.experimental_trial_completed = True
            self.experimental_panel_title.setText(
                "✅ Ensayo completado"
            )
            print(
                "Comprobación técnica neutral (NO validada):",
                self.resultado_neutral_experimental()
            )          
            self.experimental_ready.setText(
                f"Ensayo completado en "
                f"{self.experimental_response_time:.3f} segundos. "
                "Listo para avanzar al siguiente ensayo."
            )

            self.experimental_transition_timer.start(2000)
    
    def intervalo_neutral_completado(self):
        if not self.hay_medicion_experimental_activa():
            return False

        if not self.es_ensayo_neutral_experimental():
            return False
        
        ensayo = self.obtener_ensayo_actual_experimental()

        if ensayo is None or ensayo["id"] != self.experimental_active_trial_id:
            return False

        tiempo = self.obtener_tiempo_experimental()

        if tiempo is None:
            return False

        return tiempo >= self.experimental_neutral_duration

    def es_ensayo_neutral_experimental(self):
        ensayo = self.obtener_ensayo_actual_experimental()

        if ensayo is None:
            return False

        return ensayo["gesto_solicitado"] == "ninguno"

    def gesto_experimental_es_correcto(self):
        if not self.hay_medicion_experimental_activa():
            return None

        if self.es_ensayo_neutral_experimental():
            return None
        ensayo = self.obtener_ensayo_actual_experimental()

        if ensayo is None:
            return None
        if self.experimental_active_trial_id != ensayo["id"]:
            return None

        if self.experimental_detected_gesture is None:
            return None
        if self.experimental_detection_time is None:
            return None
        if self.calcular_tiempo_deteccion_experimental() is None:
            return None

        return (
            self.experimental_detected_gesture
            == ensayo["gesto_solicitado"]
        )

    def calcular_tiempo_deteccion_experimental(self):
        if (
            self.experimental_start_time is None
            or self.experimental_detection_time is None
        ):
            return None

        tiempo = (
            self.experimental_detection_time
            - self.experimental_start_time
        )

        if tiempo < 0:
            return None

        return tiempo

    def obtener_tiempo_experimental(self):
        if self.experimental_start_time is None:
            return None

        return time.perf_counter() - self.experimental_start_time

    def finalizar_medicion_experimental(self):
        if not self.hay_medicion_experimental_activa():
            return None
        if self.experimental_trial_completed:
            return None
    
        ensayo = self.obtener_ensayo_actual_experimental()

        if (
            ensayo is None
            or self.experimental_active_trial_id != ensayo["id"]
        ):
            return None

        self.experimental_response_time = (
            self.obtener_tiempo_experimental()
        )
        self.experimental_neutral_timer.stop()
        self.experimental_start_time = None

        return self.experimental_response_time

    def participante_listo_experimental(self):
        if self.experimental_transition_timer.isActive():
            return
        if (
            self.experimental_session_id is None
            or not self.experimental_sequence
            or not 0 <= self.experimental_trial_index < len(
                self.experimental_sequence
            )
        ):
            return              

        if self.experimental_ready_confirmed:
            return
        if self.experimental_trial_completed:
            return

        self.experimental_ready_confirmed = True
        self.experimental_response_time = None
        self.experimental_trial_completed = False
        self.experimental_detected_gesture = None
        self.experimental_detection_time = None
        self.experimental_start_time = time.perf_counter()
        self.experimental_session_started = True

        ensayo = self.obtener_ensayo_actual_experimental()
        self.experimental_active_trial_id = ensayo["id"]
        if self.es_ensayo_neutral_experimental():
            self.experimental_neutral_timer.start(
                int(self.experimental_neutral_duration * 1000)
            )
            print(
                "Temporizador neutral activo:",
                self.experimental_neutral_timer.isActive()
            )

        # Mostrar el estado de medición para cualquier gesto
        self.experimental_panel_title.setText(
            "🔴 Medición en curso..."
        )
        self.experimental_ready.setText(
            "Medición iniciada. Realiza el gesto solicitado."
        )

        print(
            "Medición iniciada para el ensayo:",
            ensayo["numero_iteracion"]
        )

    def iniciar_ensayo_con_espacio(self):

        if (
            self.experimental_session_id is not None
            and self.pages.currentIndex() in (1, 6)
            and not self.experimental_camera_sidebar.isHidden()
        ):
            self.participante_listo_experimental()

    def keyPressEvent(self, event):
        pagina_actual = self.pages.currentIndex()

        en_pagina_experimental = pagina_actual == 12

        en_navegacion_experimental = (
            pagina_actual in (1, 6)
            and self.experimental_panel.isVisible()
            and self.experimental_session_id is not None
        )

        if (
            event.key() == Qt.Key.Key_Space
            and not event.isAutoRepeat()
            and (
                en_pagina_experimental
                or en_navegacion_experimental
            )
        ):
            self.participante_listo_experimental()
            event.accept()
            return

        super().keyPressEvent(event)   
    
    def create_experimental_page(self):
        page = QWidget()
        page.setObjectName("experimentalPage")

        page.setStyleSheet("""
            QWidget#experimentalPage {
                background-color: #242F40;
            }
        """)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Título
        titulo = QLabel("Prueba experimental")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("""
            color: white;
            font-size: 30px;
            font-weight: bold;
        """)
        layout.addWidget(titulo)

        # Número de ensayo
        self.experimental_progress = QLabel("Ensayo 1 de 24")
        self.experimental_progress.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.experimental_progress.setStyleSheet("""
            color: #BFDBFE;
            font-size: 19px;
        """)
        layout.addWidget(self.experimental_progress)

        layout.addStretch()

        # Instrucción principal
        self.experimental_instruction = QLabel(
            "Realiza el gesto G1."
        )
        self.experimental_instruction.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.experimental_instruction.setWordWrap(True)
        self.experimental_instruction.setStyleSheet("""
            color: white;
            font-size: 34px;
            font-weight: bold;
        """)
        layout.addWidget(self.experimental_instruction)

        # Mensaje de preparación
        self.experimental_ready = QLabel(
            "Presiona ESPACIO cuando estés listo"
        )
        self.experimental_ready.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.experimental_ready.setStyleSheet("""
            color: #BFDBFE;
            background-color: #26364A;
            border: 1px solid #60A5FA;
            border-radius: 10px;
            font-size: 21px;
            font-weight: bold;
            padding: 18px;
        """)

        layout.addWidget(self.experimental_ready)
        layout.addStretch()

        boton_volver = QPushButton("← Volver a sujetos")
        boton_volver.setFocusPolicy(Qt.FocusPolicy.NoFocus)        
        boton_volver.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                font-size: 17px;
                padding: 12px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)

        boton_volver.clicked.connect(
            self.volver_a_sujetos_experimentales
        )

        layout.addWidget(boton_volver)

        return page

    def create_categories_page(self):

        page = QWidget()

        page.setObjectName("categoriesPage")

        page.setStyleSheet("""
            QWidget#categoriesPage {
                background-color: #242F40;
            }
        """)

        layout = QVBoxLayout(page)

        # Título de la pantalla

        title = QLabel("Selecciona una categoría")
        title.setStyleSheet(
            "font-size: 28px;"
            "font-weight: bold;"
        )

        layout.addWidget(title)

        # Descripción

        self.categories_description = QLabel(
            "Selecciona una categoría para consultar sus frases."
        )

        self.categories_description.setWordWrap(True)

        self.categories_description.setStyleSheet(
            "font-size: 15px;"
        )   

        title.setStyleSheet(
            title.styleSheet() + "background: transparent; border: none;"
        )

        self.categories_description.setStyleSheet(
            self.categories_description.styleSheet()
            + "background: transparent; border: none;"
        )
        
        layout.addWidget(self.categories_description)
        layout.addSpacing(20)

        # Distribución de las categorías en una cuadrícula

        grid = QGridLayout()
        grid.setVerticalSpacing(24)

        categorias = self.get_vexa_categories()
        # Guardar las ocho tarjetas de categorías
        self.category_buttons = []

        for numero in range(1, 9):

            nombre_categoria = categorias[numero]["nombre"]

            # Identificar el gesto y las repeticiones
            numero_gesto = ((numero - 1) % 4) + 1
            repeticiones = 1 if numero <= 4 else 2

            # Mostrar el nombre sin ×2 debajo de la fotografía
            texto_boton = f"\n{nombre_categoria}\n"            

            # Buscar la fotografía del gesto
            ruta_imagen = (
                Path(__file__).resolve().parent
                / "imagenes_gestos"
                / f"G{numero_gesto}.png"
            )

            # Crear botón con fotografía arriba y texto debajo
            boton = GestureButton(texto_boton, ruta_imagen)

            # Mostrar gesto y repeticiones en la franja superior
            if repeticiones == 2:
                boton.identificador.setText(f"G{numero_gesto}   ×2")
            else:
                boton.identificador.setText(f"G{numero_gesto}")

            boton.identificador.show()

            boton.clicked.connect(
                lambda checked=False, n=numero: self.open_category(n)
            )
            
            fila = (numero - 1) // 4
            columna = (numero - 1) % 4

            grid.addWidget(boton, fila, columna)
            self.category_buttons.append(boton)
        layout.addStretch(1)
        layout.addLayout(grid)
        layout.addStretch(2)

        return page
    
    def finalizar_destello_categoria(self, numero):
        """Apaga el borde verde y abre la pantalla de frases."""

        self.category_buttons[numero - 1].resaltar(False)
        self.pages.setCurrentIndex(6)

        # Permitir nuevas selecciones después de la transición
        self.transicion_categoria_activa = False
    
    def open_category(self, numero):
        # Ignorar nuevas selecciones durante el destello
        if self.transicion_categoria_activa:
            return

        categorias = self.get_vexa_categories()

        if numero not in categorias:
            return

        # Bloquear selecciones adicionales temporalmente
        self.transicion_categoria_activa = True

        self.current_category = numero
        nombre_categoria = categorias[numero]["nombre"]
        frases = categorias[numero]["frases"]

        # Mostrar el nombre real de la categoría
        self.phrases_title.setText(
            f"{nombre_categoria} — Frases"
        )

        # Limpiar el mensaje seleccionado anteriormente
        self.phrase_text.setText(
            "Selecciona una frase para comunicarte."
        )

        # Actualizar los cinco botones
        for indice, boton in enumerate(self.phrase_buttons):

            if indice < len(frases):
                boton.etiqueta.setText(frases[indice])
                boton.setVisible(True)
            else:
                boton.setVisible(False)

        # Apariencia normal de la descripción de frases
        self.phrases_description.setText(
            "Selecciona una frase para comunicarte."
        )

        self.phrases_description.setAlignment(
            Qt.AlignmentFlag.AlignLeft
        )

        self.phrases_description.setMinimumHeight(0)

        self.phrases_description.setStyleSheet("""
            font-size: 15px;
            background: transparent;
            border: none;
        """)

        # Preparar la instrucción en la pantalla de frases
        if self.experimental_session_id is not None:

            self.phrases_description.setText(
                self.categories_description.text()
            )

            self.phrases_description.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self.phrases_description.setStyleSheet("""
                QLabel {
                    font-size: 26px;
                    font-weight: bold;
                    color: #FFFFFF;
                    background-color: #172334;
                    border: 2px solid #4B88A2;
                    border-radius: 14px;
                    padding: 20px;
                }
            """)

        # Iluminar brevemente la categoría seleccionada
        for tarjeta in self.category_buttons:
            tarjeta.resaltar(False)

        self.category_buttons[numero - 1].resaltar(True)

        # Esperar 180 ms y después abrir las frases
        QTimer.singleShot(
            180,
            lambda n=numero: self.finalizar_destello_categoria(n)
        )
        
    
    def create_profile_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("¿Quién va a usar VEXA?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
        """)

        description = QLabel(
            "Selecciona un perfil para continuar."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("font-size: 17px;")

        # Barra para seleccionar el perfil
        self.profile_selector = QComboBox()
        self.profile_selector.setMinimumSize(320, 55)

        # Tarjeta grande con el perfil seleccionado
        self.selected_profile_card = QLabel("Sin perfiles")
        self.selected_profile_card.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.selected_profile_card.setMinimumSize(360, 170)
        self.selected_profile_card.setStyleSheet("""
            QLabel {
                background-color: #202938;
                border: 2px solid #4F46E5;
                border-radius: 18px;
                padding: 20px;
                font-size: 30px;
                font-weight: bold;
                color: #FFFFFF;
            }
        """)

        # Conectar los cambios del selector
        self.profile_selector.currentTextChanged.connect(
            self.update_selected_profile_card
        )

        # Cargar los perfiles y mostrar el último seleccionado
        self.refresh_profiles()

        create_button = QPushButton("+ Crear nuevo perfil")
        create_button.setMinimumSize(240, 55)
        #create_button.clicked.connect()
        create_button.clicked.connect(self.create_new_profile)

        continue_button = QPushButton("Continuar")
        continue_button.setMinimumSize(240, 60)
        continue_button.clicked.connect(
            self.continue_with_profile
        )

        back_button = QPushButton("Volver")
        back_button.clicked.connect(
            self.return_from_profile_page
        )

        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(description)
        layout.addSpacing(20)

        layout.addWidget(
            self.selected_profile_card,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        layout.addSpacing(20)
        layout.addWidget(
            self.profile_selector,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        layout.addSpacing(15)
        layout.addWidget(
            create_button,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        layout.addWidget(
            continue_button,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        layout.addWidget(
            back_button,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        layout.addStretch()

        return page

    def update_selected_profile_card(self, profile_name):
        if profile_name:
            self.selected_profile_card.setText(
                f"PERFIL SELECCIONADO\n\n{profile_name}"
            )
        else:
            self.selected_profile_card.setText(
                "Todavía no hay perfiles\n\n"
                "Crea uno para comenzar"
            )


    def refresh_profiles(self):
        self.profile_selector.blockSignals(True)
        self.profile_selector.clear()

        self.profiles = self.settings_store.value(
            "profiles", [], type=list
        )

        # Mostrar los perfiles normales
        visible_profiles = [
            profile
            for profile in self.profiles
            if profile != "Perfil experimental"
        ]

        # Mostrar el perfil experimental solo si está activado
        if self.experimental_mode_enabled:
            if "Perfil experimental" in self.profiles:
                visible_profiles.append("Perfil experimental")

        if visible_profiles:
            self.profile_selector.addItems(visible_profiles)

            # Recuperar la selección anterior si sigue visible
            index = self.profile_selector.findText(
                self.current_profile
            )

            if index >= 0:
                self.profile_selector.setCurrentIndex(index)
            else:
                self.profile_selector.setCurrentIndex(0)

        self.profile_selector.blockSignals(False)

        # Actualizar la tarjeta visual
        self.update_selected_profile_card(
            self.profile_selector.currentText()
        )

    def create_new_profile(self):
        normal_profiles = [
            profile
            for profile in self.profiles
            if profile != "Perfil experimental"
        ]

        if len(normal_profiles) >= 3:
            QMessageBox.information(
                self,
                "Límite de perfiles",
                "VEXA permite un máximo de 3 perfiles de usuario.\n\n"
                "Para agregar un nuevo perfil, favor de " 
                "eliminar alguno de los perfiles existentes."
            )
            return
        name, accepted = QInputDialog.getText(
            self,
            "Crear perfil",
            "Escribe el nombre del nuevo perfil:"
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            QMessageBox.warning(
                self,
                "Nombre no válido",
                "Escribe un nombre para el perfil."
            )
            return
        
        # Reservar el nombre del perfil experimental
        if name.casefold() == "perfil experimental":
            QMessageBox.warning(
                self,
                "Nombre reservado",
                "El nombre 'Perfil experimental'\n"
                "está reservado para las\n"
                "evaluaciones de VEXA."
            )
            return

        existing_names = [
            profile.casefold()
            for profile in self.profiles
        ]

        if name.casefold() in existing_names:
            QMessageBox.warning(
                self,
                "Perfil duplicado",
                "Ya existe un perfil con ese nombre. "
                "Elige otro nombre."
            )
            return

        self.profiles.append(name)

        self.settings_store.setValue(
            "profiles", self.profiles
        )

        self.current_profile = name
        self.settings_store.setValue(
            "last_profile", name
        )
        # Un perfil nuevo comienza sin voz seleccionada
        self.voz_seleccionada = None

        self.btn_female_voice.setChecked(False)
        self.btn_male_voice.setChecked(False)

        self.refresh_profiles()


    def continue_with_profile(self):
        selected_profile = self.profile_selector.currentText()
        if (
            selected_profile == "Perfil experimental"
            and not self.experimental_mode_enabled
        ):
            QMessageBox.warning(
                self,
                "Modo experimental desactivado",
                "El administrador debe activar el modo "
                "experimental antes de utilizar este perfil."
            )
            return

        if not selected_profile:
            QMessageBox.information(
                self,
                "Crea tu primer perfil",
                "Antes de continuar, debes crear un perfil."
            )
            return

        self.save_profile(selected_profile)

        # Recuperar la voz propia del perfil seleccionado
        self.voz_seleccionada = self.settings_store.value(
            f"voz_perfil/{selected_profile}",
            None
        )

        # Actualizar las tarjetas de selección de voz
        self.btn_female_voice.setChecked(
            self.voz_seleccionada == "Femenina"
        )

        self.btn_male_voice.setChecked(
            self.voz_seleccionada == "Masculina"
        )

        self.route_after_policies()


    def create_policies_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 20, 35, 20)
        layout.setSpacing(12)

        title = QLabel("Condiciones de uso y privacidad")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            color: white;
            padding: 10px;
        """)

        description = QLabel(
            "Conoce cómo VEXA utiliza la cámara, los sensores "
            "EMG y los datos de calibración de tu perfil."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("""
            color: #D1D5DB;
            font-size: 17px;
            padding: 5px;
        """)

        layout.addWidget(title)
        layout.addWidget(description)

        # Contenedor desplazable para los módulos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        container = QWidget()
        modules_layout = QVBoxLayout(container)
        modules_layout.setSpacing(10)

        sections = [
            (
                "1. Finalidad de VEXA",
                "VEXA es una herramienta de apoyo a la "
                "comunicación que permite seleccionar y expresar "
                "frases mediante gestos faciales y musculares.\n\n"
                "No sustituye la atención médica ni constituye "
                "un sistema de diagnóstico."
            ),
            (
                "2. Acceso a la cámara",
                "VEXA necesita acceder a la cámara para detectar "
                "movimientos faciales en tiempo real mediante "
                "MediaPipe.\n\n"
                "Durante el uso habitual no se guardarán "
                "fotografías ni videos. Sin embargo, podrán "
                "conservarse parámetros numéricos de calibración "
                "facial asociados al perfil."
            ),
            (
                "3. Uso de sensores EMG",
                "Para reconocer la actividad muscular es necesario "
                "conectar sensores de electromiografía superficial "
                "(EMG) compatibles con VEXA.\n\n"
                "Los sensores deben colocarse siguiendo las "
                "instrucciones correspondientes. Si aparece "
                "irritación o incomodidad, se debe detener su uso."
            ),
            (
                "4. Calibración de gestos",
                "VEXA utiliza una calibración inicial para adaptar "
                "el reconocimiento facial y muscular al usuario.\n\n"
                "Los parámetros de calibración de MediaPipe y EMG "
                "se guardarán localmente y se asociarán al perfil "
                "seleccionado para evitar repetir el proceso "
                "en cada sesión.\n\n"
                "La calibración podrá repetirse si cambian las "
                "condiciones de uso o el reconocimiento deja "
                "de funcionar correctamente."
            ),
            (
                "5. Privacidad de la información",
                "Los datos obtenidos durante el uso habitual "
                "de VEXA no se utilizarán con fines experimentales, "
                "investigaciones ni publicaciones científicas.\n\n"
                "La información de calibración y las preferencias "
                "del usuario se utilizarán para el funcionamiento "
                "de la aplicación y se conservarán localmente."
            ),
            (
                "6. Conservación y eliminación",
                "Los datos de configuración y calibración se "
                "conservarán mientras el perfil permanezca "
                "registrado en VEXA.\n\n"
                "El usuario podrá solicitar la eliminación de "
                "su perfil y de los datos asociados. Esta "
                "funcionalidad deberá estar disponible en "
                "la versión de VEXA que se distribuya."
            ),
            (
                "7. Limitaciones y seguridad",
                "El reconocimiento de gestos puede presentar "
                "errores o retrasos por cambios en la iluminación, "
                "la posición de los sensores u otras condiciones.\n\n"
                "Se recomienda verificar las frases seleccionadas. "
                "VEXA no debe ser el único medio para comunicar "
                "una emergencia o solicitar ayuda inmediata."
            ),
        ]

        # Crear todos los módulos desplegables
        for heading, content in sections:
            button = QPushButton("▸ " + heading)
            button.setCheckable(True)
            button.setMinimumHeight(55)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #202938;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    text-align: left;
                    padding: 12px;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #374151;
                }
            """)

            detail = QLabel(content)
            detail.setWordWrap(True)
            detail.setStyleSheet("""
                color: #E5E7EB;
                background-color: #172334;
                font-size: 16px;
                padding: 18px;
                border-radius: 10px;
            """)
            detail.hide()

            def toggle(expanded, label=detail,
                       header=button, text=heading):
                label.setVisible(expanded)
                header.setText(
                    ("▾ " if expanded else "▸ ") + text
                )

            button.toggled.connect(toggle)

            modules_layout.addWidget(button)
            modules_layout.addWidget(detail)

        modules_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # Aceptación obligatoria
        self.policies_checkbox = QCheckBox(
            "He leído y acepto las condiciones de uso "
            "y privacidad de VEXA."
        )
        
        self.policies_checkbox.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                background-color: #354765;
                border: 2px solid #7184A5;
                border-radius: 12px;
                font-size: 17px;
                font-weight: bold;
                spacing: 14px;
                padding: 18px;
            }

            QCheckBox::indicator {
                width: 28px;
                height: 28px;
                background-color: #FFFFFF;
                border: 2px solid #A5B4FC;
                border-radius: 6px;
            }

            QCheckBox::indicator:checked {
                background-color: #818CF8;
                border: 2px solid #C7D2FE;
                image: url(:/qt-project.org/styles/commonstyle/images/checkbox_checked.png);
            }

            QCheckBox:hover {
                background-color: #405779;
                border: 2px solid #A5B4FC;
            }
        """)


        layout.addWidget(self.policies_checkbox)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        reject_button = QPushButton("No acepto")
        reject_button.setMinimumHeight(55)
        reject_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )

        accept_button = QPushButton("Acepto y continuar")
        accept_button.setMinimumHeight(55)
        accept_button.setEnabled(False)
        accept_button.clicked.connect(
            self.accept_policies
        )

        self.policies_checkbox.toggled.connect(
            accept_button.setEnabled
        )

        buttons_layout.addWidget(reject_button)
        buttons_layout.addWidget(accept_button)

        layout.addLayout(buttons_layout)

        return page

    def accept_policies(self):
        if not self.policies_checkbox.isChecked():
            return

        self.update_profile_progress(
            policies_accepted=True
        )

        self.policies_checkbox.setChecked(False)
        self.route_after_policies()

    def create_setup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addStretch()

        title = QLabel("Preparación de VEXA")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            padding: 15px;
        """)

        self.setup_step_label = QLabel("")
        self.setup_step_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.setup_step_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            padding: 15px;
        """)

        self.setup_step_description = QLabel("")
        self.setup_step_description.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.setup_step_description.setWordWrap(True)
        self.setup_step_description.setStyleSheet("""
            font-size: 17px;
            padding: 15px;
        """)

        self.setup_next_button = QPushButton(
            "Completar paso"
        )
        self.setup_next_button.setMinimumSize(260, 60)
        self.setup_next_button.clicked.connect(
            self.complete_setup_step
        )

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(self.setup_step_label)
        layout.addWidget(self.setup_step_description)
        layout.addSpacing(20)

        layout.addWidget(
            self.setup_next_button,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        layout.addStretch()

        return page

    def update_setup_page(self):
        progress = self.get_profile_progress()
        step = progress["setup_step"]

        steps = [
            (
                "Paso 1 de 3: Tutorial de uso",
                "Aquí aprenderás cómo utilizar las funciones "
                "principales de VEXA."
            ),
            (
                "Paso 2 de 3: Calibración",
                "Aquí prepararemos el sistema para reconocer "
                "las señales necesarias."
            ),
            (
                "Paso 3 de 3: Selección de voz",
                "Aquí podrás configurar la voz que utilizará "
                "VEXA para comunicar tus mensajes."
            ),
        ]

        if step >= len(steps):
            return

        title, description = steps[step]

        self.setup_step_label.setText(title)
        self.setup_step_description.setText(description)
        self.setup_next_button.setText(
            "Completar paso" if step < 2
            else "Finalizar preparación"
        )

    def complete_setup_step(self):
        progress = self.get_profile_progress()
        step = progress["setup_step"]

        if step >= 3:
            self.route_after_policies()
            return
        
        if step == 1:
            self.abrir_calibracion_perfil()
            return

        next_step = step + 1

        self.update_profile_progress(
            setup_step=next_step
        )

        if next_step == 1:
            # Tutorial terminado: iniciar la etapa de calibración.
            self.abrir_calibracion_perfil()

        elif next_step == 2:
            # Selección de voz.
            self.abrir_seleccion_voz()

        elif next_step >= 3:

            QMessageBox.information(
                self,
                "Preparación completada",
                "La preparación de este perfil ha terminado."
            )
            self.route_after_policies()

        else:
            self.update_setup_page()
    
    def create_phrases_page(self):

        page = QWidget()
        page.setObjectName("phrasesPage")
        page.setStyleSheet("""
            QWidget#phrasesPage {
                background-color: #242F40;
            }
        """)

        layout = QVBoxLayout(page)

        # Título de la pantalla

        self.phrases_title = QLabel("Frases")
        self.phrases_title.setStyleSheet(
            "font-size: 28px;"
            "font-weight: bold;"
        )

        layout.addWidget(self.phrases_title)
        self.phrase_text = QLabel(
            "Aquí aparecerá el texto de la frase seleccionada."
        )

        self.phrase_text.setWordWrap(True)

        self.phrase_text.setStyleSheet(
            "font-size: 20px;"
            "padding: 15px;"
        )

        layout.addWidget(self.phrase_text)

        # Descripción

        self.phrases_description = QLabel(
            "Selecciona una frase para comunicarte."
        )

        self.phrases_description.setWordWrap(True)

        self.phrases_title.setStyleSheet(
            self.phrases_title.styleSheet() + "background: transparent; border: none;"
        )

        self.phrase_text.setStyleSheet(
            self.phrase_text.styleSheet() + "background: transparent; border: none;"
        )

        self.phrases_description.setStyleSheet("""
            font-size: 15px;
            background: transparent;
            border: none;
        """)

        layout.addWidget(self.phrases_description)

        layout.addSpacing(20)

        # Cuadrícula de frases
        self.phrases_grid = QGridLayout()
        self.phrases_grid.setVerticalSpacing(24)
        self.phrase_buttons = []

        for numero in range(1, 6):

            ruta_imagen = (
                Path(__file__).resolve().parent
                / "imagenes_gestos"
                / f"G{numero}.png"
            )

            boton = GestureButton(
                f"Frase {numero}",
                ruta_imagen
            )

            # Identificador del gesto encima de la fotografía
            boton.identificador.setText(f"G{numero}")
            boton.identificador.show()

            # Espacio suficiente para frases de dos o más renglones
            boton.etiqueta.setMinimumHeight(65)

            # Centrar el texto dentro de ese espacio
            boton.etiqueta.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            # Separación entre fotografía y frase
            boton.layout().setSpacing(10)

            boton.clicked.connect(
                lambda checked=False, n=numero: self.select_phrase(n)
            )

            if numero <= 3:
                fila = 0
                columna = (numero - 1) * 2
            else:
                fila = 1
                columna = 2 * (numero - 4) + 1

            self.phrases_grid.addWidget(
                boton, fila, columna, 1, 2
            ) 
            self.phrase_buttons.append(boton)

        layout.addLayout(self.phrases_grid)

        layout.addStretch()

        return page

    def select_phrase(self, numero):
        # Ignorar nuevas frases mientras hay una en proceso
        if self.reproduccion_frase_activa:
            return

        # Reservar la selección desde el primer clic o gesto
        self.reproduccion_frase_activa = True
        categorias = self.get_vexa_categories()

        if self.current_category not in categorias:
            return

        categoria = categorias[self.current_category]
        frases = categoria["frases"]

        # Los botones usan números del 1 al 5
        indice = numero - 1

        if indice < 0 or indice >= len(frases):
            return

        self.current_phrase = numero
        texto = frases[indice]
        # Apagar el resaltado anterior, si existe
        for tarjeta in self.phrase_buttons:
            tarjeta.resaltar(False)

        # Identificar e iluminar la frase seleccionada
        self.tarjeta_frase_activa = self.phrase_buttons[indice]
        self.tarjeta_frase_activa.resaltar(True)
        nombre_categoria = categoria["nombre"]

        # Mostrar el nombre real y la frase
        self.phrases_title.setText(
            f"{nombre_categoria} — {texto}"
        )

        self.phrase_text.setText(texto)
        # Pronunciar automáticamente la frase seleccionada
        self.hablar_vexa(
            texto,
            self.voz_seleccionada or "Femenina"
        )
        # Regresar a la pantalla de categorías
        #self.pages.setCurrentIndex(1)


    def open_admin_login(self):
        password, accepted = QInputDialog.getText(
            self,
            "Acceso administrativo",
            "Introduce la contraseña:",
            QLineEdit.EchoMode.Password
        )

        if not accepted:
            return

        if password == self.ADMIN_PASSWORD:
            promedio_sus = calcular_sus_promedio_global()

            if promedio_sus is None:
                texto_sus = "N/D"
            else:
                texto_sus = f"{promedio_sus:.2f} / 100"

            self.etiquetas_usabilidad["satisfaccion"].setText(
                texto_sus
            )

            efectividad = calcular_efectividad_global()

            if efectividad is None:
                texto_efectividad = "N/D"
            else:
                texto_efectividad = f"{efectividad:.2f}%"

            self.etiquetas_usabilidad["efectividad"].setText(
                texto_efectividad
            )

            eficiencia = calcular_eficiencia_global()

            if eficiencia is None:
                texto_eficiencia = "N/D"
            else:
                texto_eficiencia = f"{eficiencia:.3f} aciertos/s"

            self.etiquetas_usabilidad["eficiencia"].setText(
                texto_eficiencia
            )

            self.pages.setCurrentIndex(10)
        
        else:
            QMessageBox.warning(
                self,
                "Acceso denegado",
                "La contraseña no es correcta."
            )

    def create_admin_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Botón para activar o desactivar el modo experimental
        self.btn_experimental_mode = QPushButton()
        self.btn_experimental_mode.setMinimumSize(280, 55)
        self.btn_experimental_mode.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.btn_experimental_mode.clicked.connect(
            self.toggle_experimental_mode
        )

        self.update_experimental_mode_button()
        self.btn_experimental_results = QPushButton(
            "📊 Consultar resultados experimentales"
        )
        self.btn_experimental_results.setMinimumSize(280, 55)
        self.btn_experimental_results.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.btn_experimental_results.clicked.connect(
            self.open_experimental_results
        )
        back_button = QPushButton("Volver a Inicio")
        back_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )

        # Sección de métricas globales
        titulo_metricas = QLabel("Desempeño global de VEXA")
        titulo_metricas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo_metricas.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #A5B4FC;
                padding: 10px;
            }
        """)

        layout.addWidget(titulo_metricas)

        # Contenedor horizontal para las tres donas
        contenedor_donas = QHBoxLayout()
        contenedor_donas.setSpacing(12)
        contenedor_donas.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )
        # Primer círculo Exactitud global
        columna_exactitud = QVBoxLayout()

        self.dona_exactitud_global = GraficaDona()
        self.dona_exactitud_global.setFixedSize(170, 170)
        self.dona_exactitud_global.seleccionada = True
        self.dona_exactitud_global.update()

        etiqueta_exactitud = QLabel("Exactitud")
        etiqueta_exactitud.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        etiqueta_exactitud.setStyleSheet("""
            QLabel {
                font-size: 17px;
                font-weight: bold;
                color: #A5B4FC;
            }
        """)

        columna_exactitud.addWidget(
            self.dona_exactitud_global,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        columna_exactitud.addSpacing(12)
        columna_exactitud.addWidget(etiqueta_exactitud)

        contenedor_donas.addLayout(columna_exactitud)
        # Seguno círculo Precisión global
        columna_precision = QVBoxLayout()

        self.dona_precision_global = GraficaDona()
        self.dona_precision_global.setFixedSize(190, 190)

        etiqueta_precision = QLabel("Precisión")
        etiqueta_precision.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        etiqueta_precision.setStyleSheet("""
            QLabel {
                font-size: 17px;
                font-weight: bold;
                color: #A5B4FC;
            }
        """)

        columna_precision.addWidget(
            self.dona_precision_global,
            alignment=Qt.AlignmentFlag.AlignCenter
        )
        
        columna_precision.addSpacing(12)
        columna_precision.addWidget(etiqueta_precision)

        contenedor_donas.addLayout(columna_precision)        

        # Tercer círculo Sensibilidad global
        columna_sensibilidad = QVBoxLayout()

        self.dona_sensibilidad_global = GraficaDona()
        self.dona_sensibilidad_global.setFixedSize(190, 190)

        etiqueta_sensibilidad = QLabel("Sensibilidad")
        etiqueta_sensibilidad.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        etiqueta_sensibilidad.setStyleSheet("""
            QLabel {
                font-size: 17px;
                font-weight: bold;
                color: #A5B4FC;
            }
        """)

        columna_sensibilidad.addWidget(
            self.dona_sensibilidad_global,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        columna_sensibilidad.addSpacing(12)
        columna_sensibilidad.addWidget(etiqueta_sensibilidad)

        contenedor_donas.addLayout(columna_sensibilidad)
        # Obtener métricas globales de las sesiones aptas
        metricas_globales = calcular_metricas_globales_vexa()
        
        sesiones_aptas_globales = obtener_sesiones_aptas_globales()
        with sqlite3.connect(DB_PATH) as conexion:
            total_sesiones = conexion.execute(
                "SELECT COUNT(*) FROM sesiones"
            ).fetchone()[0]

        sesiones_excluidas = (
            total_sesiones - len(sesiones_aptas_globales)
        )
        etiqueta_sesiones = QLabel(
            f"Sesiones aptas: {len(sesiones_aptas_globales)}"
            f"   |   Sesiones excluidas: {sesiones_excluidas}"
            f"   |   Total registradas: {total_sesiones}"
        )

        etiqueta_sesiones.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        etiqueta_sesiones.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #94A3B8;
                padding: 6px;
            }
        """)

        donas_globales = {
            "exactitud": self.dona_exactitud_global,
            "precision": self.dona_precision_global,
            "sensibilidad": self.dona_sensibilidad_global
        }

        for nombre, dona in donas_globales.items():
            valor = metricas_globales[nombre]

            dona.porcentaje = (
                round(valor * 100, 1)
                if valor is not None
                else None
            )

            dona.update()
            layout.addLayout(
                contenedor_donas
            )
        layout.addWidget(etiqueta_sesiones)
      
        # Sección de resultados globales por gesto
        self.titulo_barras_globales = QLabel(
            "Exactitud global por gesto"
        )

        self.titulo_barras_globales.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.titulo_barras_globales.setStyleSheet("""
            QLabel {
                font-size: 19px;
                font-weight: bold;
                color: #A5B4FC;
                padding: 10px;
            }
        """)
        self.titulo_barras_globales.setMinimumHeight(48)
        # Contenedor para reconocimiento y usabilidad
        contenedor_analisis = QHBoxLayout()
        contenedor_analisis.setSpacing(24)

        # Columna izquierda: métricas por gesto
        columna_barras = QVBoxLayout()
        columna_barras.setSpacing(8)
        columna_barras.setContentsMargins(20, 18, 20, 18)

        # Columna derecha: usabilidad y tiempos
        columna_usabilidad = QVBoxLayout()
        columna_usabilidad.setSpacing(12)
        columna_usabilidad.setContentsMargins(20, 18, 20, 18)

        # Panel izquierdo
        panel_barras = QFrame()
        panel_barras.setLayout(columna_barras)
        panel_barras.setObjectName("panelBarras")
        panel_barras.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum
        )
        panel_barras.setStyleSheet("""
            QFrame#panelBarras {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 14px;
            }

            QLabel {
                border: none;
                background: transparent;
            }

            QProgressBar {
                background-color: #334155;
                border: none;
                border-radius: 5px;
                min-height: 18px;
                text-align: center;
                color: white;
            }

            QProgressBar::chunk {
                background-color: #818CF8;
                border-radius: 5px;
            }
        """)

        # Panel derecho
        panel_usabilidad = QFrame()
        panel_usabilidad.setLayout(columna_usabilidad)
        panel_usabilidad.setObjectName("panelUsabilidad")
        panel_usabilidad.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum
        )
        panel_usabilidad.setStyleSheet("""
            QFrame#panelUsabilidad {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 14px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        contenedor_analisis.addWidget(panel_barras, 1)
        contenedor_analisis.addWidget(panel_usabilidad, 1)
        contenedor_analisis.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )
        # Sección derecha: usabilidad
        titulo_usabilidad = QLabel("Usabilidad")
        titulo_usabilidad.setMinimumHeight(48)
        titulo_usabilidad.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        titulo_usabilidad.setStyleSheet("""
            QLabel {
                font-size: 19px;
                font-weight: bold;
                color: #A5B4FC;
                padding: 8px;
            }
        """)

        columna_usabilidad.addWidget(titulo_usabilidad)

        self.etiquetas_usabilidad = {}

        indicadores_usabilidad = [
            ("efectividad", "Efectividad"),
            ("eficiencia", "Eficiencia"),
            ("satisfaccion", "Satisfacción (SUS)")
        ]

        for clave, nombre in indicadores_usabilidad:
            fila = QHBoxLayout()

            etiqueta = QLabel(nombre)
            etiqueta.setStyleSheet(
                "font-size: 15px; color: #CBD5E1;"
            )

            valor = QLabel("N/D")
            valor.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )
            valor.setStyleSheet("""
                QLabel {
                    font-size: 17px;
                    font-weight: bold;
                    color: #A5B4FC;
                }
            """)

            fila.addWidget(etiqueta)
            fila.addWidget(valor)

            columna_usabilidad.addLayout(fila)
            self.etiquetas_usabilidad[clave] = valor

        promedio_sus = calcular_sus_promedio_global()

        if promedio_sus is None:
            texto_sus = "N/D"
        else:
            texto_sus = f"{promedio_sus:.2f} / 100"

        self.etiquetas_usabilidad["satisfaccion"].setText(
            texto_sus
        )

        # Sección de tiempos promedio
        titulo_tiempos = QLabel("Tiempos promedio")
        titulo_tiempos.setMinimumHeight(48)
        titulo_tiempos.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        titulo_tiempos.setStyleSheet("""
            QLabel {
                font-size: 19px;
                font-weight: bold;
                color: #A5B4FC;
                padding: 8px;
            }
        """)

        columna_usabilidad.addSpacing(18)
        columna_usabilidad.addWidget(titulo_tiempos)

        self.etiquetas_tiempos_globales = {}

        nombres_tiempos = {
            1: "Respuesta (ms)",
            2: "Selección (s)",
            3: "Interacción completa (s)"
        }

        for numero, nombre in nombres_tiempos.items():
            fila_tiempo = QHBoxLayout()

            etiqueta = QLabel(nombre)

            valor = QLabel("N/D")
            valor.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )
            valor.setStyleSheet(
                "font-size: 17px; font-weight: bold; color: #A5B4FC;"
            )

            fila_tiempo.addWidget(etiqueta)
            fila_tiempo.addWidget(valor)

            columna_usabilidad.addLayout(fila_tiempo)

            self.etiquetas_tiempos_globales[numero] = valor

        promedios_tiempos = {
            1: calcular_tiempo_respuesta_promedio_global(),
            2: calcular_tiempo_seleccion_promedio_global(),
            3: calcular_tiempo_interaccion_promedio_global()
        }

        for numero, promedio in promedios_tiempos.items():
            if promedio is None:
                texto = "N/D"
            elif numero == 1:
                texto = f"{promedio:.2f} ms"
            else:
                texto = f"{promedio:.2f} s"

            self.etiquetas_tiempos_globales[numero].setText(texto)

        columna_barras.addWidget(self.titulo_barras_globales)
        layout.addLayout(contenedor_analisis)
        layout.addSpacing(20)

        # Barras globales por gesto
        self.barras_globales = {}

        gestos_globales = [
            "G1", "G2", "G3", "G4",
            "G5", "G6", "G7"
        ]

        for gesto in gestos_globales:
            fila_gesto = QHBoxLayout()

            etiqueta = QLabel(gesto)
            etiqueta.setFixedWidth(65)

            barra = QProgressBar()
            barra.setRange(0, 100)
            barra.setMinimumHeight(22)

            barra.setValue(0)
            barra.setFormat("N/D")

            # Agregar etiqueta y barra a la fila
            fila_gesto.addWidget(etiqueta)
            fila_gesto.addWidget(barra)

            # Agregar la fila al dashboard
            columna_barras.addLayout(fila_gesto)

            # Guardar la barra para actualizarla después
            self.barras_globales[gesto] = barra

        # Mostrar exactitud global por gesto inicialmente
        for gesto, barra in self.barras_globales.items():
            metricas = calcular_metricas_globales_gesto(gesto)
            exactitud = metricas["exactitud"]

            if exactitud is not None:
                barra.setValue(round(exactitud * 100))
                barra.setFormat(f"{exactitud * 100:.2f}%")
            else:
                barra.setValue(0)
                barra.setFormat("N/D")

        def actualizar_barras_globales(metrica):
            nombres = {
                "exactitud": "Exactitud",
                "precision": "Precisión",
                "sensibilidad": "Sensibilidad"
            }

            self.titulo_barras_globales.setText(
                f"{nombres[metrica]} global por gesto"
            )

            for gesto, barra in self.barras_globales.items():
                metricas = calcular_metricas_globales_gesto(gesto)
                valor = metricas[metrica]

                if valor is not None:
                    barra.setValue(round(valor * 100))
                    barra.setFormat(f"{valor * 100:.2f}%")
                else:
                    barra.setValue(0)
                    barra.setFormat("N/D")

        def seleccionar_dona_global(metrica):
            donas = {
                "exactitud": self.dona_exactitud_global,
                "precision": self.dona_precision_global,
                "sensibilidad": self.dona_sensibilidad_global
            }

            for nombre, dona in donas.items():
                dona.seleccionada = (nombre == metrica)
                dona.update()

            actualizar_barras_globales(metrica)

        self.dona_exactitud_global.al_hacer_clic = (
            lambda: seleccionar_dona_global("exactitud")
        )

        self.dona_precision_global.al_hacer_clic = (
            lambda: seleccionar_dona_global("precision")
        )

        self.dona_sensibilidad_global.al_hacer_clic = (
            lambda: seleccionar_dona_global("sensibilidad")
        )
        
        # Botón ancho: métricas por sesión
        self.btn_experimental_results.setText(
            "Ver métricas por sesión"
        )
        self.btn_experimental_results.setMinimumHeight(55)

        layout.addSpacing(18)
        layout.addWidget(self.btn_experimental_results)

        # Fila inferior: perfil experimentador y volver
        fila_botones_inferiores = QHBoxLayout()
        fila_botones_inferiores.setSpacing(16)

        self.btn_experimental_mode.setMinimumHeight(55)
        back_button.setMinimumHeight(55)

        fila_botones_inferiores.addWidget(
            self.btn_experimental_mode,
            1
        )

        fila_botones_inferiores.addWidget(
            back_button,
            1
        )

        layout.addLayout(fila_botones_inferiores)

        return page

    def mostrar_metricas_sesion(self, sesion_id):
        dialog = QDialog(self)
        dialog.setWindowTitle(
            f"Métricas experimentales - Sesión {sesion_id}"
        )
        dialog.resize(950, 500)

        layout = QVBoxLayout(dialog)

        title = QLabel(
            f"Métricas por gesto - Sesión {sesion_id}"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        metrics_table = QTableWidget()
        metrics_table.setColumnCount(8)
        metrics_table.setHorizontalHeaderLabels([
            "Gesto",
            "VP",
            "VN",
            "FP",
            "FN",
            "Exactitud",
            "Precisión",
            "Sensibilidad"
        ])
        metrics_table.setColumnWidth(0, 85)

        for columna in range(1, 5):
            metrics_table.setColumnWidth(columna, 65)

        for columna in (5, 6, 7):
            metrics_table.setColumnWidth(columna, 175)

        metrics_table.verticalHeader().setDefaultSectionSize(42)

        layout.addWidget(title)
        layout.addWidget(metrics_table)
        panel_title = QLabel("📊 Análisis visual de métricas")
        panel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_title.setStyleSheet("""
            QLabel {
                font-size: 21px;
                font-weight: bold;
                color: #A5B4FC;
                padding: 12px;
                margin-top: 10px;
            }
        """)

        layout.addWidget(panel_title)
        btn_exactitud = QPushButton("Exactitud")
        btn_exactitud.setMinimumHeight(45)
        btn_exactitud.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        btn_exactitud.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #6366F1;
            }
        """)

        btn_precision = QPushButton("Precisión")
        btn_precision.setMinimumHeight(45)
        btn_precision.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        btn_sensibilidad.clicked.connect(
            lambda: descripcion_metrica.setText(
                "SENSIBILIDAD\n\n"
                "Indica qué proporción de los casos reales "
                "de un gesto fueron reconocidos correctamente.\n\n"
                "Fórmula: VP / (VP + FN)"
            )
        )

        btn_precision.setStyleSheet(
            btn_exactitud.styleSheet()
        )

        btn_sensibilidad = QPushButton("Sensibilidad")
        btn_sensibilidad.setMinimumHeight(45)
        btn_sensibilidad.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        btn_sensibilidad.setStyleSheet(
            btn_exactitud.styleSheet()
        )

        descripcion_metrica = QLabel(
            "EXACTITUD\n\n"
            "Indica la proporción de clasificaciones correctas "
            "respecto al total de casos evaluados.\n\n"
            "Fórmula: (VP + VN) / (VP + VN + FP + FN)"
        )

        botones_metricas = QHBoxLayout()

        botones_metricas.addWidget(btn_exactitud)
        botones_metricas.addWidget(btn_precision)
        botones_metricas.addWidget(btn_sensibilidad)

        layout.addLayout(botones_metricas)

        btn_exactitud.setCheckable(True)
        btn_precision.setCheckable(True)
        btn_sensibilidad.setCheckable(True)

        btn_exactitud.setChecked(True)

        for boton in (
            btn_exactitud,
            btn_precision,
            btn_sensibilidad
        ):
            boton.setStyleSheet(boton.styleSheet() + """
                QPushButton:checked {
                    background-color: #3730A3;
                    border: 2px solid #A5B4FC;
                }
            """)

        grupo_metricas = QButtonGroup(dialog)
        grupo_metricas.setExclusive(True)

        grupo_metricas.addButton(btn_exactitud)
        grupo_metricas.addButton(btn_precision)
        grupo_metricas.addButton(btn_sensibilidad)

        descripcion_metrica.setWordWrap(True)
        descripcion_metrica.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        descripcion_metrica.setStyleSheet("""
            QLabel {
                background-color: #1E293B;
                color: #E2E8F0;
                border: 1px solid #475569;
                border-radius: 12px;
                padding: 18px;
                font-size: 14px;
            }
        """)

        layout.addWidget(descripcion_metrica)
        exactitudes = []

        for gesto in gestos:
            metricas = calcular_metricas_gesto(sesion_id, gesto)

            if metricas["exactitud"] is not None:
                exactitudes.append(metricas["exactitud"])

        if exactitudes:
            promedio_exactitud = sum(exactitudes) / len(exactitudes)
            texto_exactitud = f"{promedio_exactitud * 100:.2f}%"
        else:
            texto_exactitud = "N/D"

        valor_metrica = QLabel(texto_exactitud)
        valor_metrica.setAlignment(Qt.AlignmentFlag.AlignCenter)

        valor_metrica.setStyleSheet("""
            QLabel {
                color: #A5B4FC;
                font-size: 38px;
                font-weight: bold;
                padding: 12px;
            }
        """)
        titulo_dona = QLabel("🔵 Desempeño de la sesión")

        titulo_dona.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        titulo_dona.setStyleSheet("""
            QLabel {
                color: #A5B4FC;
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
            }
        """)

        layout.addWidget(titulo_dona)
        grafica_dona = GraficaDona()

        grafica_dona.setFixedSize(190, 190)
        grafica_dona.porcentaje = (
            round(promedio_exactitud * 100)
            if exactitudes else 0
        )

        grafica_dona.update()

        layout.addWidget(
            grafica_dona,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        layout.addWidget(valor_metrica)
        grafica_circular = QProgressBar()
        grafica_circular.setRange(0, 100)
        grafica_circular.setValue(
            round(promedio_exactitud * 100)
            if exactitudes else 0
        )
        grafica_circular.setTextVisible(False)
        grafica_circular.setFixedHeight(18)

        grafica_circular.setStyleSheet("""
            QProgressBar {
                background-color: #1E293B;
                border: none;
                border-radius: 9px;
            }

            QProgressBar::chunk {
                background-color: #818CF8;
                border-radius: 9px;
            }
        """)

        layout.addWidget(grafica_circular)
        titulo_comparacion = QLabel(
            "📊 Comparación de resultados por gesto"
        )

        titulo_comparacion.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        titulo_comparacion.setStyleSheet("""
            QLabel {
                color: #A5B4FC;
                font-size: 18px;
                font-weight: bold;
                padding: 12px;
                margin-top: 10px;
            }
        """)

        layout.addWidget(titulo_comparacion)

        barras_por_gesto = {}

        for gesto in gestos:
            metricas_gesto = calcular_metricas_gesto(
                sesion_id, gesto
            )
            exactitud = metricas_gesto["exactitud"]

            fila_gesto = QHBoxLayout()

            etiqueta_gesto = QLabel(gesto)
            etiqueta_gesto.setFixedWidth(65)

            barra_gesto = QProgressBar()
            barra_gesto.setRange(0, 100)
            barra_gesto.setMinimumHeight(28)

            if exactitud is not None:
                barra_gesto.setValue(round(exactitud * 100))
                barra_gesto.setFormat(f"{exactitud * 100:.2f}%")
            else:
                barra_gesto.setValue(0)
                barra_gesto.setFormat("N/D")

            fila_gesto.addWidget(etiqueta_gesto)
            fila_gesto.addWidget(barra_gesto)

            columna_barras.addLayout(fila_gesto)

            barras_por_gesto[gesto] = barra_gesto

        def mostrar_precision_por_gesto():
            for gesto, barra in barras_por_gesto.items():
                metricas = calcular_metricas_gesto(
                    sesion_id, gesto
                )

                precision = metricas["precision"]

                if precision is not None:
                    barra.setValue(round(precision * 100))
                    barra.setFormat(f"{precision * 100:.2f}%")
                else:
                    barra.setValue(0)
                    barra.setFormat("N/D")


        btn_precision.clicked.connect(
            mostrar_precision_por_gesto
        )
        btn_precision.clicked.connect(
            lambda: (
                setattr(
                    grafica_dona,
                    "porcentaje",
                    round(promedio_precision * 100)
                    if precisiones else 0
                ),
                grafica_dona.update()
            )
        )

        def mostrar_sensibilidad_por_gesto():
            for gesto, barra in barras_por_gesto.items():
                metricas = calcular_metricas_gesto(
                    sesion_id, gesto
                )

                sensibilidad = metricas["sensibilidad"]

                if sensibilidad is not None:
                    barra.setValue(round(sensibilidad * 100))
                    barra.setFormat(f"{sensibilidad * 100:.2f}%")
                else:
                    barra.setValue(0)
                    barra.setFormat("N/D")


        btn_sensibilidad.clicked.connect(
            mostrar_sensibilidad_por_gesto
        )
        btn_sensibilidad.clicked.connect(
            lambda: (
                setattr(
                    grafica_dona,
                    "porcentaje",
                    round(promedio_sensibilidad * 100)
                    if sensibilidades else 0
                ),
                grafica_dona.update()
            )
        )

        def mostrar_exactitud_por_gesto():
            for gesto, barra in barras_por_gesto.items():
                metricas = calcular_metricas_gesto(
                    sesion_id, gesto
                )

                exactitud = metricas["exactitud"]

                if exactitud is not None:
                    barra.setValue(round(exactitud * 100))
                    barra.setFormat(f"{exactitud * 100:.2f}%")
                else:
                    barra.setValue(0)
                    barra.setFormat("N/D")


        btn_exactitud.clicked.connect(
            mostrar_exactitud_por_gesto
        )
        
        precisiones = []

        for gesto in gestos:
            metricas = calcular_metricas_gesto(sesion_id, gesto)

            if metricas["precision"] is not None:
                precisiones.append(metricas["precision"])

        if precisiones:
            promedio_precision = sum(precisiones) / len(precisiones)
            texto_precision = f"{promedio_precision * 100:.2f}%"
        else:
            texto_precision = "N/D"

        btn_precision.clicked.connect(
            lambda: valor_metrica.setText(texto_precision)
        )

        btn_exactitud.clicked.connect(
            lambda: valor_metrica.setText(texto_exactitud)
        )
        sensibilidades = []

        for gesto in gestos:
            metricas = calcular_metricas_gesto(sesion_id, gesto)

            if metricas["sensibilidad"] is not None:
                sensibilidades.append(metricas["sensibilidad"])

        if sensibilidades:
            promedio_sensibilidad = (
                sum(sensibilidades) / len(sensibilidades)
            )
            texto_sensibilidad = f"{promedio_sensibilidad * 100:.2f}%"
        else:
            texto_sensibilidad = "N/D"

        btn_sensibilidad.clicked.connect(
            lambda: valor_metrica.setText(texto_sensibilidad)
        )
        btn_exactitud.clicked.connect(
            lambda: grafica_circular.setValue(
                round(promedio_exactitud * 100)
                if exactitudes else 0
            )
        )

        btn_precision.clicked.connect(
            lambda: grafica_circular.setValue(
                round(promedio_precision * 100)
                if precisiones else 0
            )
        )

        btn_sensibilidad.clicked.connect(
            lambda: grafica_circular.setValue(
                round(promedio_sensibilidad * 100)
                if sensibilidades else 0
            )
        )
        btn_exactitud.clicked.connect(
            lambda: descripcion_metrica.setText(
                "EXACTITUD\n\n"
                "Indica la proporción de clasificaciones correctas "
                "respecto al total de casos evaluados.\n\n"
                "Fórmula: (VP + VN) / (VP + VN + FP + FN)"
            )
        )
        
        btn_precision.clicked.connect(
            lambda: descripcion_metrica.setText(
                "PRECISIÓN\n\n"
                "Indica qué proporción de las detecciones "
                "atribuidas a un gesto fueron correctas.\n\n"
                "Fórmula: VP / (VP + FP)"
            )
        )

        gestos = [
            "G1", "G2", "G3", "G4",
            "G5", "G6", "G7", "ninguno"
        ]

        for gesto in gestos:
            conteos = calcular_conteos_gesto(
                sesion_id, gesto
            )

            fila = metrics_table.rowCount()
            metrics_table.insertRow(fila)

            metricas = calcular_metricas_gesto(sesion_id, gesto)

            valores = [
                gesto,
                conteos["VP"],
                conteos["VN"],
                conteos["FP"],
                conteos["FN"],
                (
                    f"{metricas['exactitud'] * 100:.2f}%"
                    if metricas["exactitud"] is not None
                    else "N/D"
                ),
                (
                    f"{metricas['precision'] * 100:.2f}%"
                    if metricas["precision"] is not None
                    else "N/D"
                ),
                (
                    f"{metricas['sensibilidad'] * 100:.2f}%"
                    if metricas["sensibilidad"] is not None
                    else "N/D"
                )
            ]
            
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))

                if columna in (5, 6, 7) and valor != "N/D":
                    porcentaje = float(valor.replace("%", ""))

                    if porcentaje >= 90:
                        color = "#39D98A"  # Verde
                    elif porcentaje >= 70:
                        color = "#F4C95D"  # Amarillo
                    else:
                        color = "#F87171"  # Rojo

                    item.setForeground(QColor(color))

                metrics_table.setItem(fila, columna, item)
                if columna in (5, 6, 7) and valor != "N/D":
                    barra = QProgressBar()
                    barra.setRange(0, 100)
                    barra.setValue(round(porcentaje))
                    barra.setFormat(f"{porcentaje:.2f}%")
                    barra.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    barra.setMinimumHeight(28)

                    barra.setStyleSheet(f"""
                        QProgressBar {{
                            background-color: #202938;
                            border: 1px solid #374151;
                            border-radius: 7px;
                            color: white;
                            text-align: center;
                            font-weight: bold;
                        }}

                        QProgressBar::chunk {{
                            background-color: {color};
                            border-radius: 6px;
                        }}
                    """)

                    metrics_table.setCellWidget(
                        fila, columna, barra
                    )

        dialog.exec()

    def open_experimental_results(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Resultados experimentales de VEXA")
        dialog.resize(950, 650)

        layout = QVBoxLayout(dialog)

        title = QLabel("Resultados experimentales")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 26px; font-weight: bold;"
        )

        description = QLabel(
            "Consulta de sesiones, métricas y resultados "
            "del protocolo experimental de VEXA."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)

        sessions_table = QTableWidget()
        sessions_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        sessions_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        sessions_table.setShowGrid(True)
        sessions_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #6B7280;
            }

            QTableWidget::item:selected {
                background-color: #6366F1;
                color: #FFFFFF;
            }
        """)
        sessions_table.setColumnCount(6)
        sessions_table.setHorizontalHeaderLabels([
            "ID sesión",
            "Participante",
            "Fecha",
            "Estado",
            "Apta para análisis",
            "Motivo"
        ])
        
        sessions_table.setColumnWidth(0, 100)
        sessions_table.setColumnWidth(1, 180)
        sessions_table.setColumnWidth(2, 250)
        sessions_table.setColumnWidth(3, 180)

        sessions_table.setColumnWidth(4, 180)
        sessions_table.setColumnWidth(5, 350)

        layout.addWidget(sessions_table)
        metrics_button = QPushButton(
            "Ver métricas de la sesión seleccionada"
        )
        metrics_button.setMinimumHeight(45)

        layout.addWidget(metrics_button)
        def consultar_metricas_seleccionadas():
            fila = sessions_table.currentRow()

            if fila < 0:
                QMessageBox.warning(
                    dialog,
                    "Selecciona una sesión",
                    "Primero selecciona una sesión de la tabla."
                )
                return

            sesion_id = int(
                sessions_table.item(fila, 0).text()
            )

            verificacion = verificar_sesion_para_analisis(
                sesion_id
            )

            if not verificacion["apta"]:
                QMessageBox.warning(
                    dialog,
                    "Sesión no apta para análisis",
                    verificacion.get(
                        "motivo",
                        "La sesión no cumple los criterios de análisis."
                    )
                )
                return

            self.mostrar_metricas_sesion(sesion_id)

        metrics_button.clicked.connect(
            consultar_metricas_seleccionadas
        )
        
        participantes = obtener_participantes()

        for participante in participantes:
            sesiones = obtener_sesiones_participante(
                participante["id"]
            )

            for sesion in sesiones:
                fila = sessions_table.rowCount()
                sessions_table.insertRow(fila)

                verificacion = verificar_sesion_para_analisis(
                    sesion["id"]
                )

                apta = "Sí" if verificacion["apta"] else "No"

                motivo = (
                    "Cumple los criterios de análisis"
                    if verificacion["apta"]
                    else verificacion.get("motivo", "Motivo no disponible")
                )

                valores = [
                    sesion["id"],
                    participante["codigo"],
                    sesion["fecha_inicio"],
                    sesion["estado"],
                    apta,
                    motivo
                ]

                for columna, valor in enumerate(valores):
                    sessions_table.setItem(
                        fila,
                        columna,
                        QTableWidgetItem(str(valor))
                    )
        dialog.exec()
        
    def create_data_page(self):

        page = QWidget()
        layout_principal = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setSizeConstraint(
            QLayout.SizeConstraint.SetMinimumSize
        )
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 24)

        scroll.setWidget(contenido)
        layout_principal.addWidget(scroll)

        title = QLabel("Datos")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")

        description = QLabel(
            "Aquí podremos visualizar información "
            "de EMG y Face Mesh."
        )

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(description)

        layout.addStretch()

        return page

    def create_settings_page(self):

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Configuración")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
        )
        title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )

        description = QLabel(
            "Consulta tu perfil y las opciones de VEXA."
        )
        description.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )
        description.setWordWrap(True)

        # Sección del usuario activo
        user_title = QLabel("Usuario actualmente activo")
        user_title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        user_title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )

        self.active_profile_label = QLabel()
        self.active_profile_label.setStyleSheet(
            "font-size: 20px; color: #60A5FA;"
        )
        self.active_profile_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )

        self.update_active_profile_label()

        layout.addWidget(title)
        layout.addSpacing(15)
        layout.addWidget(description)
        layout.addSpacing(35)
        layout.addWidget(user_title)

        layout.addWidget(self.active_profile_label)

        # Botón para cambiar de usuario
        self.btn_change_user = QPushButton("Cambiar de usuario")
        self.btn_change_user.setFixedWidth(240)
        self.btn_change_user.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.btn_change_user.clicked.connect(
            self.change_user
        )

        layout.addSpacing(25)
        layout.addWidget(
            self.btn_change_user,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        # Botón para administrar perfiles
        self.btn_manage_profiles = QPushButton(
            "Administrar perfiles"
        )
        self.btn_manage_profiles.setFixedWidth(240)
        self.btn_manage_profiles.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.btn_manage_profiles.clicked.connect(
            self.open_manage_profiles
        )

        layout.addSpacing(15)
        layout.addWidget(
            self.btn_manage_profiles,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        # Sección de personalización de voz
        voice_title = QLabel("Voz de VEXA")
        voice_title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        voice_title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )

        layout.addSpacing(35)
        layout.addWidget(voice_title)
        # Botón para abrir la configuración de voz
        self.btn_voice_settings = QPushButton(
            "🎙️ Elegir o cambiar voz"
        )
        self.btn_voice_settings.setFixedWidth(240)
        self.btn_voice_settings.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.btn_voice_settings.clicked.connect(
            self.abrir_seleccion_voz
        )

        layout.addSpacing(15)
        layout.addWidget(
            self.btn_voice_settings,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        layout.addStretch()

        return page

    def create_voice_selection_page(self):
        """Crea la pantalla para elegir la voz de VEXA."""

        page = QWidget()
        layout = QVBoxLayout(page)
        # Espacio flexible para centrar el contenido verticalmente
        layout.addStretch()

        title = QLabel("Selecciona la voz de VEXA")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
        )
        title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )

        description = QLabel(
            "Elige cómo quieres escuchar tus frases."
        )
        description.setStyleSheet("font-size: 22px;")
        description.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(description)
        # Tarjetas para elegir la voz
        voice_cards = QHBoxLayout()
        voice_cards.setSpacing(20)

        self.btn_female_voice = QPushButton(
            "🎙️\n\nVoz femenina"
        )
        self.btn_male_voice = QPushButton(
            "🎙️\n\nVoz masculina"
        )
        # Permitir seleccionar una sola voz
        self.btn_female_voice.setCheckable(True)
        self.btn_male_voice.setCheckable(True)

        # Selección de voces exclusiva, ambas desmarcadas
        self.btn_female_voice.setAutoExclusive(False)
        self.btn_male_voice.setAutoExclusive(False)

        self.btn_female_voice.clicked.connect(
            lambda: self.guardar_voz_perfil("Femenina")
        )

        self.btn_male_voice.clicked.connect(
            lambda: self.guardar_voz_perfil("Masculina")
        )
        
        # Demostraciones de voz
        self.btn_female_voice.clicked.connect(
            lambda: self.demostrar_voz_vexa("Femenina")
        )

        self.btn_male_voice.clicked.connect(
            lambda: self.demostrar_voz_vexa("Masculina")
        )

        for boton in (
            self.btn_female_voice,
            self.btn_male_voice
        ):
            boton.setFixedSize(220, 160)
            boton.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            boton.setStyleSheet("""
                QPushButton {
                    background-color: #202938;
                    color: white;
                    border: 2px solid #4B5563;
                    border-radius: 16px;
                    font-size: 20px;
                    font-weight: bold;
                }

                QPushButton:hover {
                    border: 2px solid #60A5FA;
                }
                QPushButton:checked {
                    border: 4px solid #39D98A;
                    background-color: #253D38;
                }
            """)

        voice_cards.addStretch()
        voice_cards.addWidget(self.btn_female_voice)
        voice_cards.addWidget(self.btn_male_voice)
        voice_cards.addStretch()

        layout.addSpacing(90)
        layout.addLayout(voice_cards)
        
        # Botón de regreso, centrado debajo de las tarjetas
        btn_regresar_voz = QPushButton("Aceptar")
        btn_regresar_voz.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_regresar_voz.setFixedHeight(45)
        btn_regresar_voz.setFixedWidth(180)

        btn_regresar_voz.clicked.connect(
            self.regresar_desde_seleccion_voz
        )

        layout.addSpacing(40)
        layout.addWidget(
            btn_regresar_voz,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        
        layout.addStretch()
        return page

    def iniciar_emg_vexa(self, puerto="COM9", umbrales=None):
        """Conecta el lector EMG sin modificar el motor facial."""
        self.emg_habilitado = False

        if umbrales is None:
            print("[VEXA EMG] Faltan umbrales reales calibrados.")
            return False

        try:
            import sys
            from pathlib import Path

            carpeta_entrega = (
                Path(__file__).resolve().parent
                / "VEXA_ENTREGA_VEXA"
            )

            if str(carpeta_entrega) not in sys.path:
                sys.path.insert(0, str(carpeta_entrega))

            from reconocimiento_vexa.emg_lector import LectorEMG
            from reconocimiento_vexa.emg_puente import PuenteEMG

            lector_anterior = getattr(self, "lector_emg", None)

            if lector_anterior is not None:
                lector_anterior.detener()

            self.lector_emg = None
            self.puente_emg = None

            lector = LectorEMG(puerto)
            lector.iniciar()

            self.lector_emg = lector
            self.puente_emg = PuenteEMG(
                lector,
                umbrales=umbrales,
            )

            self.emg_habilitado = True

            print(f"[VEXA EMG] Lector iniciado en {puerto}.")
            return True

        except Exception as exc:
            self.emg_habilitado = False
            self.puente_emg = None
            print(f"[VEXA EMG] No se pudo iniciar: {exc}")
            return False

    def detener_emg_vexa(self):
        """Detiene EMG y conserva disponible el modo facial."""
        self.emg_habilitado = False
        self.puente_emg = None

        lector = getattr(self, "lector_emg", None)
        self.lector_emg = None

        if lector is not None:
            try:
                lector.detener()
            except Exception as exc:
                print(f"[VEXA EMG] Error al detener: {exc}")

        print("[VEXA EMG] Modo facial sin EMG disponible.")

    def recibir_gesto_facial(self, evento):
        """Recibe e interpreta un gesto confirmado por MediaPipe."""

        print(f"[VEXA FACIAL] Gesto recibido: {evento}")

        # Ignorar eventos cuando el reconocimiento está deshabilitado, excepto durante pruebas simuladas controladas.
        if not self.reconocimiento_facial_habilitado:
            print("[VEXA FACIAL] Evento ignorado: reconocimiento apagado.")
            return

        # Nunca intervenir en el perfil experimental.
        if self.experimental_mode_enabled:
            return

        # Evitar gestos durante el destello de una categoría
        # o mientras se prepara/reproduce una frase.
        if self.transicion_categoria_activa:
            return

        if self.reproduccion_frase_activa:
            return

        # Comprobar que el modo corresponda a la pantalla visible.
        modo_esperado = self.modo_facial_segun_pantalla()

        if modo_esperado != self.modo_reconocimiento_actual:
            print("[VEXA FACIAL] Evento ignorado: pantalla o modo diferente.")
            return

        # VEXA EMG: validacion opcional de gestos bucales.
        # Desactivado por defecto para preservar el modo facial.
        gestos_bucales_emg = {
            "G1F", "G2F", "G3F", "G4F", "G5F",
            "G6F", "G7F", "G8F", "G9F", "G10F",
        }

        if (
            getattr(self, "emg_habilitado", False)
            and evento in gestos_bucales_emg
        ):
            puente = getattr(self, "puente_emg", None)

            if puente is None:
                print("[VEXA EMG] Gesto bloqueado: puente no disponible.")
                return

            try:
                autorizado, motivo = puente.validar(evento)
            except Exception as exc:
                print(f"[VEXA EMG] Error de validacion: {exc}")
                return

            print(
                f"[VEXA EMG] {evento}: "
                f"{'AUTORIZADO' if autorizado else 'BLOQUEADO'} "
                f"({motivo})"
            )

            if not autorizado:
                return

        categorias_por_gesto = {
            "G1F": 1,
            "G2F": 2,
            "G3F": 3,
            "G4F": 4,
            "G6F": 5,
            "G7F": 6,
            "G8F": 7,
            "G9F": 8,
        }

        if self.modo_reconocimiento_actual == "FRASES":
            frases_por_gesto = {
                "G1F": 1,
                "G2F": 2,
                "G3F": 3,
                "G4F": 4,
                "G5F": 5,
            }

            if evento in frases_por_gesto:
                numero = frases_por_gesto[evento]
                print(f"[VEXA FACIAL] Frase identificada: {numero}")
                self.select_phrase(numero)

        elif self.modo_reconocimiento_actual == "CATEGORIAS":
            if evento in categorias_por_gesto:
                numero = categorias_por_gesto[evento]
                print(f"[VEXA FACIAL] Categoría identificada: {numero}")
                self.open_category(numero)
    
    def probar_conexion_facial(self):
        """Prueba temporal de la conexión sin usar la cámara."""

        if not self.preparar_reconocimiento_facial():
            print("[VEXA FACIAL] No se pudo preparar el servicio.")
            return

        self.servicio_reconocimiento.evento_final.emit("G1F")
    
    def preparar_reconocimiento_facial(self):
        """Prepara MediaPipe para el perfil activo de VEXA."""

        # No utilizar reconocimiento facial en modo experimental.
        if self.experimental_mode_enabled:
            return False

        # Cada usuario necesita un perfil seleccionado.
        if not self.current_profile:
            return False

        # Reutilizar el servicio únicamente si pertenece al perfil activo.
        if self.servicio_reconocimiento is not None:
            if self.servicio_reconocimiento.id_perfil == self.current_profile:
                return True

            # No cambiar de perfil mientras la cámara anterior siga funcionando.
            hilo = self.servicio_reconocimiento.hilo

            if hilo is not None and hilo.isRunning():
                self.servicio_reconocimiento.detener()
                print(
                    "[VEXA FACIAL] Esperando que termine el reconocimiento "
                    "del perfil anterior."
                )
                return False

            # El servicio anterior ya no tiene una captura activa.
            self.servicio_reconocimiento.deleteLater()
            self.servicio_reconocimiento = None

        self.servicio_reconocimiento = ServicioReconocimiento(
            id_perfil=self.current_profile,
            indice_camara=0,
            modo_experimental=False,
            parent=self
        )
        # Recibir los gestos confirmados por MediaPipe.
        self.servicio_reconocimiento.evento_final.connect(
            self.recibir_gesto_facial
        )

        self.servicio_reconocimiento.terminado.connect(
            self.reconocimiento_facial_terminado
        )
        self.servicio_reconocimiento.error.connect(
            self.manejar_error_reconocimiento_facial
        )

        return True

    def detener_reconocimiento_facial(self):
        """Solicita detener la captura facial del perfil normal."""
        self.detencion_facial_solicitada = True
        self.reconocimiento_facial_activo = False
        self.modo_reconocimiento_actual = None

        servicio = self.servicio_reconocimiento
        if servicio is not None:
            servicio.detener()

    def modo_facial_segun_pantalla(self):
        """Determina qué reconocimiento corresponde a la pantalla actual."""
        if self.experimental_mode_enabled:
            return None

        if not self.current_profile:
            return None

        if self.pages.currentIndex() == 1:
            if self.transicion_categoria_activa:
                return None
            if self.reproduccion_frase_activa:
                return None
            return "CATEGORIAS"

        if self.pages.currentIndex() == 6:
            if self.reproduccion_frase_activa:
                return None
            return "FRASES"

        return None

    def iniciar_reconocimiento_facial_normal(self):
        if not self.reconocimiento_facial_habilitado:
            print("[VEXA FACIAL] Inicio bloqueado: reconocimiento deshabilitado.")
            return False
        """Inicia una sesión facial solamente cuando es seguro hacerlo."""
        modo = self.modo_facial_segun_pantalla()

        if modo is None:
            return False

        if not self.preparar_reconocimiento_facial():
            return False

        servicio = self.servicio_reconocimiento

        # Nunca iniciar otra captura mientras una anterior siga viva.
        hilo = servicio.hilo
        if hilo is not None and hilo.isRunning():
            return False

        self.modo_reconocimiento_actual = modo
        self.reconocimiento_facial_activo = True

        print(f"[VEXA FACIAL] Iniciando modo {modo}")
        self.detencion_facial_solicitada = False
        servicio.iniciar(modo)
        return True

    def reconocimiento_facial_terminado(self):
        """Recibe la confirmación de que Ale terminó su sesión."""

        self.reconocimiento_facial_activo = False

        if self.detencion_facial_solicitada:
            print(
                "[VEXA FACIAL] Detención solicitada; no se reiniciará."
            )
            return

        if not self.reconocimiento_facial_habilitado:
            return

        if self.experimental_mode_enabled:
            return

        if self.modo_facial_segun_pantalla() is None:
            print(
                "[VEXA FACIAL] Esperando fin de transición o audio."
            )
            return

        QTimer.singleShot(
            150,
            self.reanudar_reconocimiento_facial_normal
        )
    
    def reanudar_reconocimiento_facial_normal(self):
        """Reanuda solo cuando la sesión anterior terminó completamente."""

        if not self.reconocimiento_facial_habilitado:
            return

        if self.detencion_facial_solicitada:
            return

        if self.experimental_mode_enabled:
            return

        modo = self.modo_facial_segun_pantalla()

        if modo is None:
            return

        servicio = self.servicio_reconocimiento

        if servicio is None:
            return

        if servicio.id_perfil != self.current_profile:
            return

        # No competir con un cambio de modo pendiente de Ale.
        if getattr(servicio, "_pendiente", None) is not None:
            return

        hilo = servicio.hilo

        if hilo is not None:
            if hilo.isRunning() or not hilo.isFinished():
                return

        self.iniciar_reconocimiento_facial_normal()

    def habilitar_reconocimiento_facial_normal(self):
        """Habilita el reconocimiento únicamente para un perfil normal."""
        if self.experimental_mode_enabled:
            return False

        if not self.current_profile:
            return False

        # No permitir la activación en el perfil experimental.
        if self.current_profile.casefold() == "perfil experimental":
            return False

        # Verificar carga de calibración real
        try:
            from reconocimiento_vexa.calibracion.perfiles import (
                cargar_calibracion
            )
            cargar_calibracion(self.current_profile)
        except Exception as exc:
            print(
                "[VEXA FACIAL] Perfil sin calibración válida:",
                self.current_profile,
                exc
            )
            return False

        if self.pages.currentIndex() not in (1, 6):
            return False

        self.detencion_facial_solicitada = False
        self.reconocimiento_facial_habilitado = True

        if self.iniciar_reconocimiento_facial_normal():
            return True

        self.reconocimiento_facial_habilitado = False
        return False

    def manejar_error_reconocimiento_facial(self, mensaje):
        """Desactiva el reconocimiento si falla la cámara o la calibración."""

        print(f"[VEXA FACIAL] Error: {mensaje}")

        # Impedir cualquier reinicio automático pendiente.
        self.reconocimiento_facial_habilitado = False
        self.detencion_facial_solicitada = True
        self.reconocimiento_facial_activo = False
        self.modo_reconocimiento_actual = None

        servicio = self.servicio_reconocimiento

        if servicio is not None:
            servicio.detener()

        # Informar sin cerrar VEXA ni impedir el uso de los botones.
        QMessageBox.warning(
            self,
            "Reconocimiento facial",
            "No fue posible continuar con el reconocimiento facial.\n\n"
            f"Detalle: {mensaje}\n\n"
            "Puedes seguir utilizando VEXA mediante los botones."
        )
    
    def controlar_reconocimiento_por_pantalla(self, index):
        """Coordina las sesiones faciales al navegar entre pantallas."""

        if self.experimental_mode_enabled:
            return

        # Fuera de Categorías y Frases: detener definitivamente.
        if index not in (1, 6):
            self.detener_reconocimiento_facial()
            return

        modo_nuevo = "CATEGORIAS" if index == 1 else "FRASES"

        # Activar el reconocimiento al entrar a una pantalla facial
        if not self.reconocimiento_facial_habilitado:
            self.habilitar_reconocimiento_facial_normal()
            return

        servicio = self.servicio_reconocimiento

        # Solo conservar la habilitación si ya estaba activa.
        if self.reconocimiento_facial_habilitado:
            self.detencion_facial_solicitada = False

        self.reconocimiento_facial_activo = False
        self.modo_reconocimiento_actual = modo_nuevo

        if servicio is not None:
            hilo = servicio.hilo

            if hilo is not None and hilo.isRunning():
                servicio.detener()
                print(
                    f"[VEXA FACIAL] Esperando liberación para {modo_nuevo}"
                )
                return

        # Si la cámara ya está libre, programar la reanudación y se comprueban tods las condicionnes
        if self.reconocimiento_facial_habilitado:
            QTimer.singleShot(
                0,
                self.reanudar_reconocimiento_facial_normal
            )

        print(f"[VEXA FACIAL] Pantalla cambiada: {modo_nuevo}")
    
    def update_active_profile_label(self):

        if not hasattr(self, "active_profile_label"):
            return

        if self.current_profile:
            self.active_profile_label.setText(
                self.current_profile
            )
        else:
            self.active_profile_label.setText(
                "Ningún perfil seleccionado"
            )
                
    def change_user(self):

        # Recordar que venimos de Configuración
        self.profile_return_page = 5

        self.refresh_profiles()
        self.pages.setCurrentIndex(7)
    
    def return_from_profile_page(self):
        # Comprobar si existe un perfil activo válido
        profiles = self.settings_store.value(
            "profiles", [], type=list
        )

        if (
            not self.current_profile
            or self.current_profile not in profiles
        ):
            QMessageBox.information(
                self,
                "Selecciona un perfil",
                "Debes seleccionar un perfil para "
                "continuar utilizando VEXA."
            )
            return

        # Regresar a la pantalla desde donde se abrió
        return_page = getattr(
            self, "profile_return_page", 0
        )

        self.profile_return_page = 0

        # Actualizar el nombre del usuario activo
        self.update_active_profile_label()

        self.pages.setCurrentIndex(return_page)

    def open_profile_from_home(self):

        # Recordar que venimos de Inicio
        self.profile_return_page = 0
        self.pages.setCurrentIndex(7)  

    def create_manage_profiles_page(self):

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Administrar perfiles")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
        )
        title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )

        description = QLabel(
            "Consulta los perfiles registrados en VEXA "
            "y su progreso de preparación."
        )
        description.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )
        description.setWordWrap(True)
        description.setStyleSheet("""
            font-size: 18px;
            color: #D1D5DB;
            padding: 5px;
        """)

        # Área desplazable para las tarjetas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(
            QScrollArea.Shape.NoFrame
        )

        self.profiles_container = QWidget()
        self.profiles_cards_layout = QGridLayout(
            self.profiles_container
        )
        self.profiles_cards_layout.setSpacing(15)
        self.profiles_cards_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        scroll_area.setWidget(self.profiles_container)

        # Botón para regresar a Configuración
        back_button = QPushButton(
            "Volver a Configuración"
        )
        back_button.setFixedWidth(260)
        back_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(5)
        )

        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        layout.addWidget(title)
        layout.addWidget(description)

        # Limitar la altura del área de tarjetas

        layout.addWidget(scroll_area, 1)
        layout.addWidget(
            back_button,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )


        return page

    def rename_profile(self, old_name):

        # Proteger el perfil experimental
        if old_name == "Perfil experimental":
            QMessageBox.warning(
                self,
                "Perfil protegido",
                "El nombre del perfil experimental "
                "no se puede modificar."
            )
            return

        # Comprobar que el perfil existe y es normal
        profiles = self.settings_store.value(
            "profiles", [], type=list
        )

        if old_name not in profiles:
            QMessageBox.warning(
                self,
                "Perfil no disponible",
                "Este perfil no se puede renombrar."
            )
            return

        # Solicitar el nuevo nombre
        new_name, accepted = QInputDialog.getText(
            self,
            "Cambiar nombre",
            "Escribe el nuevo nombre del perfil:",
            text=old_name
        )

        if not accepted:
            return

        new_name = new_name.strip()

        if not new_name:
            QMessageBox.warning(
                self,
                "Nombre no válido",
                "Escribe un nombre para el perfil."
            )
            return

        # Reservar el nombre experimental
        if new_name.casefold() == "perfil experimental":
            QMessageBox.warning(
                self,
                "Nombre reservado",
                "Ese nombre está reservado "
                "para las evaluaciones."
            )
            return

        # Evitar nombres duplicados
        if any(
            name.casefold() == new_name.casefold()
            for name in profiles
            if name != old_name
        ):
            QMessageBox.warning(
                self,
                "Perfil duplicado",
                "Ya existe un perfil con ese nombre."
            )
            return

        if new_name == old_name:
            return

        # Recuperar el progreso guardado
        all_progress = self.settings_store.value(
            "profile_progress", {}
        )

        if not isinstance(all_progress, dict):
            all_progress = {}

        # No sobrescribir progreso existente
        if new_name in all_progress:
            QMessageBox.warning(
                self,
                "Nombre no disponible",
                "Ya existen datos guardados con "
                "ese nombre. Elige otro."
            )
            return

        # Trasladar el progreso al nuevo nombre
        if old_name in all_progress:
            all_progress[new_name] = all_progress.pop(
                old_name
            )

        # Conservar la voz al cambiar el nombre del perfil
        voz_guardada = self.settings_store.value(
            f"voz_perfil/{old_name}",
            None
        )

        if voz_guardada is not None:
            self.settings_store.setValue(
                f"voz_perfil/{new_name}",
                voz_guardada
            )

        self.settings_store.remove(
            f"voz_perfil/{old_name}"
        )
        
        # Actualizar el nombre en la lista
        index = profiles.index(old_name)
        profiles[index] = new_name

        self.settings_store.setValue(
            "profile_progress", all_progress
        )
        self.settings_store.setValue(
            "profiles", profiles
        )

        # Actualizar el último perfil utilizado
        last_profile = self.settings_store.value(
            "last_profile", ""
        )

        if last_profile == old_name:
            self.settings_store.setValue(
                "last_profile", new_name
            )

        # Actualizar el perfil activo
        if self.current_profile == old_name:
            self.current_profile = new_name

        self.profiles = profiles
        self.settings_store.sync()

        # Refrescar las pantallas
        self.refresh_profiles()
        self.refresh_manage_profiles_cards()
        self.update_active_profile_label()

        QMessageBox.information(
            self,
            "Nombre actualizado",
            f"El perfil ahora se llama '{new_name}'."
        )

    def open_manage_profiles(self):

        # Actualizar las tarjetas antes de abrir la pantalla
        self.refresh_manage_profiles_cards()

        self.pages.setCurrentIndex(11)

    def refresh_manage_profiles_cards(self):

        # Eliminar las tarjetas anteriores
        while self.profiles_cards_layout.count():

            item = self.profiles_cards_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        # Consultar los perfiles guardados
        profiles = self.settings_store.value(
            "profiles", [], type=list
        )
       
        # Separar los perfiles normales del experimental
        normal_profiles = [
            profile
            for profile in profiles
            if profile != "Perfil experimental"
        ]

        # Mostrar siempre el experimental al final si está activo
        profiles = normal_profiles

        if (
            self.experimental_mode_enabled
            and "Perfil experimental" in self.settings_store.value(
                "profiles", [], type=list
            )
        ):
            profiles.append("Perfil experimental")

        if not profiles:
            empty_label = QLabel(
                "No hay perfiles registrados."
            )
            empty_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self.profiles_cards_layout.addWidget(
                empty_label, 0, 0
            )
            return

        # Crear una tarjeta para cada perfil
        for index, profile_name in enumerate(profiles):

            progress = self.get_profile_progress(
                profile_name
            )

            policies_accepted = progress[
                "policies_accepted"
            ]
            setup_step = progress["setup_step"]

            # Contenedor de la tarjeta
            card = QWidget()
            card.setObjectName("profileCard")

            card.setStyleSheet("""
                QWidget#profileCard {
                    background-color: #202938;
                    border: 1px solid #374151;
                    border-radius: 14px;
                }

                QWidget#profileCard QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)  

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(
                12, 28, 12, 8
            )
            card_layout.setSpacing(3)
            # Mantener agrupada la información del perfil experimental
            if profile_name == "Perfil experimental":
                card_layout.setAlignment(
                    Qt.AlignmentFlag.AlignTop
                )

            # Nombre del perfil
            name_label = QLabel(profile_name)
            name_label.setStyleSheet(
                "font-size: 24px; font-weight: bold;"
            )
            name_label.setWordWrap(True)

            # Estado del perfil
            is_active = (
                profile_name == self.current_profile
            )

            status_label = QLabel(
                "● Activo" if is_active
                else "○ Inactivo"
            )
            status_label.setStyleSheet(
                "font-size: 16px; color: "
                + ("#34D399;" if is_active else "#9CA3AF;")
            )

            # Información de preparación
            policies_label = QLabel(
                "Políticas: "
                + (
                    "Aceptadas" if policies_accepted
                    else "Pendientes"
                )
            )

            tutorial_label = QLabel(
                "Tutorial: "
                + (
                    "Completado" if setup_step >= 1
                    else "Pendiente"
                )
            )

            calibration_label = QLabel(
                "Calibración: "
                + (
                    "Completada" if setup_step >= 2
                    else "Pendiente"
                )
            )

            # Consultar la voz real guardada para este perfil
            voz_guardada = self.settings_store.value(
                f"voz_perfil/{profile_name}", None
            )

            voice_status_label = QLabel(
                "Selección de voz: "
                + (
                    "Completada"
                    if voz_guardada in ("Femenina", "Masculina")
                    else "Pendiente"
                )
            )

            voice_status_label.setStyleSheet(
                "font-size: 15px; color: #D1D5DB;"
            )

            voice_label = QLabel(
                "Voz seleccionada: "
                + (
                    voz_guardada
                    if voz_guardada in ("Femenina", "Masculina")
                    else "Pendiente"
                )
            )

            for label in [
                policies_label,
                tutorial_label,
                calibration_label,
                voice_label
            ]:
                label.setStyleSheet(
                    "font-size: 15px; color: #D1D5DB;"
                )

            card_layout.addWidget(name_label)
            card_layout.addWidget(status_label)
            card_layout.addSpacing(8)
            card_layout.addWidget(policies_label)
            card_layout.addWidget(tutorial_label)
            card_layout.addWidget(calibration_label)

            if profile_name != "Perfil experimental":
                card_layout.addWidget(voice_status_label)
                card_layout.addWidget(voice_label)

            # Permitir renombrar solo perfiles normales
            if profile_name != "Perfil experimental":

                rename_button = QPushButton(
                    "✏ Cambiar nombre"
                )
                rename_button.setCursor(
                    Qt.CursorShape.PointingHandCursor
                )
                rename_button.setStyleSheet("""
                    QPushButton {
                        background-color: #3730A3;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        padding: 10px;
                        font-size: 14px;
                        font-weight: bold;
                    }

                    QPushButton:hover {
                        background-color: #4338CA;
                    }
                """)

                rename_button.clicked.connect(
                    lambda checked=False, name=profile_name:
                        self.rename_profile(name)
                )

                card_layout.addSpacing(12)
                card_layout.addWidget(rename_button)
            # Botón para eliminar el perfil
            delete_button = QPushButton("Eliminar perfil")
            delete_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #7F1D1D;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                }

                QPushButton:hover {
                    background-color: #991B1B;
                }
            """)

            delete_button.clicked.connect(
                lambda checked=False, name=profile_name:
                    self.confirm_delete_profile(name)
            )

            if profile_name != "Perfil experimental":
                card_layout.addSpacing(8)
                card_layout.addWidget(delete_button)

            # Posición de la tarjeta: dos columnas
            row = index // 2
            column = index % 2

            self.profiles_cards_layout.addWidget(
                card, row, column
            )
        
    def confirm_delete_profile(self, profile_name):

        # Proteger el perfil experimental
        if profile_name == "Perfil experimental":
            QMessageBox.warning(
                self,
                "Perfil protegido",
                "El perfil experimental no se puede eliminar."
            )
            return

        # Consultar los perfiles realmente guardados
        profiles = self.settings_store.value(
            "profiles", [], type=list
        )

        # Evitar eliminar un perfil que ya no existe
        if profile_name not in profiles:
            QMessageBox.warning(
                self,
                "Perfil no encontrado",
                "Este perfil ya no existe."
            )
            self.refresh_manage_profiles_cards()
            return

        # Solicitar confirmación
        confirmation = QMessageBox(self)
        confirmation.setWindowTitle(
            "Confirmar eliminación"
        )

        confirmation.setIcon(
            QMessageBox.Icon.Warning
        )

        confirmation.setText(
            f"¿Deseas eliminar el perfil '{profile_name}'?"
        )

        confirmation.setInformativeText(
            "Se eliminará este perfil de VEXA.\n"
            "Esta acción no se puede deshacer."
        )

        confirmation.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel
        )

        confirmation.button(
            QMessageBox.StandardButton.Yes
        ).setText("Eliminar")

        confirmation.button(
            QMessageBox.StandardButton.Cancel
        ).setText("Cancelar")

        result = confirmation.exec()

        if result != QMessageBox.StandardButton.Yes:
            return

        # Quitar el perfil de la lista
        profiles.remove(profile_name)

        # Eliminar la voz guardada del perfil eliminado
        self.settings_store.remove(
            f"voz_perfil/{profile_name}"
        )

        # Guardar la lista actualizada
        self.settings_store.setValue(
            "profiles", profiles
        )

        # Consultar el progreso de todos los perfiles
        all_progress = self.settings_store.value(
            "profile_progress", {}
        )

        if not isinstance(all_progress, dict):
            all_progress = {}

        # Eliminar únicamente el progreso del perfil borrado
        if profile_name in all_progress:
            del all_progress[profile_name]

        # Guardar el progreso actualizado
        self.settings_store.setValue(
            "profile_progress", all_progress
        )

        # Comprobar si se eliminó el perfil activo
        deleted_active_profile = (
            self.current_profile == profile_name
        )

        if deleted_active_profile:

            self.current_profile = None
            self.voz_seleccionada = None
            self.settings_store.remove(
                "last_profile"
            )

            # Evitar regresar a la sesión eliminada
            self.profile_return_page = 0

        # Guardar los cambios
        self.settings_store.sync()

        # Actualizar la información visible
        self.update_active_profile_label()
        self.refresh_profiles()
        self.refresh_manage_profiles_cards()

        QMessageBox.information(
            self,
            "Perfil eliminado",
            f"El perfil '{profile_name}' "
            "se eliminó correctamente."
        )
        # Solicitar otro perfil si se eliminó el activo
        if deleted_active_profile:
            self.pages.setCurrentIndex(7)

    def return_from_profile_page(self):

        # Regresar a la pantalla desde donde se abrió
        return_page = getattr(
            self, "profile_return_page", 0
        )

        self.profile_return_page = 0
        self.pages.setCurrentIndex(return_page)

    def update_experimental_mode_button(self):

        if self.experimental_mode_enabled:
            self.btn_experimental_mode.setText(
                "Desactivar modo experimental"
            )
            self.btn_experimental_mode.setStyleSheet("""
                QPushButton {
                    background-color: #7F1D1D;
                    color: white;
                    border-radius: 10px;
                    padding: 10px;
                    font-weight: bold;
                }
            """)
        else:
            self.btn_experimental_mode.setText(
                "Activar modo experimental"
            )
            self.btn_experimental_mode.setStyleSheet("""
                QPushButton {
                    background-color: #065F46;
                    color: white;
                    border-radius: 10px;
                    padding: 10px;
                    font-weight: bold;
                }
            """)

    def mostrar_dialogo_registrar_sus(self):
        participantes = obtener_participantes()

        if not participantes:
            QMessageBox.information(
                self,
                "Sin participantes",
                "Todavía no hay participantes registrados."
            )
            return

        opciones = [
            participante["codigo"]
            for participante in participantes
        ]

        participantes_por_codigo = {
            participante["codigo"]: participante["id"]
            for participante in participantes
        }

        opcion, aceptado = QInputDialog.getItem(
            self,
            "Registrar satisfacción SUS",
            "Selecciona el participante:",
            opciones,
            0,
            False
        )

        if not aceptado:
            return

        puntuacion, aceptado = QInputDialog.getDouble(
            self,
            "Puntuación SUS",
            "Introduce la puntuación SUS final (0 a 100):",
            0.0,
            0.0,
            100.0,
            2
        )

        if not aceptado:
            return

        try:
            guardar_puntuacion_sus(
                participantes_por_codigo[opcion],
                puntuacion
            )

        except (ValueError, sqlite3.Error) as error:
            QMessageBox.warning(
                self,
                "Error al guardar SUS",
                str(error)
            )
            return

        QMessageBox.information(
            self,
            "SUS registrado",
            f"Puntuación SUS guardada: {puntuacion:.2f} / 100"
        )
    
    def toggle_experimental_mode(self):
        # No desactivar el modo si el perfil exp está activo
        if (
            self.experimental_mode_enabled
            and self.current_profile == "Perfil experimental"
        ):
            QMessageBox.warning(
                self,
                "Perfil experimental activo",
                "No puedes desactivar el modo experimental\n"
                "mientras ese perfil esté en uso.\n\n"
                "Primero cambia a un perfil normal."
            )
            return

        # Cambiar el estado del modo experimental
        self.experimental_mode_enabled = (
            not self.experimental_mode_enabled
        )

        # Guardar el estado
        self.settings_store.setValue(
            "experimental_mode_enabled",
            self.experimental_mode_enabled
        )
        self.settings_store.sync()

        # Actualizar el botón y los perfiles visibles
        self.update_experimental_mode_button()
        self.refresh_profiles()

# ==================================================
# INICIAR APLICACIÓN
if __name__ == "__main__":
    inicializar_base_datos()
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QWidget {
            background-color: #111827;
            color: #F9FAFB;
            font-family: Arial;
        }

        QPushButton {
            background-color: #1F2937;
            color: #F9FAFB;
            border: none;
            border-radius: 8px;
            padding: 12px;
            font-size: 15px;
        }

        QPushButton:hover {
            background-color: #374151;
        }

        QPushButton:pressed {
            background-color: #4B5563;
        }
    """)



    window = VexaWindow()
    window.show()

    sys.exit(app.exec())



