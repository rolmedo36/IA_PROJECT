#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA COMERCIAL PRECISO v8.6 - RESÚMENES MENSUALES NATURALES
✓ Nuevo: "ventas enero 2026" → Resumen completo del mes
✓ Resumen mensual: totales + TOP 10 productos + TOP 5 vendedores + TOP 5 ubicaciones
✓ Mantiene todas las funcionalidades existentes (comillas, comparativas, rangos)
✓ Sin dependencia de Ollama/IA - 100% Pandas
"""
import os
import sys
import pandas as pd
import re
import customtkinter as ctk
from tkinter import messagebox, filedialog, END
from datetime import datetime
import threading
import subprocess
import traceback

# ==================== CONFIGURACIÓN ====================
os.environ["TOKENIZERS_PARALLELISM"] = "false"

COLOR_FONDO = "#0a0a0a"
COLOR_TEXTO = "#ffffff"
COLOR_ENTRY = "#1a1a1a"
COLOR_BOTON = "#0066cc"
COLOR_BOTON_HOVER = "#0055aa"
COLOR_EXITO = "#00aa00"
COLOR_ERROR = "#cc0000"
COLOR_SECCION = "#1e3a5f"
COLOR_NETSUITE = "#8a2be2"

MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'set': 9, 'oct': 10,
    'nov': 11, 'dic': 12
}

MESES_ES_NOMBRES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}


class SistemaVentasIA:
    def __init__(self):
        self.df = None

    def cargar_datos(self, ruta_archivo):
        """Carga y normaliza datos"""
        try:
            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    self.df = pd.read_csv(
                        ruta_archivo,
                        encoding=enc,
                        sep=',',
                        on_bad_lines='skip',
                        thousands=None,
                        decimal='.'
                    )
                    if not self.df.empty:
                        break
                except Exception:
                    continue

            if self.df is None or self.df.empty:
                raise Exception("No se pudo cargar el archivo CSV")

            self.df.columns = [self._normalizar_columna(c) for c in self.df.columns]

            cols_esperadas = ['transaccion', 'fecha', 'vendedor', 'ubicacion', 'id_articulo', 'articulo', 'marca',
                              'cantidad', 'precio_publico', 'total']
            faltantes = [c for c in cols_esperadas if c not in self.df.columns]
            if faltantes:
                raise Exception(f"Columnas faltantes: {faltantes}")

            self.df['fecha'] = pd.to_datetime(self.df['fecha'], format='mixed', dayfirst=True, errors='coerce')
            self.df['anio'] = self.df['fecha'].dt.year
            self.df['mes'] = self.df['fecha'].dt.month
            self.df['dia'] = self.df['fecha'].dt.day

            self.df['cantidad'] = pd.to_numeric(self.df['cantidad'], errors='coerce').fillna(0)
            self.df['total'] = pd.to_numeric(self.df['total'], errors='coerce').fillna(0)
            self.df['precio_publico'] = pd.to_numeric(self.df['precio_publico'], errors='coerce').fillna(0)

            self.df['articulo'] = self.df['articulo'].fillna('SIN_DESCRIPCION').astype(str).str.strip().replace('',
                                                                                                                'SIN_DESCRIPCION')
            self.df['vendedor_normalizado'] = self.df['vendedor'].fillna('').astype(str).apply(
                lambda x: re.split(r'\s+', x.strip().upper())[0] if x.strip() else 'SIN_VENDEDOR'
            )
            self.df['ubicacion_normalizada'] = self.df['ubicacion'].fillna('').astype(str).apply(
                self._normalizar_ubicacion)

            total_registros = len(self.df)
            total_piezas = int(self.df['cantidad'].sum())
            total_ventas = self.df['total'].sum()
            total_transacciones = self.df['transaccion'].nunique()

            return True, (
                f"✓ Datos cargados correctamente ({total_registros:,} registros)\n"
                f"   • Periodo: {self.df['fecha'].min().strftime('%d/%m/%Y')} a {self.df['fecha'].max().strftime('%d/%m/%Y')}\n"
                f"   • Piezas totales: {total_piezas:,}\n"
                f"   • Ventas totales: ${total_ventas:,.2f}\n"
                f"   • Transacciones: {total_transacciones:,}"
            )

        except Exception as e:
            return False, f"Error al cargar datos: {str(e)}"

    def _normalizar_columna(self, col):
        col = str(col).lower().strip()
        reemplazos = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n'}
        for a, b in reemplazos.items():
            col = col.replace(a, b)
        return col.replace(' ', '_')

    def _normalizar_ubicacion(self, ub):
        ub = str(ub).upper().strip()
        if 'MASCOTA' in ub and ('TIENDA' in ub or 'T ' in ub or '- T' in ub):
            return 'MASCOTA - TIENDA'
        elif 'MASCOTA' in ub:
            return 'MASCOTA - CEL'
        elif 'CELESTERRA' in ub or 'CELES' in ub:
            base = re.sub(r'\s*-\s*CELESTERRA.*|CELESTERRA.*', '', ub).strip()
            return f"{base} - CELESTERRA" if base else 'CELESTERRA'
        elif 'CEL' in ub and 'MASCOTA' not in ub and 'CELESTERRA' not in ub:
            base = re.sub(r'\s*-\s*CEL.*|CEL.*', '', ub).strip()
            return f"{base} - CEL" if base else 'OTRO CEL'
        elif 'PLAZA' in ub:
            match = re.search(r'PLAZA\s+([A-ZÁÉÍÓÚ\s]+)', ub)
            if match:
                plaza = match.group(1).strip()
                if 'ALAMO' in plaza:
                    return 'Plaza Alamo - CELESTERRA'
                elif 'MADISON' in plaza:
                    return 'Plaza Madison - CEL'
                elif 'SAUCES' in plaza:
                    return 'Plaza Sauces - CEL'
                elif any(x in plaza for x in ['CONCHITAS', 'ZENTER', 'TORRES']):
                    return f"Plaza {plaza} - CEL"
                else:
                    return f"Plaza {plaza}"
            return ub
        elif 'ARCOS' in ub:
            return 'Arcos - C'
        elif 'PATRIA' in ub:
            return 'Patria - CEL'
        elif 'FEDERALISMO' in ub:
            return 'Federalismo - CEL'
        elif 'HIDALGO' in ub:
            return 'Hidalgo - CEL'
        elif 'NACIONES' in ub:
            return 'Naciones Unidas - CEL'
        elif 'CAMINO REAL' in ub:
            return 'Camino Real - C'
        else:
            return ub

    def _parse_rango_fechas(self, texto):
        """Extrae rango de fechas personalizado"""
        texto = texto.lower().strip()
        patron_rango = r'(?:del\s+)?(\d{1,2})\s*(?:al|a|de|del)\s*(\d{1,2})\s+([a-z]+)\s*(\d{4})?'
        match = re.search(patron_rango, texto)

        if match:
            dia_inicio = int(match.group(1))
            dia_fin = int(match.group(2))
            mes_texto = match.group(3)
            anio = int(match.group(4)) if match.group(4) else datetime.now().year

            mes_num = MESES_ES.get(mes_texto, None)
            if mes_num is None:
                return None, None, None

            try:
                inicio = pd.Timestamp(year=anio, month=mes_num, day=dia_inicio)
                fin = pd.Timestamp(year=anio, month=mes_num, day=dia_fin)
                periodo_str = f"{dia_inicio}-{dia_fin} {MESES_ES_NOMBRES.get(mes_num, mes_texto.capitalize())} {anio}"
                return inicio, fin, periodo_str
            except ValueError:
                return None, None, None

        return None, None, None

    def _parse_mes_anio(self, texto):
        """Extrae mes/año simple (ej: 'enero 2026')"""
        texto = texto.lower()
        mes_num = None
        anio = None

        for mes_es, num in MESES_ES.items():
            if re.search(rf'\b{mes_es}\b', texto):
                mes_num = num
                break

        anio_match = re.search(r'\b(202[0-9])\b', texto)
        if anio_match:
            anio = int(anio_match.group(1))
        else:
            anio = datetime.now().year

        if mes_num and anio:
            inicio = pd.Timestamp(year=anio, month=mes_num, day=1)
            fin = inicio + pd.offsets.MonthEnd(0)
            mes_nombre = MESES_ES_NOMBRES.get(mes_num, f"Mes {mes_num}")
            return inicio, fin, f"{mes_nombre} {anio}"

        return None, None, None

    def buscar_producto_inteligente(self, busqueda, usar_comillas=False):
        """Busca producto con coincidencia PARCIAL"""
        if self.df is None:
            return None, "❌ No hay datos cargados"

        busqueda = busqueda.strip().lower()
        palabras_busq = [p for p in re.findall(r'\w+', busqueda) if len(p) > 2]

        if not palabras_busq:
            return None, f"⚠️ Búsqueda demasiado corta: '{busqueda}'"

        def calcular_coincidencias(desc):
            desc_lower = desc.lower()
            coincidencias = sum(1 for p in palabras_busq if p in desc_lower)
            return coincidencias / len(palabras_busq)

        self.df['coincidencia'] = self.df['articulo'].apply(calcular_coincidencias)
        coincidentes = self.df[self.df['coincidencia'] > 0.5]

        if len(coincidentes) == 0:
            self.df['similitud'] = self.df['articulo'].apply(
                lambda x: sum(1 for p in palabras_busq if p in x.lower()) / len(palabras_busq)
            )
            top3 = self.df.nlargest(3, 'similitud')[['articulo', 'id_articulo', 'similitud']]
            opciones = "\n".join([
                f"   {i + 1}. {row['articulo']} (ID: {row['id_articulo']}) - Coincidencia: {row['similitud']:.0%}"
                for i, (_, row) in enumerate(top3.iterrows())
            ])
            return None, (
                f"⚠️ Producto '{busqueda}' no encontrado.\n\n"
                f"TOP 3 sugerencias:\n{opciones}\n\n"
                f"💡 Tips:\n"
                f"   • Usa comillas para mayor precisión: \"shumatsu 3 pzas\"\n"
                f"   • Incluye más palabras clave si hay ambigüedad"
            )

        mejor = coincidentes.nlargest(1, 'coincidencia').iloc[0]
        desc_real = mejor['articulo']

        return coincidentes[coincidentes['articulo'] == desc_real], f"✅ Producto encontrado: {desc_real}"

    def _filtrar_por_rango(self, df, inicio, fin):
        """Filtra DataFrame por rango de fechas inclusivo"""
        if inicio is None and fin is None:
            return df

        return df[(df['fecha'] >= inicio) & (df['fecha'] <= fin)]

    def resumen_mensual(self, mes_num, anio):
        """Genera resumen completo de un mes específico"""
        if self.df is None:
            return "❌ No hay datos cargados"

        # Filtrar por mes/año
        df_mes = self.df[(self.df['mes'] == mes_num) & (self.df['anio'] == anio)]

        if len(df_mes) == 0:
            mes_nombre = MESES_ES_NOMBRES.get(mes_num, f"Mes {mes_num}")
            return f"⚠️ No hay ventas registradas para {mes_nombre} {anio}"

        # Métricas generales
        total_piezas = int(df_mes['cantidad'].sum())
        total_ventas = df_mes['total'].sum()
        total_trans = df_mes['transaccion'].nunique()
        ticket_promedio = total_ventas / total_trans if total_trans > 0 else 0

        mes_nombre = MESES_ES_NOMBRES.get(mes_num, f"Mes {mes_num}")
        resultado = f"✅ RESUMEN DE VENTAS: {mes_nombre} {anio}\n{'=' * 80}\n"
        resultado += f"   • Piezas vendidas: {total_piezas:,}\n"
        resultado += f"   • Ventas totales: ${total_ventas:,.2f}\n"
        resultado += f"   • Transacciones: {total_trans:,}\n"
        resultado += f"   • Ticket promedio: ${ticket_promedio:,.2f}\n\n"

        # TOP 10 productos
        top_prod = df_mes.groupby('articulo')['cantidad'].sum().nlargest(10).to_dict()
        resultado += f"📦 TOP 10 PRODUCTOS:\n"
        for i, (prod, cant) in enumerate(top_prod.items(), 1):
            prod_str = str(prod).strip()
            if len(prod_str) > 45:
                prod_str = prod_str[:42] + "..."
            resultado += f"   {i:2d}. {prod_str:<45} {int(cant):>6,} pz\n"

        # TOP 5 vendedores
        top_vend = df_mes.groupby('vendedor_normalizado')['cantidad'].sum().nlargest(5).to_dict()
        resultado += f"\n👔 TOP 5 VENDEDORES:\n"
        for i, (vend, cant) in enumerate(top_vend.items(), 1):
            nombre_real = self.df[self.df['vendedor_normalizado'] == vend]['vendedor'].iloc[0]
            nombre_corto = ' '.join(nombre_real.split()[:2])
            resultado += f"   {i}. {nombre_corto:<20} {int(cant):>6,} pz\n"

        # TOP 5 ubicaciones
        top_ub = df_mes.groupby('ubicacion_normalizada')['cantidad'].sum().nlargest(5).to_dict()
        resultado += f"\n📍 TOP 5 UBICACIONES:\n"
        for i, (ub, cant) in enumerate(top_ub.items(), 1):
            resultado += f"   {i}. {ub:<30} {int(cant):>6,} pz\n"

        return resultado

    def ventas_por_producto(self, producto_busq, inicio=None, fin=None, usar_comillas=False):
        """Ventas detalladas de un producto específico"""
        if self.df is None:
            return "❌ No hay datos cargados"

        df_producto, msg_busqueda = self.buscar_producto_inteligente(producto_busq, usar_comillas)

        if df_producto is None:
            return msg_busqueda

        desc_real = df_producto['articulo'].iloc[0]
        df_filtrado = self._filtrar_por_rango(df_producto, inicio, fin)
        periodo_str = f" ({inicio.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')})" if inicio and fin else ""

        if len(df_filtrado) == 0:
            return f"⚠️ No hay ventas de '{desc_real}' en el periodo seleccionado{periodo_str}"

        total_piezas = int(df_filtrado['cantidad'].sum())
        total_ventas = df_filtrado['total'].sum()
        transacciones = df_filtrado['transaccion'].nunique()

        resultado = f"{msg_busqueda}\n"
        resultado += f"📦 PRODUCTO: {desc_real}{periodo_str}\n{'=' * 80}\n"
        resultado += f"   • Piezas vendidas: {total_piezas:,}\n"
        resultado += f"   • Ventas totales: ${total_ventas:,.2f}\n"
        resultado += f"   • Transacciones: {transacciones:,}\n\n"

        top_vend = df_filtrado.groupby('vendedor_normalizado')['cantidad'].sum().nlargest(5).to_dict()
        resultado += f"👔 TOP 5 VENDEDORES:\n"
        for i, (vend, cant) in enumerate(top_vend.items(), 1):
            nombre_real = self.df[self.df['vendedor_normalizado'] == vend]['vendedor'].iloc[0]
            nombre_corto = ' '.join(nombre_real.split()[:2])
            resultado += f"   {i}. {nombre_corto:<20} {int(cant):>6,} pz\n"

        top_ub = df_filtrado.groupby('ubicacion_normalizada')['cantidad'].sum().nlargest(5).to_dict()
        resultado += f"\n📍 TOP 5 UBICACIONES:\n"
        for i, (ub, cant) in enumerate(top_ub.items(), 1):
            resultado += f"   {i}. {ub:<30} {int(cant):>6,} pz\n"

        return resultado

    def comparar_productos_rangos(self, producto_busq, rango1_inicio, rango1_fin, rango2_inicio, rango2_fin, rango1_str,
                                  rango2_str, usar_comillas=False):
        """Compara ventas de un producto entre dos rangos de fechas"""
        if self.df is None:
            return "❌ No hay datos cargados"

        df_producto, msg_busqueda = self.buscar_producto_inteligente(producto_busq, usar_comillas)
        if df_producto is None:
            return msg_busqueda

        desc_real = df_producto['articulo'].iloc[0]

        df_p1 = self._filtrar_por_rango(df_producto, rango1_inicio, rango1_fin)
        piezas1 = int(df_p1['cantidad'].sum()) if len(df_p1) > 0 else 0
        ventas1 = df_p1['total'].sum() if len(df_p1) > 0 else 0
        trans1 = df_p1['transaccion'].nunique() if len(df_p1) > 0 else 0

        df_p2 = self._filtrar_por_rango(df_producto, rango2_inicio, rango2_fin)
        piezas2 = int(df_p2['cantidad'].sum()) if len(df_p2) > 0 else 0
        ventas2 = df_p2['total'].sum() if len(df_p2) > 0 else 0
        trans2 = df_p2['transaccion'].nunique() if len(df_p2) > 0 else 0

        diff_piezas = piezas2 - piezas1
        diff_ventas = ventas2 - ventas1
        pct_piezas = (diff_piezas / piezas1 * 100) if piezas1 > 0 else 0
        pct_ventas = (diff_ventas / ventas1 * 100) if ventas1 > 0 else 0

        resultado = f"{msg_busqueda}\n"
        resultado += f"📊 COMPARATIVA: {desc_real}\n{'=' * 80}\n"
        resultado += f"{'Periodo':<25} {'Piezas':>10} {'Ventas':>15} {'Trans':>6}\n"
        resultado += f"{'-' * 80}\n"
        resultado += f"{rango1_str:<25} {piezas1:>10,} ${ventas1:>14,.2f} {trans1:>6}\n"
        resultado += f"{rango2_str:<25} {piezas2:>10,} ${ventas2:>14,.2f} {trans2:>6}\n"
        resultado += f"{'-' * 80}\n"
        resultado += f"{'Diferencia':<25} {diff_piezas:>10,} ${diff_ventas:>14,.2f}\n"
        resultado += f"{'Crecimiento %':<25} {pct_piezas:>9.1f}% {pct_ventas:>14.1f}%\n"

        if diff_piezas > 0:
            resultado += f"\n📈 ¡{desc_real} vendió {abs(diff_piezas):,} piezas MÁS en {rango2_str}!"
        elif diff_piezas < 0:
            resultado += f"\n📉 {desc_real} vendió {abs(diff_piezas):,} piezas MENOS en {rango2_str}"
        else:
            resultado += f"\n➡️  Ventas estables entre periodos"

        return resultado


# ==================== INTERFAZ GRÁFICA ====================
class AplicacionVentas(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.sistema = SistemaVentasIA()
        self.setup_ui()
        self.extraccion_en_progreso = False

    def setup_ui(self):
        self.title("📊 Analista Comercial Preciso v8.6 - Resúmenes Mensuales")
        self.geometry("1150x880")
        self.configure(fg_color=COLOR_FONDO)

        ctk.CTkLabel(
            self,
            text="🔍 Análisis Comercial con Resúmenes Mensuales Naturales",
            font=("Helvetica", 24, "bold"),
            text_color=COLOR_TEXTO
        ).pack(pady=15)

        frame_carga = ctk.CTkFrame(self, fg_color=COLOR_ENTRY)
        frame_carga.pack(fill="x", padx=20, pady=5)

        self.lbl_archivo = ctk.CTkLabel(
            frame_carga,
            text="📁 No hay archivo cargado",
            text_color="#aaaaaa",
            font=("Helvetica", 12)
        )
        self.lbl_archivo.pack(side="left", padx=10, pady=5)

        ctk.CTkButton(
            frame_carga,
            text="📥 Extraer datos de NetSuite",
            command=self.extraer_datos_netsuite,
            fg_color=COLOR_NETSUITE,
            hover_color="#6a1b9a",
            width=220,
            height=35,
            font=("Helvetica", 13, "bold")
        ).pack(side="right", padx=5, pady=5)

        ctk.CTkButton(
            frame_carga,
            text="📥 Cargar CSV NetSuite",
            command=self.cargar_csv,
            fg_color=COLOR_BOTON,
            hover_color=COLOR_BOTON_HOVER,
            width=190,
            height=35
        ).pack(side="right", padx=10, pady=5)

        frame_ejemplos = ctk.CTkFrame(self, fg_color=COLOR_SECCION)
        frame_ejemplos.pack(fill="x", padx=20, pady=10)

        ejemplos_txt = (
            "💡 NUEVO: Consultas naturales para resúmenes mensuales:\n"
            "   • 'ventas enero 2026'          → Resumen completo del mes\n"
            "   • 'ventas febrero 2026'        → Resumen de febrero\n"
            "   • 'compara noe enero vs febrero 2026' → Comparativa de vendedor\n"
            '   • compara "shumatsu 3 pzas" 1 al 10 enero vs 1 al 10 febrero 2026'
        )
        ctk.CTkLabel(
            frame_ejemplos,
            text=ejemplos_txt,
            text_color=COLOR_TEXTO,
            font=("Helvetica", 12),
            justify="left"
        ).pack(padx=15, pady=10)

        ctk.CTkLabel(
            self,
            text='💬 Consulta natural (ej: "ventas enero 2026" o "compara noe enero vs febrero 2026"):',
            text_color=COLOR_TEXTO,
            font=("Helvetica", 14)
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.entrada = ctk.CTkEntry(
            self,
            placeholder_text='Ej: ventas enero 2026 | compara "shumatsu 3 pzas" 1 al 10 enero vs 1 al 10 febrero 2026',
            font=("Helvetica", 14),
            height=55,
            fg_color=COLOR_ENTRY,
            text_color=COLOR_TEXTO
        )
        self.entrada.pack(fill="x", padx=20, pady=5)
        self.entrada.bind("<Return>", self.procesar_pregunta)

        frame_botones = ctk.CTkFrame(self, fg_color=COLOR_FONDO)
        frame_botones.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            frame_botones,
            text="🔍 Consultar",
            command=self.procesar_pregunta,
            fg_color=COLOR_BOTON,
            hover_color=COLOR_BOTON_HOVER,
            width=140,
            height=42,
            font=("Helvetica", 14, "bold")
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_botones,
            text="🧹 Limpiar",
            command=self.limpiar,
            fg_color="#880000",
            hover_color="#aa0000",
            width=120,
            height=38
        ).pack(side="right", padx=5)

        ctk.CTkLabel(
            self,
            text="📝 Resultados:",
            text_color=COLOR_TEXTO,
            font=("Helvetica", 14, "bold")
        ).pack(anchor="w", padx=20, pady=(10, 5))

        frame_resultados = ctk.CTkFrame(self, fg_color=COLOR_ENTRY)
        frame_resultados.pack(fill="both", expand=True, padx=20, pady=5)

        self.texto = ctk.CTkTextbox(
            frame_resultados,
            font=("Courier New", 13),
            fg_color=COLOR_FONDO,
            text_color=COLOR_TEXTO,
            wrap="word"
        )
        self.texto.pack(fill="both", expand=True, padx=5, pady=5)

        self.status = ctk.CTkLabel(
            self,
            text="Estado: Listo | ✅ v8.6 con resúmenes mensuales naturales",
            text_color=COLOR_EXITO,
            font=("Helvetica", 11, "bold")
        )
        self.status.pack(anchor="w", padx=20, pady=5)

        self._mostrar_bienvenida()

    def _mostrar_bienvenida(self):
        bienvenida = (
            "🌟 ¡BIENVENIDO AL SISTEMA DE ANÁLISIS COMERCIAL AVANZADO!\n"
            f"{'=' * 80}\n\n"
            "✨ NUEVA CARACTERÍSTICA v8.6:\n"
            "   ✅ ¡NUEVO! Consultas naturales para resúmenes mensuales:\n"
            "      → 'ventas enero 2026' = Resumen completo del mes ✅\n"
            "      → 'ventas febrero 2026' = Resumen de febrero ✅\n"
            '   ✅ Comillas para precisión: "shumatsu 3 pzas" ≠ "shot shumatsu"\n'
            "   ✅ Comparativas por rangos: 1-10 enero vs 1-10 febrero\n"
            "   ✅ Extracción automática de NetSuite con un clic\n\n"
            "💡 EJEMPLOS DE USO:\n"
            "   • ventas enero 2026\n"
            "   • ventas febrero 2026\n"
            '   • compara "shumatsu 3 pzas" 1 al 10 enero vs 1 al 10 febrero 2026\n'
            "   • ventas de noe enero 2026\n\n"
            f"{'=' * 80}\n"
        )
        self.texto.insert("end", bienvenida)

    def cargar_csv(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar export de NetSuite",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if ruta:
            self.lbl_archivo.configure(text=f"📁 {os.path.basename(ruta)}")
            self.status.configure(text="Cargando datos...", text_color=COLOR_BOTON)
            self.update()

            exito, msg = self.sistema.cargar_datos(ruta)
            if exito:
                self.status.configure(text="✓ Datos cargados correctamente", text_color=COLOR_EXITO)
                self.texto.insert("end", f"\n{'=' * 80}\n{msg}\n")
                self.texto.see(END)
            else:
                self.status.configure(text=f"Error: {msg[:80]}...", text_color=COLOR_ERROR)
                messagebox.showerror("Error", msg)

    def extraer_datos_netsuite(self):
        """Ejecuta ia_ventas_extrae.py en hilo separado"""
        if self.extraccion_en_progreso:
            messagebox.showinfo("Información", "Extracción ya en progreso. Espera a que termine.")
            return

        self.extraccion_en_progreso = True
        self.status.configure(text="🔄 Extrayendo datos de NetSuite...", text_color=COLOR_NETSUITE)
        self.update()

        def tarea_extraccion():
            error_msg = None
            archivo_generado = None

            try:
                try:
                    if 'ia_ventas_extrae' in sys.modules:
                        del sys.modules['ia_ventas_extrae']

                    from ia_ventas_extrae import main as extraer_main
                    resultado = extraer_main(fecha_inicio='01/01/2026')

                    if resultado and isinstance(resultado, dict) and resultado.get('success'):
                        archivo_generado = resultado.get('archivo', 'ventas_ia.csv')
                    else:
                        error_msg = resultado.get('error', 'Error desconocido en extracción') if isinstance(resultado,
                                                                                                            dict) else "Resultado inválido de main()"

                except (ImportError, ModuleNotFoundError, AttributeError) as e1:
                    try:
                        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ia_ventas_extrae.py')
                        if not os.path.exists(script_path):
                            raise FileNotFoundError(f"No se encontró ia_ventas_extrae.py en {script_path}")

                        resultado = subprocess.run(
                            [sys.executable, script_path],
                            capture_output=True,
                            text=True,
                            timeout=300,
                            cwd=os.path.dirname(script_path)
                        )

                        if resultado.returncode == 0:
                            match = re.search(r'(?:archivo\s*generado|generado|saved|exportado)[:\s]*([^\s]+\.csv)',
                                              resultado.stdout, re.IGNORECASE)
                            archivo_generado = match.group(1) if match else 'ventas_ia.csv'
                        else:
                            stderr_msg = resultado.stderr.strip() if resultado.stderr else f"Código de error: {resultado.returncode}"
                            error_msg = stderr_msg[:500]

                    except Exception as e2:
                        error_msg = f"Error subprocess: {str(e2)}"

            except Exception as e3:
                error_msg = f"Error inesperado: {str(e3)}\n{traceback.format_exc()[:300]}"

            finally:
                if error_msg:
                    self.after(0, lambda msg=error_msg: self._extraccion_fallida(msg))
                elif archivo_generado:
                    self.after(0, lambda archivo=archivo_generado: self._extraccion_exitosa(archivo))
                else:
                    self.after(0,
                               lambda: self._extraccion_fallida("Extracción completada pero no se generó archivo CSV"))

                self.after(0, lambda: setattr(self, 'extraccion_en_progreso', False))

        threading.Thread(target=tarea_extraccion, daemon=True).start()

    def _extraccion_exitosa(self, archivo_generado):
        rutas_posibles = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), archivo_generado),
            os.path.abspath(archivo_generado)
        ]

        ruta_valida = None
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                ruta_valida = ruta
                break

        if ruta_valida:
            self.lbl_archivo.configure(text=f"📁 {os.path.basename(ruta_valida)} (NetSuite)")
            exito, msg = self.sistema.cargar_datos(ruta_valida)
            if exito:
                self.status.configure(text=f"✓ Datos extraídos y cargados: {os.path.basename(ruta_valida)}",
                                      text_color=COLOR_EXITO)
                self.texto.insert("end", f"\n{'=' * 80}\n✅ EXTRACCIÓN EXITOSA DE NETSUITE\n{msg}\n")
                self.texto.see(END)
                messagebox.showinfo("Éxito", f"Datos extraídos correctamente:\n{os.path.basename(ruta_valida)}")
            else:
                self.status.configure(text=f"⚠️ Archivo generado pero error al cargar", text_color=COLOR_ERROR)
                messagebox.showwarning("Advertencia", f"Archivo generado pero no se pudo cargar:\n{msg}")
        else:
            self.status.configure(text=f"⚠️ Archivo no encontrado: {archivo_generado}", text_color=COLOR_ERROR)
            messagebox.showerror("Error", f"No se encontró el archivo generado:\n{archivo_generado}")

    def _extraccion_fallida(self, error_msg):
        self.status.configure(text=f"❌ Error en extracción", text_color=COLOR_ERROR)
        mensaje_corto = error_msg[:200] + "..." if len(error_msg) > 200 else error_msg
        self.texto.insert("end", f"\n{'=' * 80}\n❌ ERROR EN EXTRACCIÓN DE NETSUITE:\n{mensaje_corto}\n")
        self.texto.see(END)
        messagebox.showerror("Error de Extracción", f"No se pudieron extraer los datos:\n{mensaje_corto}")

    def procesar_pregunta(self, event=None):
        pregunta = self.entrada.get().strip()
        if not pregunta:
            messagebox.showwarning("Advertencia", "Escribe una consulta primero")
            return

        self.status.configure(text="Procesando...", text_color=COLOR_BOTON)
        self.update()

        pregunta_lower = pregunta.lower()
        resultado = None

        # === NUEVO: DETECCIÓN DE "VENTAS [MES] [AÑO]" ===
        if 'ventas' in pregunta_lower and any(mes in pregunta_lower for mes in MESES_ES.keys()):
            # Extraer mes/año
            inicio, fin, periodo_str = self.sistema._parse_mes_anio(pregunta_lower)
            if inicio and fin:
                mes_num = inicio.month
                anio = inicio.year
                resultado = self.sistema.resumen_mensual(mes_num, anio)
            else:
                resultado = "⚠️ No pude identificar el mes/año. Usa formato: 'ventas enero 2026'"

        # === DETECCIÓN DE COMILLAS ===
        elif '"' in pregunta_lower:
            usar_comillas = True
            comillas_match = re.search(r'"([^"]+)"', pregunta)
            producto_busq = comillas_match.group(1).strip() if comillas_match else None

            # Detección de comparativa
            if 'compara' in pregunta_lower and ('vs' in pregunta_lower or 'contra' in pregunta_lower) and producto_busq:
                rangos = []
                texto_temp = pregunta_lower

                for _ in range(2):
                    r_inicio, r_fin, r_str = self.sistema._parse_rango_fechas(texto_temp)
                    if r_inicio and r_fin:
                        rangos.append((r_inicio, r_fin, r_str))
                        texto_temp = re.sub(rf'\d+\s*al\s*\d+\s+\w+\s*\d*', '', texto_temp, count=1)
                    if len(rangos) >= 2:
                        break

                if len(rangos) == 2:
                    resultado = self.sistema.comparar_productos_rangos(
                        producto_busq,
                        rangos[0][0], rangos[0][1],
                        rangos[1][0], rangos[1][1],
                        rangos[0][2], rangos[1][2],
                        usar_comillas
                    )
                else:
                    resultado = "⚠️ Necesito dos rangos de fechas para comparar"

            # Ventas de producto
            elif 'ventas' in pregunta_lower and producto_busq:
                inicio, fin, _ = self.sistema._parse_rango_fechas(pregunta_lower)
                if inicio is None or fin is None:
                    inicio, fin, _ = self.sistema._parse_mes_anio(pregunta_lower)

                if inicio and fin:
                    resultado = self.sistema.ventas_por_producto(producto_busq, inicio, fin, usar_comillas)
                else:
                    resultado = f"⚠️ Especifica un periodo (ej: '\"shumatsu 3 pzas\" enero 2026')"

        # === CONSULTA NO RECONOCIDA ===
        else:
            resultado = (
                "❓ Consulta no reconocida. Usa formatos como:\n"
                "   • ventas enero 2026          → Resumen completo del mes ✅\n"
                "   • ventas febrero 2026        → Resumen de febrero ✅\n"
                '   • compara "shumatsu 3 pzas" 1 al 10 enero vs 1 al 10 febrero 2026\n'
                '   • ventas de "shot shumatsu" enero 2026\n'
                "   • ventas de noe enero 2026\n\n"
                "💡 Tips:\n"
                "   • Para resumen mensual: 'ventas [mes] [año]'\n"
                '   • Para producto específico: usa comillas "nombre producto"\n'
                "   • Para comparar: 'compara [producto/vendedor] [periodo1] vs [periodo2]'"
            )

        self._mostrar_respuesta(pregunta, resultado)

    def _mostrar_respuesta(self, pregunta, respuesta):
        self.texto.insert("end", f"\n{'=' * 80}\n👤 Consulta: {pregunta}\n\n{respuesta}\n")
        self.texto.see(END)
        self.status.configure(text="✓ Listo - Datos 100% reales", text_color=COLOR_TEXTO)
        self.entrada.delete(0, END)

    def limpiar(self):
        self.texto.delete("1.0", END)
        self._mostrar_bienvenida()


# ==================== EJECUCIÓN ====================
if __name__ == "__main__":
    dependencias = []
    try:
        import pandas
    except ImportError:
        dependencias.append("pandas")

    try:
        import customtkinter
    except ImportError:
        dependencias.append("customtkinter")

    if dependencias:
        print("❌ FALTAN DEPENDENCIAS:")
        print(f"   pip install {' '.join(dependencias)} openpyxl")
        sys.exit(1)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = AplicacionVentas()
    app.mainloop()