import pandas as pd
import sqlite3

# Carga tu CSV
df = pd.read_csv('ventas_ia.csv')

# Limpieza rápida de columnas para que SQL no de problemas
df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

# Crear conexión y guardar
conn = sqlite3.connect('ventas_netsuite.db')
df.to_sql('ventas', conn, if_exists='replace', index=False)
conn.close()
print("✅ Base de datos SQLite creada con éxito.")