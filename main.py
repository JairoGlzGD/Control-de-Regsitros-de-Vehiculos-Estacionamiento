import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import datetime
import math
import os

# Dependencias opcionales: qrcode (generar QR), Pillow (manejo de imágenes), pyzbar/opencv (lectura)
try:
    import qrcode
    from PIL import Image, ImageTk
    QR_AVAILABLE = True
except Exception:
    qrcode = None
    Image = None
    ImageTk = None
    QR_AVAILABLE = False

try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_AVAILABLE = True
except Exception:
    zbar_decode = None
    PYZBAR_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except Exception:
    cv2 = None
    np = None
    CV2_AVAILABLE = False

# --- CONFIGURACIÓN DE BASE DE DATOS ---
DB_NAME = "estacionamiento.db"

def inicializar_db():
    """Crea las tablas necesarias si no existen."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla Tarifas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tarifas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descripcion TEXT,
        costo_hora REAL,
        costo_fraccion REAL
    )
    ''')
    
    # Tabla Tickets
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        folio INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_entrada TEXT,
        fecha_salida TEXT,
        monto_total REAL,
        estado TEXT, -- 'Pendiente', 'Pagado'
        tipo_vehiculo TEXT
    )
    ''')
    
    # Insertar tarifas por defecto si está vacía
    cursor.execute("SELECT count(*) FROM tarifas")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO tarifas (descripcion, costo_hora, costo_fraccion) VALUES ('Auto', 20.0, 10.0)")
        cursor.execute("INSERT INTO tarifas (descripcion, costo_hora, costo_fraccion) VALUES ('Moto', 10.0, 5.0)")
        print("Tarifas iniciales creadas.")
    
    conn.commit()
    conn.close()

# --- LÓGICA DEL SISTEMA ---

class EstacionamientoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Estacionamiento - Control de Caja")
        self.root.geometry("800x600")
        
        # Estilos visuales
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 12), padding=10)
        style.configure("TLabel", font=("Helvetica", 11))
        
        # --- GUI: PANEL IZQUIERDO (ENTRADA) ---
        frame_entrada = ttk.LabelFrame(root, text=" ENTRADA DE VEHÍCULOS ", padding=20)
        frame_entrada.place(x=20, y=20, width=370, height=500)
        
        ttk.Label(frame_entrada, text="Seleccione Tipo de Vehículo:").pack(pady=10)
        
        ttk.Button(frame_entrada, text="🚗 AUTOMÓVIL (Entrada)", 
                   command=lambda: self.registrar_entrada("Auto")).pack(fill="x", pady=5)
        
        ttk.Button(frame_entrada, text="🏍️ MOTOCICLETA (Entrada)", 
                   command=lambda: self.registrar_entrada("Moto")).pack(fill="x", pady=5)

        self.lbl_ultimo_ticket = ttk.Label(frame_entrada, text="Último ticket: Ninguno", foreground="blue")
        self.lbl_ultimo_ticket.pack(pady=20)

        # --- GUI: PANEL DERECHO (SALIDA Y COBRO) ---
        frame_salida = ttk.LabelFrame(root, text=" SALIDA Y COBRO ", padding=20)
        frame_salida.place(x=410, y=20, width=370, height=500)
        
        ttk.Label(frame_salida, text="Ingresa Folio del Ticket:").pack(pady=5)
        
        self.entry_folio = ttk.Entry(frame_salida, font=("Helvetica", 14), justify='center')
        self.entry_folio.pack(pady=5)

        # Botón para escanear QR / código de barras (intenta webcam, si no disponible, permite seleccionar imagen)
        ttk.Button(frame_salida, text="📷 Escanear QR/Código", command=self.escanear_qr).pack(fill="x", pady=5)

        ttk.Button(frame_salida, text="🔍 Calcular Cobro", command=self.calcular_cobro).pack(fill="x", pady=10)
        
        # Area de resultados
        self.lbl_info_cobro = ttk.Label(frame_salida, text="", justify="center", background="#e1e1e1", relief="sunken")
        self.lbl_info_cobro.pack(fill="both", expand=True, pady=10)
        
        self.btn_pagar = ttk.Button(frame_salida, text="💰 CONFIRMAR PAGO Y SALIDA", state="disabled", command=self.procesar_pago)
        self.btn_pagar.pack(fill="x", pady=10)

        # Variables temporales para el cobro actual
        self.cobro_actual = None # Guardará {folio, total, fecha_salida}

    def registrar_entrada(self, tipo_vehiculo):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        fecha_entrada = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("INSERT INTO tickets (fecha_entrada, estado, tipo_vehiculo) VALUES (?, ?, ?)", 
                       (fecha_entrada, 'Pendiente', tipo_vehiculo))
        conn.commit()
        
        folio = cursor.lastrowid
        conn.close()
        self.lbl_ultimo_ticket.config(text=f"Ticket Generado: #{folio}\nHora: {fecha_entrada[-8:]}")

        # Generar QR (si está disponible). Se guarda en carpeta tickets_qr
        qr_path = None
        if QR_AVAILABLE:
            try:
                qr_path = self.generar_qr(folio)
            except Exception:
                qr_path = None

        # Mostrar información al usuario y, si existe QR, mostrar opción para guardar/imprimir
        msg = f"Entrada Registrada.\n\nFolio: {folio}\nVehículo: {tipo_vehiculo}"
        if qr_path:
            msg += "\n\nSe generó el código QR para el ticket."

        messagebox.showinfo("Ticket Generado", msg)

        if qr_path and QR_AVAILABLE:
            try:
                self.mostrar_qr_popup(qr_path, folio)
            except Exception:
                pass

    # ------------------ FUNCIONES QR / BARRA ------------------
    def generar_qr(self, folio: int) -> str:
        """Genera un QR con el folio y lo guarda en tickets_qr/{folio}.png. Retorna la ruta."""
        if not QR_AVAILABLE:
            raise RuntimeError("Librería qrcode/Pillow no disponible")

        out_dir = os.path.join(os.path.dirname(__file__), "tickets_qr")
        os.makedirs(out_dir, exist_ok=True)

        data = str(folio)
        qr = qrcode.QRCode(version=2, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        path = os.path.join(out_dir, f"ticket_{folio}.png")
        img.save(path)
        return path

    def mostrar_qr_popup(self, img_path: str, folio: int):
        """Muestra una ventana con el QR y opción para guardar/imprimir."""
        if not Image or not ImageTk:
            return

        popup = tk.Toplevel(self.root)
        popup.title(f"QR - Ticket #{folio}")

        img = Image.open(img_path)
        img_thumbnail = img.copy()
        img_thumbnail.thumbnail((300, 300))
        tk_img = ImageTk.PhotoImage(img_thumbnail)

        lbl = ttk.Label(popup, image=tk_img)
        lbl.image = tk_img
        lbl.pack(padx=10, pady=10)

        def guardar_como():
            dest = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image","*.png")], initialfile=f"ticket_{folio}.png")
            if dest:
                img.save(dest)
                messagebox.showinfo("Guardado", f"Imagen guardada en: {dest}")

        ttk.Button(popup, text="Guardar/Imprimir...", command=guardar_como).pack(pady=5)
        ttk.Button(popup, text="Cerrar", command=popup.destroy).pack(pady=5)

    def escanear_qr(self):
        """Intenta escanear desde webcam (si está disponible) o pedir al usuario seleccionar una imagen."""
        # Priorizar webcam si está disponible
        if CV2_AVAILABLE and PYZBAR_AVAILABLE:
            try:
                folio = self._scan_from_webcam()
                if folio:
                    self.entry_folio.delete(0, tk.END)
                    self.entry_folio.insert(0, str(folio))
                    self.calcular_cobro()
                    return
            except Exception:
                pass

        if PYZBAR_AVAILABLE:
            # Abrir selector de archivo
            try:
                folio = self._scan_from_file()
                if folio:
                    self.entry_folio.delete(0, tk.END)
                    self.entry_folio.insert(0, str(folio))
                    self.calcular_cobro()
                    return
            except Exception:
                pass

        messagebox.showwarning("Escaneo no disponible", "No se encontraron librerías para escanear QR (pyzbar/opencv). Ingrese el folio manualmente.")

    def _scan_from_file(self):
        path = filedialog.askopenfilename(title="Seleccionar imagen con QR/Código", filetypes=[("Imagen","*.png;*.jpg;*.jpeg;*.bmp;*.gif" )])
        if not path:
            return None

        if not PYZBAR_AVAILABLE:
            raise RuntimeError("pyzbar no disponible")

        img = Image.open(path)
        decoded = zbar_decode(img)
        if not decoded:
            messagebox.showerror("No detectado", "No se encontró un código válido en la imagen seleccionada.")
            return None

        # Tomar el primer resultado
        data = decoded[0].data.decode('utf-8')
        if data.isdigit():
            return int(data)
        return None

    def _scan_from_webcam(self):
        if not CV2_AVAILABLE or not PYZBAR_AVAILABLE:
            raise RuntimeError("OpenCV o pyzbar no disponibles")

        cap = cv2.VideoCapture(0)
        messagebox.showinfo("Webcam", "Se abrirá la cámara. Presione 'q' para cancelar.")
        folio = None
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                decoded = zbar_decode(gray)
                for d in decoded:
                    try:
                        data = d.data.decode('utf-8')
                        if data.isdigit():
                            folio = int(data)
                            # Mostrar rectángulo y romper
                            pts = d.polygon
                            if len(pts) > 2:
                                pts = [(p.x, p.y) for p in pts]
                                cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0,255,0), 2)
                            break
                    except Exception:
                        continue

                cv2.imshow('Escaneo QR - Presione q para salir', frame)
                if folio is not None:
                    cv2.waitKey(500)
                    break
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        if folio is None:
            messagebox.showinfo("Resultado", "No se detectó ningún folio durante el escaneo.")
        return folio

    def calcular_cobro(self):
        folio_txt = self.entry_folio.get()
        if not folio_txt.isdigit():
            messagebox.showerror("Error", "Ingrese un número de folio válido")
            return

        folio = int(folio_txt)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Buscar ticket
        cursor.execute("SELECT fecha_entrada, estado, tipo_vehiculo FROM tickets WHERE folio = ?", (folio,))
        ticket = cursor.fetchone()
        
        if not ticket:
            messagebox.showerror("Error", "Ticket no encontrado")
            conn.close()
            return
            
        fecha_entrada_str, estado, tipo_vehiculo = ticket
        
        if estado == 'Pagado':
            messagebox.showwarning("Aviso", "Este ticket ya fue pagado anteriormente.")
            conn.close()
            return

        # Buscar tarifas
        cursor.execute("SELECT costo_hora, costo_fraccion FROM tarifas WHERE descripcion = ?", (tipo_vehiculo,))
        tarifa = cursor.fetchone() # (20.0, 10.0)
        conn.close()

        # CALCULO DE TIEMPO Y DINERO
        fmt = "%Y-%m-%d %H:%M:%S"
        entrada = datetime.datetime.strptime(fecha_entrada_str, fmt)
        salida = datetime.datetime.now()
        
        # Para pruebas: Descomenta la siguiente línea para simular que pasaron 2 horas y media
        # salida = entrada + datetime.timedelta(hours=2, minutes=35) 
        
        diferencia = salida - entrada
        minutos_totales = int(diferencia.total_seconds() / 60)
        
        # Reglas de cobro (Ejemplo simple)
        costo_hora = tarifa[0]
        costo_fraccion = tarifa[1]
        
        if minutos_totales <= 15: # Tolerancia
            total = 0
            detalle = "Tiempo de tolerancia (Gratis)"
        else:
            # Primera hora se cobra completa
            horas = 1
            resto_minutos = minutos_totales - 60
            
            # Fracciones adicionales
            fracciones = 0
            if resto_minutos > 0:
                fracciones = math.ceil(resto_minutos / 15) # Cada 15 min es una fracción
                
            total = costo_hora + (fracciones * costo_fraccion)
            detalle = f"{minutos_totales} min totales.\n1 Hora + {fracciones} Fracciones."

        # Mostrar en pantalla
        texto_resultado = f"Folio: {folio} | {tipo_vehiculo}\n"
        texto_resultado += f"Entrada: {entrada.strftime('%H:%M')}\n"
        texto_resultado += f"Salida: {salida.strftime('%H:%M')}\n"
        texto_resultado += f"\n----------------\nTOTAL A PAGAR:\n${total:.2f}\n----------------\n"
        texto_resultado += f"({detalle})"
        
        self.lbl_info_cobro.config(text=texto_resultado)
        self.btn_pagar.config(state="normal")
        
        # Guardar datos para procesar el pago
        self.cobro_actual = {
            "folio": folio,
            "total": total,
            "fecha_salida": salida.strftime(fmt)
        }

    def procesar_pago(self):
        if not self.cobro_actual:
            return
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tickets 
            SET fecha_salida = ?, monto_total = ?, estado = 'Pagado'
            WHERE folio = ?
        ''', (self.cobro_actual["fecha_salida"], self.cobro_actual["total"], self.cobro_actual["folio"]))
        
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Éxito", "Pago registrado correctamente.\nLa barrera de salida se ha levantado.")
        
        # Limpiar formulario
        self.entry_folio.delete(0, tk.END)
        self.lbl_info_cobro.config(text="")
        self.btn_pagar.config(state="disabled")
        self.cobro_actual = None

if __name__ == "__main__":
    inicializar_db() # Crea la BD si no existe
    root = tk.Tk()
    app = EstacionamientoApp(root)
    root.mainloop()