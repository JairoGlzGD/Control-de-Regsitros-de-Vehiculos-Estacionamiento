# Proyecto Registro Vehículos — Emisión y Lectura de Folios (QR)

Este repositorio contiene una versión del sistema de estacionamiento que genera un folio numérico para cada ticket y opcionalmente crea una imagen con código QR para imprimir o guardar.

Características añadidas:
- Generación de QR al registrar la entrada (si `qrcode` y `Pillow` están instalados).
- Visualización y opción de guardar la imagen del ticket (QR).
- Escaneo de QR desde imagen (requiere `pyzbar`) o desde webcam (`pyzbar` + `opencv-python` + `numpy`).
- Si las librerías opcionales no están instaladas, el sistema sigue funcionando con entrada manual de folio.

Instalación (opcional):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ejecución:

```bash
python3 main.py
```

Notas:
- Si no instala las dependencias opcionales, la funcionalidad de generar/leer QR quedará deshabilitada y el sistema seguirá funcionando con entrada manual de folio.
- Para imprimir el ticket QR puede usar la opción de guardar en la ventana emergente y luego imprimir desde su visor de imágenes.
