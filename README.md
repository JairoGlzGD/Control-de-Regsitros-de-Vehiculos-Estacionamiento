🚗 Sistema de Gestión de Estacionamiento (Parking System)

Un sistema de punto de venta y control de acceso para estacionamientos desarrollado en Python. Permite gestionar entradas y salidas mediante códigos de barras, calcular tarifas automáticamente por tiempo y generar reportes financieros.

Diseñado para ser ligero, portátil (SQLite) y convertible a un ejecutable nativo de Windows (.exe).

📋 Características Principales

Control de Acceso: Generación de tickets de entrada con Código de Barras (Code128).

Soporte Multi-Vehículo: Tarifas diferenciadas para Automóviles y Motocicletas.

Cálculo Automático: Algoritmo que calcula el costo basado en horas y fracciones (15 min), con tiempo de tolerancia configurable.

Integración con Hardware:

Compatible con Lectores de Código de Barras (USB).

Impresión automática de tickets (usa la impresora predeterminada de Windows).

Módulo de Administración:

Configuración de Tarifas: Ajuste de precios sin tocar el código.

Reportes y Consultas: Visualización de historial y corte de caja con filtros por Año, Mes, Día y Hora.

Persistencia de Datos: Uso de SQLite para una base de datos local y segura.

🛠️ Tecnologías Utilizadas

Lenguaje: Python 3.x

Interfaz Gráfica (GUI): Tkinter (Nativo)

Base de Datos: SQLite3

Generación de Imágenes: Pillow (PIL)

Códigos de Barras: python-barcode

🚀 Instalación y Ejecución (Código Fuente)

Si deseas correr el proyecto desde el código fuente o modificarlo:

Clonar el repositorio:

git clone https://github.com/JairoGlzGD/Control-de-Regsitros-de-Vehiculos-Estacionamiento.git
cd sistema-estacionamiento


Instalar dependencias:
Necesitas instalar las librerías para el manejo de imágenes y códigos de barras.

pip install pillow python-barcode


Ejecutar la aplicación:

python main.py


📦 Generar Ejecutable (.exe) para Windows

Este proyecto está optimizado para ser compilado con PyInstaller. Se incluye una corrección específica para evitar errores de fuentes (fonts) al generar los códigos de barras en el ejecutable.

Instala PyInstaller:

pip install pyinstaller


Ejecuta el comando de compilación:

pyinstaller --noconsole --onefile --windowed main.py


El archivo final main.exe aparecerá en la carpeta dist/. Puedes llevar este archivo a cualquier computadora con Windows (no requiere instalar Python).

📖 Cómo Usar

1. Entrada de Vehículos

Selecciona el tipo de vehículo (Auto o Moto).

El sistema generará un ticket visual en pantalla y lo enviará a la impresora predeterminada.

El ticket incluye un código de barras único.

2. Salida y Cobro

Posiciónate en el campo "Escanear Código".

Usa el lector de códigos de barras sobre el ticket (o escribe el folio y presiona Enter).

El sistema calculará el tiempo total y el monto a pagar según las reglas de negocio (tolerancia, costo por hora, costo por fracción).

Presiona "Cobrar" para registrar la salida y liberar la barrera.

3. Reportes y Configuración

Usa el botón "⚙️ Tarifas" para cambiar los precios por hora/fracción.

Usa el botón "📊 Ver Reportes" para ver cuánto dinero ha ingresado en el día, mes o año específico.

🐛 Solución de Problemas Comunes

Error: "Cannot open resource" al generar el ticket en el .exe

Este proyecto ya incluye el parche para este error. La función codigo.save() utiliza options={"write_text": False} para evitar buscar fuentes del sistema que no se empaquetan con PyInstaller.

La impresora no imprime automáticamente

El sistema usa os.startfile(archivo, "print"). Asegúrate de tener una Impresora Predeterminada configurada en el Panel de Control de Windows.

📄 Licencia

Este proyecto es de uso libre para fines educativos o comerciales.
