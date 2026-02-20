import tkinter as tk
from tkinter import filedialog, scrolledtext
import pandas as pd
import threading
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_ollama import OllamaLLM


class SuperAnalistaIA:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual Analyst IA: Pandas + Llama3")
        self.root.geometry("1100x850")
        self.root.configure(bg="#f0f2f5")

        # Conexión a tu Llama 3 local
        self.llm = OllamaLLM(model="llama3", temperature=0.2)
        self.df = None
        self.agent = None

        self.setup_ui()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1a73e8", pady=20)
        header.pack(fill=tk.X)
        tk.Label(header, text="PANEL DE CONTROL DE VENTAS - MODO HÍBRIDO",
                 fg="white", bg="#1a73e8", font=("Helvetica", 18, "bold")).pack()

        # Botones de Carga
        btn_frame = tk.Frame(self.root, bg="#f0f2f5")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="📂 Seleccionar CSV de NetSuite", command=self.load_data,
                  bg="#ffffff", font=("Arial", 10, "bold"), padx=20, pady=5).pack()

        self.status_label = tk.Label(self.root, text="Estado: Esperando archivo...", bg="#f0f2f5", fg="#666")
        self.status_label.pack()

        # Chat Principal
        # Un fondo gris muy claro y texto azul oscuro/negro es lo más "normal" y legible
        self.chat_display = scrolledtext.ScrolledText(
            self.root,
            font=("Segoe UI", 11),
            bg="#F0F2F5",  # Fondo gris casi blanco (Gris "Google")
            fg="#212529",  # Texto casi negro
            insertbackground="black",  # Cursor negro
            padx=15,
            pady=15,
            state='disabled'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        # Entrada de usuario
        input_frame = tk.Frame(self.root, bg="#f0f2f5", pady=15)
        input_frame.pack(fill=tk.X, padx=30)

        self.user_entry = tk.Entry(input_frame, font=("Arial", 12), bd=2)
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10)
        self.user_entry.bind("<Return>", lambda e: self.process_query())

        # Botón de Procesar
        tk.Button(input_frame, text="ANALIZAR", command=self.process_query,
                  bg="#1a73e8", fg="white", font=("Arial", 10, "bold"), padx=25).pack(side=tk.RIGHT, padx=5)

    def load_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.df = pd.read_csv(file_path)
            # Limpieza básica
            self.df.columns = [c.strip().lower() for c in self.df.columns]
            if 'total' in self.df.columns:
                self.df['total'] = pd.to_numeric(self.df['total'], errors='coerce').fillna(0)
            if 'cantidad' in self.df.columns:
                self.df['cantidad'] = pd.to_numeric(self.df['cantidad'], errors='coerce').fillna(0)

            # Crear Agente de Pandas para cálculos exactos
            self.agent = create_pandas_dataframe_agent(
                self.llm,
                self.df,
                verbose=True,
                allow_dangerous_code=True,
                # max_iterations=3,
                handle_parsing_errors=True
            )

            self.status_label.config(text=f"✅ Datos cargados: {len(self.df)} transacciones encontradas.", fg="green")
            self.log_message("Sistema", "Base de datos cargada. Puedes pedir cálculos exactos o análisis estratégicos.")

    def log_message(self, sender, msg):
        self.chat_display.config(state='normal')
        color = "#0078D4" if sender == "Tú" else "#444444"

        self.chat_display.tag_config(sender, foreground=color, font=("Segoe UI", 11, "bold"))

        self.chat_display.insert(tk.END, f"{sender}: ", sender)
        self.chat_display.insert(tk.END, f"{msg}\n\n")

        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def process_query(self):
        query = self.user_entry.get()
        if not query or self.df is None: return

        self.log_message("Tú", query)
        self.user_entry.delete(0, tk.END)

        # Detectar si es una pregunta estratégica o de cálculo
        if any(word in query.lower() for word in ["opinas", "estrategia", "resumen", "consejo", "por qué"]):
            threading.Thread(target=self.run_ollama_strategic, args=(query,), daemon=True).start()
        else:
            threading.Thread(target=self.run_pandas_exact, args=(query,), daemon=True).start()

    def run_pandas_exact(self, query):
        try:
            # Agregamos un recordatorio de formato en cada consulta
            full_query = f"{query}. Responde siempre iniciando con 'Final Answer:'"
            response = self.agent.invoke({"input": full_query})

            # Extraer la respuesta de forma segura
            ans = response.get("output", "No se pudo obtener una respuesta clara.")
            if "Final Answer:" in ans:
                ans = ans.split("Final Answer:")[-1].strip()

            self.root.after(0, lambda: self.log_message("Analista (Cálculo)", ans))

        except Exception as e:
            # Si el agente falla pero imprimió la respuesta en consola (error de parsing)
            err_str = str(e)
            if "Final Answer:" in err_str:
                ans = err_str.split("Final Answer:")[-1].strip().split("\n")[0]
                self.root.after(0, lambda: self.log_message("Analista (Cálculo)", ans))
            else:
                self.root.after(0, lambda: self.log_message("Sistema", f"Error de proceso: Reintente la consulta."))
        finally:
            # Esto es vital: Reactivar el botón o limpiar el estado si fuera necesario
            pass

    def run_pandas_exact_RESP(self, query):
        try:
            # Agente para precisión numérica
            res = self.agent.invoke({"input": query})
            self.root.after(0, lambda: self.log_message("Analista (Cálculo)", res["output"]))
        except Exception as e:
            self.root.after(0, lambda: self.log_message("Error",
                                                        "No pude procesar el cálculo. Intenta ser más específico."))

    def run_ollama_strategic(self, query):
        # 1. Calculamos datos REALES con Pandas para "anclar" a la IA
        # Filtramos por las ubicaciones de mascotas que me diste
        df_mascotas = self.df[self.df['ubicacion'].str.contains('MASCOTA - T|MASCOTA- CEL', na=False)]
        df_bienestar = self.df[~self.df['ubicacion'].str.contains('MASCOTA - T|MASCOTA- CEL', na=False)]

        top_articulos = self.df.groupby('articulo')['cantidad'].sum().nlargest(5).to_string()
        mejores_vendedores_bienestar = df_bienestar.groupby('vendedor')['total'].sum().nlargest(5).to_string()

        # 2. Construimos el contexto blindado
        contexto_real = f"""
            ESTA ES LA INFORMACIÓN REAL DEL ARCHIVO (NO INVENTES NOMBRES):
            - Ubicaciones de VETERINARIA/MASCOTAS: 'MASCOTA - T' y 'MASCOTA- CEL'.
            - Top 5 Artículos Globales (Real):
            {top_articulos}

            - Top 5 Vendedores de BIENESTAR SEXUAL (Real):
            {mejores_vendedores_bienestar}

            - Resumen Mascotas: Total unidades vendidas en veterinaria: {df_mascotas['cantidad'].sum()}
            """

        # 3. El Prompt con instrucciones de "No Alucinación"
        full_prompt = (
            f"{contexto_real}\n\n"
            f"Pregunta del usuario: {query}\n\n"
            "INSTRUCCIONES CRÍTICAS:\n"
            "1. Usa ÚNICAMENTE los nombres de artículos y vendedores que aparecen arriba.\n"
            "2. Si un dato no está en el resumen, di 'Dato no disponible' en lugar de inventar.\n"
            "3. Recuerda que MASCOTA - T y MASCOTA- CEL son la división de veterinaria.\n"
            "Responde en español con formato ejecutivo."
        )

        try:
            res = self.llm.invoke(full_prompt)
            self.root.after(0, lambda: self.log_message("Ollama (Estrategia)", res))
        except Exception as e:
            self.root.after(0, lambda: self.log_message("Error", "Ollama no respondió."))


if __name__ == "__main__":
    root = tk.Tk()
    app = SuperAnalistaIA(root)
    root.mainloop()