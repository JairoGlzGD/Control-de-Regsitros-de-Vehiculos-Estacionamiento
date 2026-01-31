import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import math
import os
import sys

# --- LIBRERÍAS EXTERNAS ---
from PIL import Image, ImageTk
import barcode
from barcode.writer import ImageWriter

# --- CONFIGURACIÓN ---
DB_NAME = "estacionamiento.db"
TOLERANCIA = 10  # Minutos de tolerancia global

def inicializar_db():
    """Crea tablas de tickets y tarifas si no existen."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla Tickets
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        folio INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_entrada TEXT,
        fecha_salida TEXT,
        monto_total REAL,
        estado TEXT,
        tipo_vehiculo TEXT
    )
    ''')
    
    # Tabla Tarifas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tarifas (
        tipo_vehiculo TEXT PRIMARY KEY,
        costo_hora REAL,
        costo_fraccion REAL
    )
    ''')
    
    # Insertar tarifas por defecto
    cursor.execute("SELECT count(*) FROM tarifas")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO tarifas VALUES ('Auto', 20.0, 10.0)")
        cursor.execute("INSERT INTO tarifas VALUES ('Moto', 10.0, 5.0)")
        print("Tarifas iniciales creadas.")
        
    conn.commit()
    conn.close()

class EstacionamientoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Estacionamiento v1.0")
        self.root.geometry("1100x750")
        
        style = ttk.Style()
        style.configure("Big.TButton", font=("Segoe UI", 14, "bold"), padding=10)
        style.configure("Big.TLabel", font=("Segoe UI", 12))
        
        # === BARRA SUPERIOR ===
        frame_top = tk.Frame(root, bg="#ddd", height=50)
        frame_top.pack(fill="x")
        
        tk.Label(frame_top, text=" SISTEMA DE CONTROL DE ACCESO ", bg="#ddd", font=("Segoe UI", 14, "bold")).pack(side="left", padx=20)
        
        # Botones de la barra superior
        btn_reportes = tk.Button(frame_top, text="📊 Ver Reportes", bg="#b3e5fc", command=self.abrir_reportes)
        btn_reportes.pack(side="right", padx=10, pady=5)
        
        btn_config = tk.Button(frame_top, text="⚙️ Tarifas", bg="#eee", command=self.abrir_configuracion)
        btn_config.pack(side="right", padx=10, pady=5)

        # === CONTENEDOR PRINCIPAL ===
        main_container = tk.Frame(root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # === PANEL ENTRADA (Izquierda) ===
        frame_entrada = ttk.LabelFrame(main_container, text=" ENTRADA ", padding=20)
        frame_entrada.pack(side="left", fill="both", expand=True, padx=10)
        
        ttk.Label(frame_entrada, text="Seleccione Tipo:", style="Big.TLabel").pack(pady=10)
        
        ttk.Button(frame_entrada, text="🚘 ENTRADA AUTO", style="Big.TButton", 
                   command=lambda: self.generar_entrada("Auto")).pack(fill="x", pady=5)
        
        ttk.Button(frame_entrada, text="🏍️ ENTRADA MOTO", style="Big.TButton", 
                   command=lambda: self.generar_entrada("Moto")).pack(fill="x", pady=5)
        
        self.lbl_imagen_ticket = ttk.Label(frame_entrada, text="[Vista Previa]", background="#f0f0f0", anchor="center")
        self.lbl_imagen_ticket.pack(pady=20, fill="x", ipady=20)
        
        self.lbl_info_ticket = ttk.Label(frame_entrada, text="", font=("Segoe UI", 12, "bold"), foreground="#0056b3")
        self.lbl_info_ticket.pack(pady=5)

        # === PANEL SALIDA (Derecha) ===
        frame_salida = ttk.LabelFrame(main_container, text=" SALIDA Y COBRO ", padding=20)
        frame_salida.pack(side="right", fill="both", expand=True, padx=10)
        
        ttk.Label(frame_salida, text="Escanear Código:", style="Big.TLabel").pack(pady=10)
        
        self.entry_folio = ttk.Entry(frame_salida, font=("Segoe UI", 24), justify='center')
        self.entry_folio.pack(fill="x", pady=10)
        self.entry_folio.bind('<Return>', self.calcular_cobro)
        self.entry_folio.focus()
        
        ttk.Button(frame_salida, text="🔍 Buscar Manualmente", command=self.calcular_cobro).pack(pady=5)
        
        self.lbl_resultado_cobro = ttk.Label(frame_salida, text="Listo para escanear...", 
                                             font=("Consolas", 14), background="black", foreground="#00ff00", anchor="center")
        self.lbl_resultado_cobro.pack(fill="both", expand=True, pady=20)
        
        self.btn_pagar = ttk.Button(frame_salida, text="💰 COBRAR", style="Big.TButton", 
                                    state="disabled", command=self.procesar_pago)
        self.btn_pagar.pack(fill="x", pady=10)
        
        self.datos_pago_pendiente = None

    def generar_entrada(self, tipo):
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("INSERT INTO tickets (fecha_entrada, estado, tipo_vehiculo) VALUES (?, ?, ?)", 
                           (fecha_actual, 'Pendiente', tipo))
            conn.commit()
            folio_id = cursor.lastrowid
            conn.close()
            
            # Generar Barcode
            nombre_archivo = "ticket_actual"
            codigo_clase = barcode.get_barcode_class('code128')
            codigo = codigo_clase(str(folio_id), writer=ImageWriter())
            
            # --- FIX PARA EL ERROR 'CANNOT OPEN RESOURCE' EN EXE ---
            # Desactivamos el texto dentro de la imagen del código de barras
            # para evitar que busque fuentes (letras) que no existen en el EXE.
            codigo.save(nombre_archivo, options={"write_text": False})
            
            # Mostrar
            archivo_completo = f"{nombre_archivo}.png"
            if os.path.exists(archivo_completo):
                img = Image.open(archivo_completo)
                img = img.resize((380, 100), Image.Resampling.LANCZOS) # Ajusté altura ya que sin texto es más chaparrito
                img_tk = ImageTk.PhotoImage(img)
                self.lbl_imagen_ticket.config(image=img_tk)
                self.lbl_imagen_ticket.image = img_tk
                
                # Mostramos el folio en texto grande abajo, así que no hace falta en las barras
                self.lbl_info_ticket.config(text=f"Folio: {folio_id}\nVehículo: {tipo}\nHora: {fecha_actual[-8:]}")
                
                if sys.platform == "win32":
                    try: os.startfile(archivo_completo, "print") 
                    except: os.startfile(archivo_completo)
            else:
                messagebox.showerror("Error", "No se generó el ticket visual.")
        except Exception as e:
            # Muestra el error exacto si vuelve a fallar
            messagebox.showerror("Error", f"Fallo al generar entrada:\n{e}")

    def calcular_cobro(self, event=None):
        folio_texto = self.entry_folio.get().strip()
        if not folio_texto.isdigit():
            messagebox.showerror("Error", "Código inválido")
            self.limpiar_salida()
            return

        folio = int(folio_texto)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT fecha_entrada, estado, tipo_vehiculo FROM tickets WHERE folio = ?", (folio,))
        ticket = cursor.fetchone()
        
        if not ticket:
            messagebox.showerror("Error", "Ticket no encontrado")
            conn.close(); self.limpiar_salida(); return
            
        fecha_str, estado, tipo_vehiculo = ticket
        
        if estado == 'Pagado':
            messagebox.showinfo("Aviso", "Ticket YA PAGADO.")
            conn.close(); self.limpiar_salida(); return

        cursor.execute("SELECT costo_hora, costo_fraccion FROM tarifas WHERE tipo_vehiculo = ?", (tipo_vehiculo,))
        tarifa = cursor.fetchone()
        conn.close()
        
        if not tarifa:
            messagebox.showerror("Error", f"No hay tarifa para {tipo_vehiculo}")
            return
            
        tarifa_hora, tarifa_fraccion = tarifa
        entrada = datetime.datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
        salida = datetime.datetime.now()
        
        duracion = salida - entrada
        minutos = math.ceil(duracion.total_seconds() / 60)
        
        total = 0.0
        detalle = ""
        
        if minutos <= TOLERANCIA:
            total = 0.0; detalle = "Tiempo de Tolerancia (Gratis)"
        else:
            total += tarifa_hora
            restante = minutos - 60
            if restante > 0:
                fracciones = math.ceil(restante / 15)
                total += fracciones * tarifa_fraccion
                detalle = f"1h (${tarifa_hora}) + {fracciones} frac. (${tarifa_fraccion} c/u)"
            else:
                detalle = f"1 Hora (${tarifa_hora})"

        texto = f"FOLIO: {folio} ({tipo_vehiculo})\nMinutos: {minutos}\nTOTAL: ${total:.2f}\n----------------\n{detalle}"
        self.lbl_resultado_cobro.config(text=texto)
        self.btn_pagar.config(state="normal")
        self.datos_pago_pendiente = {"folio": folio, "salida": salida.strftime("%Y-%m-%d %H:%M:%S"), "total": total}

    def procesar_pago(self):
        if self.datos_pago_pendiente:
            d = self.datos_pago_pendiente
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE tickets SET fecha_salida=?, monto_total=?, estado='Pagado' WHERE folio=?",
                           (d['salida'], d['total'], d['folio']))
            conn.commit()
            conn.close()
            messagebox.showinfo("Cobrado", "Pago registrado.")
            self.limpiar_salida()

    def limpiar_salida(self):
        self.entry_folio.delete(0, tk.END)
        self.lbl_resultado_cobro.config(text="Listo para escanear...")
        self.btn_pagar.config(state="disabled")
        self.datos_pago_pendiente = None
        self.entry_folio.focus()

    def abrir_configuracion(self):
        ventana_conf = tk.Toplevel(self.root)
        ventana_conf.title("Configurar Tarifas")
        ventana_conf.geometry("400x300")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tarifas")
        tarifas_actuales = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        conn.close()
        
        entries = {}
        for vehiculo in ["Auto", "Moto"]:
            frame = tk.LabelFrame(ventana_conf, text=f" Tarifa {vehiculo} ", padx=10, pady=5)
            frame.pack(fill="x", padx=20, pady=5)
            vals = tarifas_actuales.get(vehiculo, (0.0, 0.0))
            
            tk.Label(frame, text="1ra Hora: $").grid(row=0, column=0)
            e_hora = tk.Entry(frame, width=10); e_hora.insert(0, vals[0]); e_hora.grid(row=0, column=1)
            tk.Label(frame, text="Fracción: $").grid(row=0, column=2)
            e_frac = tk.Entry(frame, width=10); e_frac.insert(0, vals[1]); e_frac.grid(row=0, column=3)
            entries[vehiculo] = (e_hora, e_frac)
            
        def guardar_cambios():
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                for vehiculo, (e_h, e_f) in entries.items():
                    cursor.execute("UPDATE tarifas SET costo_hora=?, costo_fraccion=? WHERE tipo_vehiculo=?", 
                                   (float(e_h.get()), float(e_f.get()), vehiculo))
                conn.commit(); conn.close()
                messagebox.showinfo("Éxito", "Tarifas actualizadas.")
                ventana_conf.destroy()
            except ValueError:
                messagebox.showerror("Error", "Ingrese solo números.")

        tk.Button(ventana_conf, text="💾 GUARDAR", bg="#4CAF50", fg="white", command=guardar_cambios).pack(pady=20)

    # === MÓDULO: REPORTES ===
    def abrir_reportes(self):
        rep_win = tk.Toplevel(self.root)
        rep_win.title("Reporte de Registros y Ventas")
        rep_win.geometry("900x600")
        
        frame_filtros = ttk.LabelFrame(rep_win, text=" Filtros de Búsqueda ", padding=10)
        frame_filtros.pack(fill="x", padx=10, pady=5)
        
        hoy = datetime.datetime.now()
        
        ttk.Label(frame_filtros, text="Año:").pack(side="left", padx=(0,5))
        cb_anio = ttk.Combobox(frame_filtros, values=["Todos"] + [str(y) for y in range(hoy.year, 2023, -1)], width=6, state="readonly")
        cb_anio.set(str(hoy.year))
        cb_anio.pack(side="left", padx=(0,15))
        
        ttk.Label(frame_filtros, text="Mes:").pack(side="left", padx=(0,5))
        meses = ["Todos"] + [f"{i:02d}" for i in range(1, 13)]
        cb_mes = ttk.Combobox(frame_filtros, values=meses, width=5, state="readonly")
        cb_mes.set("Todos")
        cb_mes.pack(side="left", padx=(0,15))
        
        ttk.Label(frame_filtros, text="Día:").pack(side="left", padx=(0,5))
        dias = ["Todos"] + [f"{i:02d}" for i in range(1, 32)]
        cb_dia = ttk.Combobox(frame_filtros, values=dias, width=5, state="readonly")
        cb_dia.set("Todos")
        cb_dia.pack(side="left", padx=(0,15))

        ttk.Label(frame_filtros, text="Hora:").pack(side="left", padx=(0,5))
        horas = ["Todos"] + [f"{i:02d}" for i in range(0, 24)]
        cb_hora = ttk.Combobox(frame_filtros, values=horas, width=5, state="readonly")
        cb_hora.set("Todos") 
        cb_hora.pack(side="left", padx=(0,15))
        
        columns = ("folio", "entrada", "salida", "vehiculo", "monto", "estado")
        tree = ttk.Treeview(rep_win, columns=columns, show="headings")
        tree.heading("folio", text="Folio")
        tree.heading("entrada", text="Fecha Entrada")
        tree.heading("salida", text="Fecha Salida")
        tree.heading("vehiculo", text="Tipo")
        tree.heading("monto", text="Monto")
        tree.heading("estado", text="Estado")
        
        tree.column("folio", width=60, anchor="center")
        tree.column("entrada", width=150, anchor="center")
        tree.column("salida", width=150, anchor="center")
        tree.column("vehiculo", width=80, anchor="center")
        tree.column("monto", width=80, anchor="e")
        tree.column("estado", width=80, anchor="center")
        
        scrollbar = ttk.Scrollbar(rep_win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        lbl_total = tk.Label(rep_win, text="Total Ventas: $0.00", font=("Arial", 16, "bold"), fg="green")
        lbl_total.pack(pady=10)
        
        def consultar_db():
            for row in tree.get_children(): tree.delete(row)
            anio, mes, dia, hora = cb_anio.get(), cb_mes.get(), cb_dia.get(), cb_hora.get()
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            query = "SELECT folio, fecha_entrada, fecha_salida, tipo_vehiculo, monto_total, estado FROM tickets WHERE 1=1"
            params = []
            
            if anio != "Todos": query += " AND strftime('%Y', fecha_entrada) = ?"; params.append(anio)
            if mes != "Todos": query += " AND strftime('%m', fecha_entrada) = ?"; params.append(mes)
            if dia != "Todos": query += " AND strftime('%d', fecha_entrada) = ?"; params.append(dia)
            if hora != "Todos": query += " AND strftime('%H', fecha_entrada) = ?"; params.append(hora)
                
            query += " ORDER BY folio DESC"
            cursor.execute(query, params)
            registros = cursor.fetchall()
            conn.close()
            
            suma_ventas = 0.0
            for r in registros:
                folio_val, ent, sal, tipo, monto, est = r
                monto_visual = f"${monto:.2f}" if monto else "$0.00"
                salida_visual = sal if sal else "---"
                tree.insert("", "end", values=(folio_val, ent, salida_visual, tipo, monto_visual, est))
                if est == "Pagado" and monto: suma_ventas += monto
            lbl_total.config(text=f"Total Ventas (Filtrado): ${suma_ventas:.2f}")

        btn_buscar = tk.Button(frame_filtros, text="🔍 CONSULTAR", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=consultar_db)
        btn_buscar.pack(side="left", padx=20)
        consultar_db()

if __name__ == "__main__":
    try:
        inicializar_db()
        root = tk.Tk()
        app = EstacionamientoApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error Fatal", f"El programa no pudo iniciar:\n{str(e)}")
