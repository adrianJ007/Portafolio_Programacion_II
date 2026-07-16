import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import sys
import json
from datetime import datetime
import random

# ============================================================================
# 1. MODELOS (Problema 1)
# ============================================================================

class Estudiante:
    def __init__(self, nombre, cedula, tipo_grupo):
        self.nombre = nombre
        self.cedula = cedula 
        self.tipo_grupo = tipo_grupo
        self.notas = {}
        self.nota_final = 0.0

    def calcular_nota_final(self, porcentajes):
        total = 0
        for actividad, porcentaje in porcentajes.items():
            nota = self.notas.get(actividad, 0)
            total += nota * (porcentaje / 100)
        self.nota_final = total
        return total
    
    def exportar_notas(self, asignatura_nombre, profesor_nombre, porcentajes):
        from datetime import datetime
        contenido = f"""
{'='*60}
            REPORTE INDIVIDUAL DE NOTAS
{'='*60}

DATOS DEL ESTUDIANTE
{'-'*40}
    Nombre:     {self.nombre}
    Cédula:     {self.cedula}
    Tipo:       {self.tipo_grupo}

DATOS DE LA ASIGNATURA
{'-'*40}
    Profesor:   {profesor_nombre}
    Asignatura: {asignatura_nombre}

DETALLE DE NOTAS
{'-'*40}
"""
        for actividad, porcentaje in porcentajes.items():
            nota = self.notas.get(actividad, 0)
            aporte = nota * (porcentaje / 100)
            contenido += f"  {actividad:<20} {porcentaje:>5}% → Nota: {nota:>6.2f} → Aporte: {aporte:>6.2f}\n"
        
        contenido += f"""
{'-'*40}
    NOTA FINAL: {self.nota_final:.2f}
    ESTADO:     {'APROBADO ✅' if self.nota_final >= 60 else 'REPROBADO ❌'}

{'='*60}
    Reporte generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
{'='*60}
"""
        return contenido


class Asignatura:
    def __init__(self, nombre):
        self.nombre = nombre
        self.estudiantes = []
        self.porcentajes = {}

    def validar_porcentaje(self):
        total = sum(self.porcentajes.values())
        return abs(total - 100) < 0.01
    
    def actualizar_todas_notas_finales(self):
        for estudiante in self.estudiantes:
            estudiante.calcular_nota_final(self.porcentajes)
    
    def obtener_estudiante(self, cedula):
        for e in self.estudiantes:
            if e.cedula == cedula:
                return e
        return None


class Profesor:
    def __init__(self, nombre, cedula, email=""):
        self.nombre = nombre
        self.cedula = cedula
        self.email = email
        self.contraseña = ""
        self.asignaturas = []
    
    def agregar_asignatura(self, asignatura):
        self.asignaturas.append(asignatura)
    
    def eliminar_asignatura(self, nombre_asignatura):
        self.asignaturas = [a for a in self.asignaturas if a.nombre != nombre_asignatura]
    
    def obtener_asignatura(self, nombre):
        for a in self.asignaturas:
            if a.nombre == nombre:
                return a
        return None
    
    def total_estudiantes(self):
        return sum(len(a.estudiantes) for a in self.asignaturas)


class SistemaGestion:
    def __init__(self):
        self.profesores = []
    
    def agregar_profesor(self, profesor):
        self.profesores.append(profesor)
    
    def obtener_profesor(self, cedula):
        for p in self.profesores:
            if p.cedula == cedula:
                return p
        return None
    
    def guardar_datos(self, archivo="sistema_completo.json"):
        datos = {"profesores": []}
        for prof in self.profesores:
            prof_data = {
                "nombre": prof.nombre,
                "cedula": prof.cedula,
                "email": prof.email,
                "contraseña": prof.contraseña,
                "asignaturas": []
            }
            for asig in prof.asignaturas:
                asig_data = {
                    "nombre": asig.nombre,
                    "porcentajes": asig.porcentajes,
                    "estudiantes": [
                        {
                            "nombre": e.nombre,
                            "cedula": e.cedula,
                            "tipo_grupo": e.tipo_grupo,
                            "notas": e.notas,
                            "nota_final": e.nota_final
                        } for e in asig.estudiantes
                    ]
                }
                prof_data["asignaturas"].append(asig_data)
            datos["profesores"].append(prof_data)
        
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def cargar_datos(self, archivo="sistema_completo.json"):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            
            self.profesores = []
            for prof_data in datos["profesores"]:
                prof = Profesor(prof_data["nombre"], prof_data["cedula"], prof_data.get("email", ""))
                prof.contraseña = prof_data.get("contraseña", "")
                
                for asig_data in prof_data["asignaturas"]:
                    asig = Asignatura(asig_data["nombre"])
                    asig.porcentajes = asig_data.get("porcentajes", {})
                    
                    for est_data in asig_data["estudiantes"]:
                        est = Estudiante(est_data["nombre"], est_data["cedula"], est_data["tipo_grupo"])
                        est.notas = est_data.get("notas", {})
                        est.nota_final = est_data.get("nota_final", 0)
                        asig.estudiantes.append(est)
                    
                    prof.asignaturas.append(asig)
                
                self.profesores.append(prof)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False


# ============================================================================
# 2. ENCRIPTADOR SIMÉTRICO
# ============================================================================

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class EncriptadorSimetrico:
    def __init__(self):
        self.salt = b'salt_para_encriptar_123'
        self.backend = default_backend()
    
    def _derivar_clave(self, password: str, longitud: int = 32) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=longitud,
            salt=self.salt,
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(password.encode('utf-8'))
    
    def encriptar_archivo(self, archivo_entrada: str, archivo_salida: str, password: str) -> bool:
        try:
            with open(archivo_entrada, 'rb') as f:
                datos = f.read()
            
            clave = self._derivar_clave(password)
            iv = os.urandom(16)
            
            cipher = Cipher(algorithms.AES(clave), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            
            padding_length = 16 - (len(datos) % 16)
            datos_padded = datos + bytes([padding_length] * padding_length)
            
            datos_encriptados = encryptor.update(datos_padded) + encryptor.finalize()
            
            with open(archivo_salida, 'wb') as f:
                f.write(iv + datos_encriptados)
            
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def desencriptar_archivo(self, archivo_entrada: str, archivo_salida: str, password: str) -> bool:
        try:
            with open(archivo_entrada, 'rb') as f:
                iv = f.read(16)
                datos_encriptados = f.read()
            
            clave = self._derivar_clave(password)
            
            cipher = Cipher(algorithms.AES(clave), modes.CBC(iv), backend=self.backend)
            decryptor = cipher.decryptor()
            
            datos_padded = decryptor.update(datos_encriptados) + decryptor.finalize()
            
            padding_length = datos_padded[-1]
            datos = datos_padded[:-padding_length]
            
            with open(archivo_salida, 'wb') as f:
                f.write(datos)
            
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False


# ============================================================================
# 3. LOGIN
# ============================================================================

class PantallaLoginProblema1(tk.Frame):
    def __init__(self, parent, on_login_success, on_volver=None):
        super().__init__(parent, bg="#f0f0f0")
        self.on_login_success = on_login_success
        self.on_volver = on_volver
        self.sistema = SistemaGestion()
        self.sistema.cargar_datos()
        
        self.configurar_ui()
        self.crear_profesor_demo()
    
    def configurar_ui(self):
        frame = tk.Frame(self, bg="#f0f0f0")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(frame, text="🔐 ACCESO AL SISTEMA", font=("Arial", 16, "bold"),
                bg="#f0f0f0", fg="#2196F3").pack(pady=(0, 20))
        tk.Label(frame, text="Problema 1 - Gestión de Notas", font=("Arial", 12),
                bg="#f0f0f0", fg="#666").pack(pady=(0, 30))
        
        tk.Label(frame, text="Usuario (Cédula):", font=("Arial", 10), 
                bg="#f0f0f0", anchor="w").pack(fill="x")
        self.entry_usuario = tk.Entry(frame, font=("Arial", 12), bg="white", 
                                        relief=tk.SOLID, bd=1, width=25)
        self.entry_usuario.pack(fill="x", pady=(0, 15))
        
        tk.Label(frame, text="Contraseña:", font=("Arial", 10), 
                bg="#f0f0f0", anchor="w").pack(fill="x")
        self.entry_password = tk.Entry(frame, font=("Arial", 12), bg="white", 
                                        relief=tk.SOLID, bd=1, show="•", width=25)
        self.entry_password.pack(fill="x", pady=(0, 20))
        
        tk.Button(frame, text="🔓 INICIAR SESIÓN", command=self.iniciar_sesion,
                    bg="#2196F3", fg="white", font=("Arial", 11, "bold"),
                    padx=20, pady=8, width=25).pack(pady=5)
        
        tk.Button(frame, text="📝 REGISTRAR NUEVO DOCENTE", command=self.registrar_docente,
                    bg="#4CAF50", fg="white", font=("Arial", 10),
                    padx=20, pady=5, width=25).pack(pady=5)
        
        tk.Button(frame, text="❓ OLVIDÉ MI CONTRASEÑA", command=self.recuperar_password,
                    bg="#FF9800", fg="white", font=("Arial", 10),
                    padx=20, pady=5, width=25).pack(pady=5)
        
        tk.Button(frame, text="◀ VOLVER AL MENÚ", command=self.volver_al_menu,
                    bg="#9E9E9E", fg="white", font=("Arial", 10),
                    padx=20, pady=5, width=25).pack(pady=(20, 0))
        
        self.bind('<Return>', lambda event: self.iniciar_sesion())
        self.entry_usuario.focus()
    
    def volver_al_menu(self):
        self.destroy()
        if self.on_volver:
            self.on_volver()
    
    def crear_profesor_demo(self):
        if not self.sistema.profesores:
            profesor_demo = Profesor("Administrador", "admin123", "admin@email.com")
            profesor_demo.contraseña = "admin123"
            self.sistema.profesores.append(profesor_demo)
            self.sistema.guardar_datos()
    
    def iniciar_sesion(self):
        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get().strip()
        
        if not usuario or not password:
            messagebox.showwarning("Campos vacíos", "Por favor ingrese usuario y contraseña")
            return
        
        profesor = self.sistema.obtener_profesor(usuario)
        
        if profesor and hasattr(profesor, 'contraseña') and profesor.contraseña == password:
            messagebox.showinfo("Éxito", f"¡Bienvenido {profesor.nombre}!")
            self.on_login_success(profesor)
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")
    
    def registrar_docente(self):
        ventana = tk.Toplevel(self)
        ventana.title("Registrar Nuevo Docente")
        ventana.geometry("400x450")
        ventana.configure(bg="#f0f0f0")
        ventana.resizable(False, False)
        
        frame = tk.Frame(ventana, bg="#f0f0f0")
        frame.pack(expand=True, fill="both", padx=30, pady=30)
        
        tk.Label(frame, text="📝 REGISTRO DE DOCENTE", font=("Arial", 14, "bold"),
                bg="#f0f0f0", fg="#333").pack(pady=(0, 20))
        
        entradas = {}
        campos = [
            ("Nombre completo:", "entry_nombre"),
            ("Cédula (usuario):", "entry_cedula"),
            ("Correo electrónico:", "entry_email"),
            ("Contraseña:", "entry_password"),
            ("Confirmar contraseña:", "entry_confirm")
        ]
        
        for label, key in campos:
            tk.Label(frame, text=label, font=("Arial", 10), bg="#f0f0f0", 
                    anchor="w").pack(fill="x", pady=(10, 0))
            show = "•" if "contraseña" in key else ""
            entry = tk.Entry(frame, font=("Arial", 11), bg="white", 
                            relief=tk.SOLID, bd=1, show=show)
            entry.pack(fill="x", pady=(0, 5))
            entradas[key] = entry
        
        def guardar_registro():
            nombre = entradas["entry_nombre"].get().strip()
            cedula = entradas["entry_cedula"].get().strip()
            email = entradas["entry_email"].get().strip()
            password = entradas["entry_password"].get().strip()
            confirm = entradas["entry_confirm"].get().strip()
            
            if not all([nombre, cedula, password]):
                messagebox.showerror("Error", "Nombre, cédula y contraseña son obligatorios")
                return
            
            if password != confirm:
                messagebox.showerror("Error", "Las contraseñas no coinciden")
                return
            
            if self.sistema.obtener_profesor(cedula):
                messagebox.showerror("Error", "Ya existe un docente con esa cédula")
                return
            
            nuevo_profesor = Profesor(nombre, cedula, email)
            nuevo_profesor.contraseña = password
            self.sistema.agregar_profesor(nuevo_profesor)
            self.sistema.guardar_datos()
            
            messagebox.showinfo("Éxito", f"Docente {nombre} registrado correctamente")
            ventana.destroy()
        
        tk.Button(frame, text="REGISTRAR", command=guardar_registro,
                    bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                    padx=20, pady=8).pack(pady=20)
    
    def recuperar_password(self):
        ventana = tk.Toplevel(self)
        ventana.title("Recuperar Contraseña")
        ventana.geometry("400x300")
        ventana.configure(bg="#f0f0f0")
        
        frame = tk.Frame(ventana, bg="#f0f0f0")
        frame.pack(expand=True, fill="both", padx=30, pady=30)
        
        tk.Label(frame, text="🔐 RECUPERAR CONTRASEÑA", font=("Arial", 12, "bold"),
                bg="#f0f0f0", fg="#333").pack(pady=(0, 20))
        
        tk.Label(frame, text="Ingrese su cédula:", font=("Arial", 10),
                bg="#f0f0f0").pack(anchor="w")
        entry_cedula = tk.Entry(frame, font=("Arial", 11), bg="white")
        entry_cedula.pack(fill="x", pady=(0, 15))
        
        tk.Label(frame, text="Ingrese su correo electrónico:", font=("Arial", 10),
                bg="#f0f0f0").pack(anchor="w")
        entry_email = tk.Entry(frame, font=("Arial", 11), bg="white")
        entry_email.pack(fill="x", pady=(0, 20))
        
        def buscar_contraseña():
            cedula = entry_cedula.get().strip()
            email = entry_email.get().strip()
            
            profesor = self.sistema.obtener_profesor(cedula)
            
            if profesor and hasattr(profesor, 'email') and profesor.email == email:
                messagebox.showinfo("Contraseña encontrada",
                                    f"Su contraseña es: {profesor.contraseña}\n\n"
                                    f"Recomendamos cambiarla después de iniciar sesión.")
                ventana.destroy()
            else:
                messagebox.showerror("Error", "Cédula o correo incorrectos")
        
        tk.Button(frame, text="BUSCAR", command=buscar_contraseña,
                    bg="#FF9800", fg="white", font=("Arial", 11),
                    padx=20, pady=8).pack()


# ============================================================================
# 4. INTERFAZ DEL PROBLEMA 1 (Gestión de Notas)
# ============================================================================

class PantallaProblema1(tk.Frame):
    def __init__(self, parent, profesor_logueado, on_volver=None):
        super().__init__(parent, bg="#f0f0f0")
        
        self.profesor_logueado = profesor_logueado
        self.asignatura_actual = None
        self.on_volver = on_volver
        self.encriptador = EncriptadorSimetrico()
        self.CONTRASENA_ENCRIPTACION = "Notas2026"
        
        self.configurar_ui()
        self.actualizar_lista_asignaturas()
    
    def volver_al_menu(self):
        self.destroy()
        if self.on_volver:
            self.on_volver()
    
    def configurar_ui(self):
        tk.Label(self, text=f"Bienvenido, {self.profesor_logueado.nombre}", 
                font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#2196F3").pack(pady=5)
        tk.Label(self, text="Sistema de Gestión de Notas - Problema 1", font=("Arial", 16, "bold"),
                bg="#f0f0f0", fg="#333").pack(pady=5)
        
        tk.Button(self, text="◀ Volver al Menú Principal", command=self.volver_al_menu,
                    bg="#9E9E9E", fg="white", font=("Arial", 10), padx=10).pack(anchor="nw", padx=10, pady=5)
        
        panel_asignatura = tk.LabelFrame(self, text="📚 Asignatura", bg="#f0f0f0", font=("Arial", 10, "bold"))
        panel_asignatura.pack(fill="x", padx=10, pady=5)
        
        frame_asignatura = tk.Frame(panel_asignatura, bg="#f0f0f0")
        frame_asignatura.pack(padx=10, pady=5)
        
        tk.Label(frame_asignatura, text="Seleccionar:", bg="#f0f0f0").pack(side="left", padx=5)
        
        self.combo_asignaturas = ttk.Combobox(frame_asignatura, state="readonly", width=35)
        self.combo_asignaturas.pack(side="left", padx=5)
        self.combo_asignaturas.bind("<<ComboboxSelected>>", self.cambiar_asignatura)
        
        tk.Button(frame_asignatura, text="➕ Nueva Asignatura", command=self.nueva_asignatura,
                    bg="#2196F3", fg="white").pack(side="left", padx=5)
        tk.Button(frame_asignatura, text="⚙️ Configurar %", command=self.configurar_porcentajes,
                    bg="#FF9800", fg="white").pack(side="left", padx=5)
        
        panel_estudiantes = tk.LabelFrame(self, text="📋 Estudiantes", bg="#f0f0f0", font=("Arial", 10, "bold"))
        panel_estudiantes.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(panel_estudiantes, columns=("Cédula", "Nombre", "Tipo", "Nota Final", "Estado"), show="headings")
        self.tree.heading("Cédula", text="Cédula")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Tipo", text="Tipo")
        self.tree.heading("Nota Final", text="Nota Final")
        self.tree.heading("Estado", text="Estado")
        
        self.tree.column("Cédula", width=100)
        self.tree.column("Nombre", width=200)
        self.tree.column("Tipo", width=100)
        self.tree.column("Nota Final", width=100)
        self.tree.column("Estado", width=100)
        
        self.tree.bind("<Double-1>", self.descargar_notas_individuales)
        self.tree.bind("<Button-3>", self.mostrar_menu_contextual)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        panel_botones = tk.Frame(self, bg="#f0f0f0")
        panel_botones.pack(pady=10)
        
        tk.Button(panel_botones, text="➕ Agregar Estudiante", command=self.agregar_estudiante,
                    bg="#009688", fg="white", padx=15).pack(side="left", padx=5)
        tk.Button(panel_botones, text="📝 Ingresar Notas", command=self.ingresar_notas,
                    bg="#9C27B0", fg="white", padx=15).pack(side="left", padx=5)
        tk.Button(panel_botones, text="🎲 Simular (N veces)", command=self.simular_calculos,
                    bg="#795548", fg="white", padx=15).pack(side="left", padx=5)
        tk.Button(panel_botones, text="📊 Ver Reporte", command=self.ver_reporte,
                    bg="#3F51B5", fg="white", padx=15).pack(side="left", padx=5)
        tk.Button(panel_botones, text="💾 Guardar Reporte (Encriptado)", command=self.guardar_reporte_encriptado,
                    bg="#E91E63", fg="white", padx=15).pack(side="left", padx=5)
        tk.Button(panel_botones, text="💾 Guardar Todo", command=self.guardar_todo,
                    bg="#607D8B", fg="white", padx=15).pack(side="left", padx=5)
        
        tk.Label(self, text="💡 Sugerencia: Haga doble clic en un estudiante para descargar sus notas (encriptadas)",
                font=("Arial", 9), bg="#f0f0f0", fg="#666").pack(pady=5)
    
    def actualizar_lista_asignaturas(self):
        if self.profesor_logueado:
            nombres = [a.nombre for a in self.profesor_logueado.asignaturas]
            self.combo_asignaturas["values"] = nombres
            if nombres:
                self.combo_asignaturas.current(0)
                self.asignatura_actual = self.profesor_logueado.asignaturas[0]
                self.mostrar_estudiantes()
            else:
                self.asignatura_actual = None
                self.tree.delete(*self.tree.get_children())
    
    def cambiar_asignatura(self, event):
        nombre = self.combo_asignaturas.get()
        if self.profesor_logueado and nombre:
            self.asignatura_actual = self.profesor_logueado.obtener_asignatura(nombre)
            self.mostrar_estudiantes()
    
    def nueva_asignatura(self):
        nombre = simpledialog.askstring("Nueva Asignatura", "Nombre de la asignatura:")
        if nombre:
            if self.profesor_logueado.obtener_asignatura(nombre):
                messagebox.showerror("Error", "Ya existe esa asignatura para este profesor")
                return
            asignatura = Asignatura(nombre)
            self.profesor_logueado.agregar_asignatura(asignatura)
            self.actualizar_lista_asignaturas()
            messagebox.showinfo("Éxito", f"Asignatura '{nombre}' creada")
    
    def mostrar_estudiantes(self):
        self.tree.delete(*self.tree.get_children())
        if not self.asignatura_actual:
            return
        for est in self.asignatura_actual.estudiantes:
            estado = "✅ Aprobado" if est.nota_final >= 60 else "❌ Reprobado"
            self.tree.insert("", tk.END, values=(est.cedula, est.nombre, est.tipo_grupo, f"{est.nota_final:.2f}", estado))
    
    def descargar_notas_individuales(self, event):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un estudiante")
            return
        item = seleccion[0]
        valores = self.tree.item(item, "values")
        estudiante = None
        for est in self.asignatura_actual.estudiantes:
            if est.cedula == valores[0]:
                estudiante = est
                break
        if estudiante:
            self.guardar_notas_individuales(estudiante)
    
    def mostrar_menu_contextual(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="📥 Descargar Notas (Encriptado)", 
                            command=lambda: self.descargar_notas_individuales(None))
            menu.post(event.x_root, event.y_root)
    
    def guardar_notas_individuales(self, estudiante):
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"notas_{estudiante.nombre.replace(' ', '_')}_{fecha}"
        
        archivo = filedialog.asksaveasfilename(
            title="Guardar notas del estudiante (encriptado)",
            defaultextension=".enc",
            initialfile=nombre_archivo + ".enc",
            filetypes=[("Archivos encriptados", "*.enc"), ("Todos los archivos", "*.*")]
        )
        
        if archivo:
            try:
                contenido = estudiante.exportar_notas(
                    self.asignatura_actual.nombre,
                    self.profesor_logueado.nombre,
                    self.asignatura_actual.porcentajes
                )
                archivo_temp = archivo + ".temp.txt"
                with open(archivo_temp, "w", encoding="utf-8") as f:
                    f.write(contenido)
                
                if self.encriptador.encriptar_archivo(archivo_temp, archivo, self.CONTRASENA_ENCRIPTACION):
                    os.remove(archivo_temp)
                    messagebox.showinfo("Éxito", 
                        f"✅ Notas guardadas y encriptadas correctamente.\n\n"
                        f"📁 Archivo: {os.path.basename(archivo)}\n"
                        f"🔑 Contraseña: {self.CONTRASENA_ENCRIPTACION}")
                else:
                    messagebox.showerror("Error", "No se pudo encriptar el archivo")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")
    
    def generar_contenido_reporte(self):
        contenido = f"""
{'═' * 80}
                    📊 REPORTE DE NOTAS
{'═' * 80}

📋 INFORMACIÓN GENERAL
{'─' * 80}
    Profesor:     {self.profesor_logueado.nombre}
    Asignatura:   {self.asignatura_actual.nombre}
    Total Estudiantes: {len(self.asignatura_actual.estudiantes)}

⚙️ CONFIGURACIÓN DE EVALUACIÓN
{'─' * 80}
"""
        for act, porc in self.asignatura_actual.porcentajes.items():
            contenido += f"  • {act}: {porc}%\n"
        
        contenido += f"\n📝 DETALLE DE ESTUDIANTES\n{'─' * 80}\n"
        
        for i, est in enumerate(self.asignatura_actual.estudiantes, 1):
            contenido += f"\n  {i}. {est.nombre.upper()}"
            contenido += f"\n     Cédula: {est.cedula} | Tipo: {est.tipo_grupo}"
            contenido += f"\n     Nota Final: {est.nota_final:.2f} - {'APROBADO ✅' if est.nota_final >= 60 else 'REPROBADO ❌'}"
            contenido += "\n     Notas por actividad:"
            for act, nota in est.notas.items():
                contenido += f"\n        • {act}: {nota}"
        
        if self.asignatura_actual.estudiantes:
            notas = [e.nota_final for e in self.asignatura_actual.estudiantes]
            aprobados = len([n for n in notas if n >= 60])
            reprobados = len(notas) - aprobados
            contenido += f"\n\n{'─' * 80}\n📈 ESTADÍSTICAS\n{'─' * 80}"
            contenido += f"\n  Promedio: {sum(notas)/len(notas):.2f}"
            contenido += f"\n  Aprobados: {aprobados}/{len(notas)} ({aprobados*100/len(notas):.1f}%)"
            contenido += f"\n  Reprobados: {reprobados}/{len(notas)} ({reprobados*100/len(notas):.1f}%)"
        return contenido
    
    def guardar_reporte_encriptado(self):
        if not self.asignatura_actual:
            messagebox.showwarning("Advertencia", "Selecciona una asignatura")
            return
        
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"reporte_{self.asignatura_actual.nombre.replace(' ', '_')}_{fecha}"
        
        archivo = filedialog.asksaveasfilename(
            title="Guardar reporte encriptado",
            defaultextension=".enc",
            initialfile=nombre_archivo + ".enc",
            filetypes=[("Archivos encriptados", "*.enc"), ("Todos los archivos", "*.*")]
        )
        
        if archivo:
            try:
                contenido = self.generar_contenido_reporte()
                archivo_temp = archivo + ".temp.txt"
                with open(archivo_temp, "w", encoding="utf-8") as f:
                    f.write(contenido)
                
                if self.encriptador.encriptar_archivo(archivo_temp, archivo, self.CONTRASENA_ENCRIPTACION):
                    os.remove(archivo_temp)
                    messagebox.showinfo("Éxito", 
                        f"✅ Reporte guardado y encriptado.\n\n"
                        f"🔑 Contraseña: {self.CONTRASENA_ENCRIPTACION}")
                else:
                    messagebox.showerror("Error", "No se pudo encriptar")
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")
    
    def agregar_estudiante(self):
        if not self.asignatura_actual:
            messagebox.showwarning("Advertencia", "Selecciona una asignatura")
            return
        nombre = simpledialog.askstring("Nuevo Estudiante", "Nombre completo:")
        cedula = simpledialog.askstring("Nuevo Estudiante", "Cédula:")
        tipo = simpledialog.askstring("Nuevo Estudiante", "Tipo (presencial/distancia):")
        if nombre and cedula and tipo in ["presencial", "distancia"]:
            estudiante = Estudiante(nombre, cedula, tipo)
            self.asignatura_actual.estudiantes.append(estudiante)
            self.mostrar_estudiantes()
            messagebox.showinfo("Éxito", "Estudiante agregado")
        else:
            messagebox.showerror("Error", "Tipo inválido. Usa 'presencial' o 'distancia'")
    
    def configurar_porcentajes(self):
        if not self.asignatura_actual:
            messagebox.showwarning("Advertencia", "Selecciona una asignatura")
            return
        
        ventana = tk.Toplevel(self)
        ventana.title("Configurar Porcentajes")
        ventana.geometry("500x450")
        ventana.configure(bg="#f0f0f0")
        
        tk.Label(ventana, text=f"Asignatura: {self.asignatura_actual.nombre}", 
                font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)
        
        frame_predef = tk.LabelFrame(ventana, text="Opciones Predefinidas", bg="#f0f0f0")
        frame_predef.pack(fill="x", padx=20, pady=10)
        
        configuraciones = {
            "📚 Estándar (5 actividades)": {"Examen Semestral":40, "Parciales":25, "Laboratorios":15, "Investigaciones":10, "Asistencias":10},
            "📖 Teórico (4 actividades)": {"Examen Semestral":50, "Parciales":25, "Investigaciones":15, "Asistencias":10},
            "🔬 Práctico (4 actividades)": {"Laboratorios":40, "Proyectos":30, "Parciales":20, "Asistencias":10},
            "🎯 Continua (3 actividades)": {"Tareas":40, "Parciales":30, "Proyecto":30}
        }
        
        def aplicar_predef(config):
            self.asignatura_actual.porcentajes = config
            self.asignatura_actual.actualizar_todas_notas_finales()
            self.mostrar_estudiantes()
            messagebox.showinfo("Éxito", f"Configuración aplicada: {sum(config.values())}%")
            ventana.destroy()
        
        for nombre, config in configuraciones.items():
            btn = tk.Button(frame_predef, text=nombre,
                            command=lambda c=config: aplicar_predef(c),
                            bg="#2196F3", fg="white", padx=10, pady=3)
            btn.pack(fill="x", padx=5, pady=2)
        
        frame_pers = tk.LabelFrame(ventana, text="Configuración Personalizada", bg="#f0f0f0")
        frame_pers.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(frame_pers, text="Formato: actividad:porcentaje, actividad2:porcentaje", 
                bg="#f0f0f0", font=("Arial", 9)).pack()
        tk.Label(frame_pers, text="Ejemplo: Examen:40, Tareas:30, Proyecto:30", 
                bg="#f0f0f0", font=("Arial", 9)).pack()
        
        texto = tk.Text(frame_pers, height=5, width=50)
        texto.pack(pady=5)
        
        if self.asignatura_actual.porcentajes:
            actual = ", ".join([f"{k}:{v}" for k, v in self.asignatura_actual.porcentajes.items()])
            texto.insert("1.0", actual)
        
        def guardar_personalizado():
            try:
                contenido = texto.get("1.0", tk.END).strip()
                nuevos = {}
                for parte in contenido.split(","):
                    if ":" in parte:
                        nombre, valor = parte.split(":")
                        nuevos[nombre.strip()] = float(valor.strip())
                total = sum(nuevos.values())
                if abs(total - 100) > 0.01:
                    messagebox.showerror("Error", f"Los porcentajes suman {total}%, deben sumar 100%")
                    return
                self.asignatura_actual.porcentajes = nuevos
                self.asignatura_actual.actualizar_todas_notas_finales()
                self.mostrar_estudiantes()
                messagebox.showinfo("Éxito", "Porcentajes guardados")
                ventana.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Formato inválido: {e}")
        
        tk.Button(frame_pers, text="Guardar Personalizado", command=guardar_personalizado,
                    bg="#4CAF50", fg="white").pack(pady=5)
    
    def ingresar_notas(self):
        if not self.asignatura_actual:
            messagebox.showwarning("Advertencia", "Selecciona una asignatura")
            return
        if not self.asignatura_actual.porcentajes:
            messagebox.showwarning("Advertencia", "Configura los porcentajes primero")
            return
        
        ventana_est = tk.Toplevel(self)
        ventana_est.title("Seleccionar Estudiante")
        ventana_est.geometry("350x450")
        ventana_est.configure(bg="#f0f0f0")
        
        tk.Label(ventana_est, text="Selecciona un estudiante:", font=("Arial", 12, "bold"),
                bg="#f0f0f0").pack(pady=10)
        
        frame_lista = tk.Frame(ventana_est, bg="#f0f0f0")
        frame_lista.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(frame_lista)
        scrollbar.pack(side="right", fill="y")
        
        lista = tk.Listbox(frame_lista, yscrollcommand=scrollbar.set, font=("Arial", 10))
        lista.pack(fill="both", expand=True)
        scrollbar.config(command=lista.yview)
        
        for e in self.asignatura_actual.estudiantes:
            lista.insert(tk.END, f"{e.nombre} - {e.cedula}")
        
        def seleccionar():
            seleccion = lista.curselection()
            if seleccion:
                estudiante = self.asignatura_actual.estudiantes[seleccion[0]]
                ventana_est.destroy()
                self.mostrar_ventana_notas(estudiante)
        
        tk.Button(ventana_est, text="Seleccionar", command=seleccionar, 
                    bg="#4CAF50", fg="white", padx=20, pady=5).pack(pady=10)
    
    def mostrar_ventana_notas(self, estudiante):
        ventana = tk.Toplevel(self)
        ventana.title(f"Ingresar Notas - {estudiante.nombre}")
        ventana.geometry("400x500")
        ventana.configure(bg="#f0f0f0")
        
        tk.Label(ventana, text=f"Estudiante: {estudiante.nombre}", 
                font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=5)
        tk.Label(ventana, text=f"Cédula: {estudiante.cedula}", 
                font=("Arial", 10), bg="#f0f0f0").pack()
        
        frame_notas = tk.Frame(ventana, bg="#f0f0f0")
        frame_notas.pack(pady=10, padx=20, fill="both", expand=True)
        
        entradas = {}
        for actividad, porcentaje in self.asignatura_actual.porcentajes.items():
            frame_act = tk.Frame(frame_notas, bg="#f0f0f0")
            frame_act.pack(fill="x", pady=5)
            tk.Label(frame_act, text=f"{actividad} ({porcentaje}%):", 
                    width=25, anchor="w", bg="#f0f0f0").pack(side="left")
            entry = tk.Entry(frame_act, width=10)
            entry.pack(side="left", padx=5)
            if actividad in estudiante.notas:
                entry.insert(0, str(estudiante.notas[actividad]))
            entradas[actividad] = entry
        
        label_nota_final = tk.Label(ventana, text=f"Nota Final Actual: {estudiante.nota_final:.2f}", 
                                    font=("Arial", 10, "bold"), bg="#f0f0f0", fg="#2196F3")
        label_nota_final.pack(pady=5)
        
        def guardar_notas():
            try:
                for act, entry in entradas.items():
                    valor = float(entry.get())
                    if 0 <= valor <= 100:
                        estudiante.notas[act] = valor
                    else:
                        raise ValueError("Nota fuera de rango")
                estudiante.calcular_nota_final(self.asignatura_actual.porcentajes)
                self.mostrar_estudiantes()
                label_nota_final.config(text=f"Nota Final: {estudiante.nota_final:.2f}", fg="#4CAF50")
                messagebox.showinfo("Éxito", f"Notas guardadas\nNota final: {estudiante.nota_final:.2f}")
            except ValueError:
                messagebox.showerror("Error", "Nota inválida (0-100)")
        
        tk.Button(ventana, text="💾 Guardar Notas", command=guardar_notas, 
                    bg="#4CAF50", fg="white", padx=15, pady=5).pack(pady=10)
    
    def simular_calculos(self):
        if not self.asignatura_actual:
            messagebox.showwarning("Advertencia", "Selecciona una asignatura")
            return
        if not self.asignatura_actual.estudiantes:
            messagebox.showwarning("Advertencia", "No hay estudiantes")
            return
        if not self.asignatura_actual.porcentajes:
            messagebox.showwarning("Advertencia", "Configura los porcentajes primero")
            return
        
        N = simpledialog.askinteger("Simulación", "Número de veces a simular:", minvalue=1, maxvalue=100)
        if not N:
            return
        
        for _ in range(N):
            for est in self.asignatura_actual.estudiantes:
                for act in self.asignatura_actual.porcentajes.keys():
                    est.notas[act] = random.randint(50, 100)
                est.calcular_nota_final(self.asignatura_actual.porcentajes)
        
        self.mostrar_estudiantes()
        messagebox.showinfo("Simulación", f"Simulación completada {N} veces")
    
    def ver_reporte(self):
        if not self.asignatura_actual:
            messagebox.showwarning("Advertencia", "Selecciona una asignatura")
            return
        
        reporte = tk.Toplevel(self)
        reporte.title(f"📊 Reporte de Notas - {self.asignatura_actual.nombre}")
        reporte.geometry("800x600")
        reporte.configure(bg="#f0f0f0")
        
        frame_scroll = tk.Frame(reporte)
        frame_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame_scroll)
        scrollbar.pack(side="right", fill="y")
        
        texto = tk.Text(frame_scroll, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                        font=("Courier", 10), bg="white")
        texto.pack(fill="both", expand=True)
        scrollbar.config(command=texto.yview)
        
        texto.insert("1.0", self.generar_contenido_reporte())
        texto.config(state=tk.DISABLED)
        
        tk.Button(reporte, text="Cerrar", command=reporte.destroy,
                    bg="#f44336", fg="white", padx=20, pady=5).pack(pady=10)
    
    def guardar_todo(self):
        sistema_temp = SistemaGestion()
        sistema_temp.profesores = [self.profesor_logueado]
        if sistema_temp.guardar_datos():
            messagebox.showinfo("Éxito", "Datos guardados correctamente")
        else:
            messagebox.showerror("Error", "Error al guardar")


# ============================================================================
# 5. INTERFAZ DEL PROBLEMA 2 (Encriptación de Archivos)
# ============================================================================

class PantallaProblema2(tk.Frame):
    def __init__(self, parent, on_volver=None):
        super().__init__(parent, bg="#f0f0f0")
        self.on_volver = on_volver
        self.encriptador = EncriptadorSimetrico()
        self.archivo_actual = None
        
        self.configurar_ui()
    
    def configurar_ui(self):
        tk.Label(self, text="🔐 PROBLEMA 2: ENCRIPTACIÓN DE ARCHIVOS", font=("Arial", 16, "bold"),
                bg="#f0f0f0", fg="#2196F3").pack(pady=10)
        tk.Label(self, text="Método Simétrico (AES) - Misma clave para encriptar y desencriptar", 
                font=("Arial", 10), bg="#f0f0f0", fg="#666").pack()
        
        if self.on_volver:
            tk.Button(self, text="◀ Volver al Menú Principal", command=self.on_volver,
                        bg="#9E9E9E", fg="white", font=("Arial", 10), padx=10).pack(anchor="nw", padx=10, pady=5)
        
        panel_archivos = tk.LabelFrame(self, text="📂 Selección de Archivos", bg="#f0f0f0", font=("Arial", 11, "bold"))
        panel_archivos.pack(fill="x", padx=10, pady=10)
        
        frame_origen = tk.Frame(panel_archivos, bg="#f0f0f0")
        frame_origen.pack(fill="x", padx=10, pady=10)
        
        tk.Label(frame_origen, text="Archivo origen:", bg="#f0f0f0", width=15, anchor="w").pack(side="left")
        self.label_archivo = tk.Label(frame_origen, text="Ningún archivo seleccionado", bg="#f0f0f0", fg="#666", anchor="w")
        self.label_archivo.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frame_origen, text="📁 Buscar", command=self.seleccionar_archivo, bg="#2196F3", fg="white", padx=10).pack(side="right")
        
        panel_password = tk.LabelFrame(self, text="🔑 Configuración de la Clave", bg="#f0f0f0", font=("Arial", 11, "bold"))
        panel_password.pack(fill="x", padx=10, pady=10)
        
        frame_password = tk.Frame(panel_password, bg="#f0f0f0")
        frame_password.pack(padx=10, pady=10)
        
        tk.Label(frame_password, text="Contraseña:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(side="left")
        self.entry_password = tk.Entry(frame_password, show="•", width=30, font=("Arial", 11))
        self.entry_password.pack(side="left", padx=10)
        
        self.mostrar_var = tk.IntVar(value=0)
        self.check_mostrar = tk.Checkbutton(frame_password, text="👁 Mostrar contraseña",
                                            variable=self.mostrar_var,
                                            command=self.toggle_password,
                                            bg="#f0f0f0")
        self.check_mostrar.pack(side="left")
        
        panel_acciones = tk.Frame(self, bg="#f0f0f0")
        panel_acciones.pack(pady=20)
        
        tk.Button(panel_acciones, text="🔒 ENCRIPTAR ARCHIVO", command=self.encriptar_archivo,
                    bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), padx=20, pady=10, width=20).pack(side="left", padx=10)
        
        tk.Button(panel_acciones, text="🔓 DESENCRIPTAR ARCHIVO", command=self.desencriptar_archivo,
                    bg="#2196F3", fg="white", font=("Arial", 12, "bold"), padx=20, pady=10, width=20).pack(side="left", padx=10)
        
        panel_log = tk.LabelFrame(self, text="📋 Registro de Actividad", bg="#f0f0f0", font=("Arial", 11, "bold"))
        panel_log.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.text_log = tk.Text(panel_log, height=10, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.text_log.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(self.text_log)
        scrollbar.pack(side="right", fill="y")
        self.text_log.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_log.yview)
        
        self.agregar_log("✅ Programa listo. Seleccione un archivo para comenzar.")
        self.agregar_log("💡 La misma contraseña sirve para encriptar y desencriptar.")
    
    def toggle_password(self):
        if self.mostrar_var.get() == 1:
            self.entry_password.config(show="")
        else:
            self.entry_password.config(show="•")
    
    def seleccionar_archivo(self):
        archivo = filedialog.askopenfilename(title="Seleccionar archivo")
        if archivo:
            self.archivo_actual = archivo
            self.label_archivo.config(text=os.path.basename(archivo), fg="#333")
            self.agregar_log(f"📂 Archivo seleccionado: {os.path.basename(archivo)}")
    
    def agregar_log(self, mensaje):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_log.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.text_log.see(tk.END)
    
    def encriptar_archivo(self):
        if not self.archivo_actual:
            messagebox.showwarning("Advertencia", "Seleccione un archivo primero")
            return
        
        password = self.entry_password.get()
        if not password:
            messagebox.showwarning("Advertencia", "Ingrese una contraseña")
            return
        
        archivo_salida = filedialog.asksaveasfilename(
            title="Guardar archivo encriptado",
            defaultextension=".enc",
            initialfile=os.path.basename(self.archivo_actual) + ".enc",
            filetypes=[("Archivos encriptados", "*.enc"), ("Todos los archivos", "*.*")]
        )
        
        if not archivo_salida:
            return
        
        self.agregar_log(f"🔒 Encriptando archivo...")
        
        if self.encriptador.encriptar_archivo(self.archivo_actual, archivo_salida, password):
            self.agregar_log(f"✅ Archivo encriptado: {os.path.basename(archivo_salida)}")
            messagebox.showinfo("Éxito", f"Archivo encriptado correctamente\n\nGuardado en: {archivo_salida}")
        else:
            self.agregar_log("❌ Error al encriptar")
            messagebox.showerror("Error", "No se pudo encriptar el archivo")
    
    def desencriptar_archivo(self):
        if not self.archivo_actual:
            messagebox.showwarning("Advertencia", "Seleccione un archivo encriptado (.enc)")
            return
        
        password = self.entry_password.get()
        if not password:
            messagebox.showwarning("Advertencia", "Ingrese la misma contraseña que usó para encriptar")
            return
        
        archivo_salida = filedialog.asksaveasfilename(
            title="Guardar archivo desencriptado",
            defaultextension="",
            initialfile=os.path.basename(self.archivo_actual).replace(".enc", ""),
            filetypes=[("Todos los archivos", "*.*")]
        )
        
        if not archivo_salida:
            return
        
        self.agregar_log(f"🔓 Desencriptando archivo...")
        
        if self.encriptador.desencriptar_archivo(self.archivo_actual, archivo_salida, password):
            self.agregar_log(f"✅ Archivo desencriptado: {os.path.basename(archivo_salida)}")
            messagebox.showinfo("Éxito", f"Archivo desencriptado correctamente\n\nGuardado en: {archivo_salida}")
        else:
            self.agregar_log("❌ Error al desencriptar (¿contraseña incorrecta?)")
            messagebox.showerror("Error", "No se pudo desencriptar.\nVerifique la contraseña.")


# ============================================================================
# 6. APLICACIÓN PRINCIPAL
# ============================================================================

class AppPrincipal:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Taller Práctico 1 - Programación II")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        self.root.resizable(False, False)
        
        self.configurar_menu()
        self.mostrar_menu_central()
    
    def configurar_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        archivo_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Archivo", menu=archivo_menu)
        archivo_menu.add_command(label="Salir", command=self.root.quit)
        
        ayuda_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Ayuda", menu=ayuda_menu)
        ayuda_menu.add_command(label="Acerca de", command=self.mostrar_acerca_de)
    
    def mostrar_acerca_de(self):
        acerca = tk.Toplevel(self.root)
        acerca.title("Acerca de")
        acerca.geometry("400x250")
        acerca.configure(bg="#f0f0f0")
        acerca.resizable(False, False)
        acerca.transient(self.root)
        acerca.grab_set()
        
        tk.Label(acerca, text="📚 TALLER PRÁCTICO 1", font=("Arial", 16, "bold"),
                bg="#f0f0f0", fg="#2196F3").pack(pady=20)
        tk.Label(acerca, text="Programación II", font=("Arial", 12),
                bg="#f0f0f0", fg="#666").pack()
        tk.Label(acerca, text="Universidad Tecnológica de Panamá", font=("Arial", 10),
                bg="#f0f0f0", fg="#888").pack()
        tk.Label(acerca, text="\nProblema 1: Gestión de Notas", font=("Arial", 10),
                bg="#f0f0f0", fg="#333").pack()
        tk.Label(acerca, text="Problema 2: Encriptación de Archivos (AES)", font=("Arial", 10),
                bg="#f0f0f0", fg="#333").pack()
        
        tk.Button(acerca, text="Cerrar", command=acerca.destroy,
                    bg="#2196F3", fg="white", padx=20, pady=5).pack(pady=20)
    
    def limpiar_pantalla(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def mostrar_menu_central(self):
        self.limpiar_pantalla()
        
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True)
        
        center_frame = tk.Frame(main_frame, bg="#f0f0f0")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(center_frame, text="📚 TALLER PRÁCTICO 1", font=("Arial", 24, "bold"),
                bg="#f0f0f0", fg="#2196F3").pack(pady=(0, 10))
        
        tk.Label(center_frame, text="Programación II - Universidad Tecnológica de Panamá", 
                font=("Arial", 11), bg="#f0f0f0", fg="#666").pack(pady=(0, 40))
        
        tk.Frame(center_frame, height=2, width=300, bg="#2196F3").pack(pady=10)
        
        btn_problema1 = tk.Button(center_frame, 
                                    text="📋 PROBLEMA 1\nGestión de Notas", 
                                    command=self.iniciar_problema1,
                                    bg="#4CAF50", fg="white",
                                    font=("Arial", 12, "bold"),
                                    padx=40, pady=20, width=25, height=2,
                                    relief=tk.RAISED, bd=3)
        btn_problema1.pack(pady=10)
        
        btn_problema2 = tk.Button(center_frame, 
                                    text="🔐 PROBLEMA 2\nEncriptación de Archivos (AES)",
                                    command=self.iniciar_problema2,
                                    bg="#FF9800", fg="white",
                                    font=("Arial", 12, "bold"),
                                    padx=40, pady=20, width=25, height=2,
                                    relief=tk.RAISED, bd=3)
        btn_problema2.pack(pady=10)
        
        btn_salir = tk.Button(center_frame,
                                text="❌ SALIR",
                                command=self.root.quit,
                                bg="#f44336", fg="white",
                                font=("Arial", 11, "bold"),
                                padx=40, pady=10, width=25,
                                relief=tk.RAISED, bd=3)
        btn_salir.pack(pady=(20, 0))
        
        self.agregar_efecto_hover(btn_problema1, "#4CAF50", "#45a049")
        self.agregar_efecto_hover(btn_problema2, "#FF9800", "#fb8c00")
        self.agregar_efecto_hover(btn_salir, "#f44336", "#d32f2f")
        
        self.configurar_menu()
    
    def agregar_efecto_hover(self, boton, color_normal, color_hover):
        def on_enter(event):
            boton.config(bg=color_hover)
        def on_leave(event):
            boton.config(bg=color_normal)
        boton.bind("<Enter>", on_enter)
        boton.bind("<Leave>", on_leave)
    
    def iniciar_problema1(self):
        self.limpiar_pantalla()
        login_frame = PantallaLoginProblema1(self.root, self.on_login_exitoso, on_volver=self.mostrar_menu_central)
        login_frame.pack(fill="both", expand=True)
    
    def on_login_exitoso(self, profesor):
        self.limpiar_pantalla()
        p1_frame = PantallaProblema1(self.root, profesor, on_volver=self.mostrar_menu_central)
        p1_frame.pack(fill="both", expand=True)
    
    def iniciar_problema2(self):
        self.limpiar_pantalla()
        
        container = tk.Frame(self.root, bg="#f0f0f0")
        container.pack(fill="both", expand=True)
        
        btn_volver = tk.Button(container,
                                text="◀ Volver al Menú Principal",
                                command=self.mostrar_menu_central,
                                bg="#9E9E9E", fg="white", font=("Arial", 10),
                                padx=10, pady=5)
        btn_volver.pack(anchor="nw", padx=10, pady=5)
        
        p2_frame = PantallaProblema2(container, on_volver=self.mostrar_menu_central)
        p2_frame.pack(fill="both", expand=True)
    
    def run(self):
        self.root.mainloop()


# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    app = AppPrincipal()
    app.run()