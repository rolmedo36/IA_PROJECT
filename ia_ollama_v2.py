import tkinter as tk
from tkinter import scrolledtext
import sqlite3
import threading
import re
import ollama  # Requiere: pip install ollama


class AnalistaDirectoPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Analista de Datos NetSuite - Llama 3")
        self.root.geometry("1000x800")
        self.root.configure(bg="#f4f4f9")

        self.db_path = 'ventas_netsuite.db'
        self.setup_ui()

    def setup_ui(self):
        # Header decorativo
        header = tk.Frame(self.root, bg="#1a73e8", pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="ASISTENTE DE INTELIGENCIA DE NEGOCIOS",
                 fg="white", bg="#1a73e8", font=("Segoe UI", 12, "bold")).pack()

        # Área de Chat
        self.chat_display = scrolledtext.ScrolledText(
            self.root, font=("Consolas", 11), bg="white", padx=15, pady=15
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.chat_display.config(state='disabled')

        # Frame de entrada
        input_frame = tk.Frame(self.root, bg="#f4f4f9")
        input_frame.pack(fill=tk.X, padx=20, pady=10)

        self.user_entry = tk.Entry(input_frame, font=("Segoe UI", 12), bd=2, relief="flat")
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.user_entry.bind("<Return>", lambda e: self.procesar())

        btn = tk.Button(input_frame, text="ANALIZAR", command=self.procesar,
                        bg="#1a73e8", fg="white", font=("Segoe UI", 10, "bold"),
                        padx=20, relief="flat", cursor="hand2")
        btn.pack(side=tk.RIGHT, padx=5)

    def log(self, sender, msg):
        self.chat_display.config(state='normal')
        tag = sender.lower()
        self.chat_display.tag_config("tú", foreground="#1a73e8", font=("Consolas", 11, "bold"))
        self.chat_display.tag_config("analista", foreground="#2e7d32", font=("Consolas", 11, "bold"))
        self.chat_display.tag_config("sistema", foreground="#d32f2f", font=("Consolas", 11, "italic"))

        self.chat_display.insert(tk.END, f"{sender}: ", tag)
        self.chat_display.insert(tk.END, f"{msg}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def procesar(self):
        pregunta = self.user_entry.get()
        if not pregunta: return
        self.log("Tú", pregunta)
        self.user_entry.delete(0, tk.END)
        # Hilo separado para no congelar la ventana
        threading.Thread(target=self.run_ai, args=(pregunta,), daemon=True).start()

    def run_ai(self, pregunta):
        try:
            # 1. Obtener estructura de la base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(ventas)")
            columnas = [c[1] for c in cursor.fetchall()]

            # 2. Instrucciones para la IA (Prompt Engineering)
            prompt = (
                f"Eres un experto en SQLite. Tabla: 'ventas'. Columnas: {columnas}. "
                f"Reglas de negocio: 'MASCOTA - T' y 'MASCOTA- CEL' son Veterinaria. "
                f"Genera SOLO el código SQL para: {pregunta}. "
                "No uses bloques de código (```), no des explicaciones. "
                "Si usas UNION con LIMIT, usa subconsultas: SELECT * FROM (SELECT...) UNION ALL SELECT * FROM (SELECT...)."
            )

            response = ollama.generate(model='llama3', prompt=prompt)
            sql = response['response'].strip()

            # Limpieza de seguridad por si la IA ignora las instrucciones de formato
            sql = sql.replace('```sql', '').replace('```', '')
            sql = sql.split(';')[0] + ';'  # Solo tomar la primera instrucción
            sql = re.sub(r'^(SQL|Respuesta|Query):', '', sql, flags=re.IGNORECASE).strip()

            print(f"--- DEBUG SQL EJECUTADO ---\n{sql}\n---------------------------")

            # 3. Ejecutar y obtener resultados
            cursor.execute(sql)
            resultados = cursor.fetchall()
            conn.close()

            # 4. Formatear y mostrar
            if resultados:
                res_fmt = "\n".join([str(r) for r in resultados])
                self.root.after(0, lambda: self.log("Analista", f"Resultados encontrados:\n{res_fmt}"))
            else:
                self.root.after(0, lambda: self.log("Analista", "No se encontraron datos para esta consulta."))

        except Exception as e:
            # Corrección del NameError: capturamos el mensaje en una variable local
            error_msg = str(e)
            print(f"DEBUG ERROR: {error_msg}")
            # Pasamos m=error_msg para asegurar que el valor persista en el lambda
            self.root.after(0, lambda m=error_msg: self.log("Sistema", f"Error: {m}"))


if __name__ == "__main__":
    root = tk.Tk()
    AnalistaDirectoPro(root)
    root.mainloop()