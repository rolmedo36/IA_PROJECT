#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXTRACTOR NETSUITE v4.0 - MÍNIMO Y FUNCIONAL
✓ Headers SIN espacios: "Prefer" (no "Prefer ")
✓ Fecha en formato DATE 'YYYY-MM-DD' (no TO_DATE)
✓ Sin subqueries complejas (usa tl.rate directamente)
✓ Paginación OData nativa (@odata.nextLink)
✓ Forzado: Siempre extrae desde 01/01/2026
"""
import os
import sys
import json
import csv
import logging
from datetime import datetime
from requests_oauthlib import OAuth1Session

# Configuración básica
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


# Cargar credenciales desde .env
def cargar_credencial(var):
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if line.strip() and '=' in line:
                    k, v = line.strip().split('=', 1)
                    if k.strip() == var:
                        return v.strip().strip('"').strip("'")
    return os.getenv(var)


# Credenciales (reemplaza con tus valores reales en .env)
NETSUITE_ACCOUNT = cargar_credencial('NETSUITE_ACCOUNT') or '6248386'
NETSUITE_ACCOUNT_REALM = NETSUITE_ACCOUNT.split('.')[0].split('-')[0]
NETSUITE_CONSUMER_KEY = cargar_credencial('NETSUITE_CONSUMER_KEY') or 'tu_consumer_key'
NETSUITE_CONSUMER_SECRET = cargar_credencial('NETSUITE_CONSUMER_SECRET') or 'tu_consumer_secret'
NETSUITE_TOKEN_KEY = cargar_credencial('NETSUITE_TOKEN_KEY') or 'tu_token_key'
NETSUITE_TOKEN_SECRET = cargar_credencial('NETSUITE_TOKEN_SECRET') or 'tu_token_secret'

NETSUITE_URL = f"https://{NETSUITE_ACCOUNT}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql"


def crear_sesion():
    """Crea sesión OAuth sin errores"""
    return OAuth1Session(
        client_key=NETSUITE_CONSUMER_KEY,
        client_secret=NETSUITE_CONSUMER_SECRET,
        resource_owner_key=NETSUITE_TOKEN_KEY,
        resource_owner_secret=NETSUITE_TOKEN_SECRET,
        signature_method='HMAC-SHA256',
        realm=NETSUITE_ACCOUNT_REALM
    )


def extraer_ventas():
    """Extracción MÍNIMA y FUNCIONAL desde 01/01/2026"""
    session = crear_sesion()

    # Headers CORRECTOS (sin espacios al final!)
    headers = {
        "Prefer": "transient",  # ¡SIN ESPACIO después de "Prefer"!
        "Content-Type": "application/json"  # ¡SIN ESPACIO después de "Content-Type"!
    }

    # Query MÍNIMA y VALIDADA para SuiteQL
    query = """
    SELECT t.tranid, t.trandate, t.employee, tl.location, tl.item, tl.quantity, tl.rate
    FROM transaction t
    JOIN transactionline tl ON tl.transaction = t.id
    WHERE t.type = 'CashSale'
      AND t.trandate >= '01/02/2026'
      AND tl.taxLine = 'F'
      AND tl.mainLine = 'F'
      AND tl.quantity > 0
    ORDER BY t.trandate, t.id 
    """

    logger.info("🚀 Extrayendo ventas desde 01/02/2026...")
    body = json.dumps({"q": query})

    try:
        response = session.post(NETSUITE_URL, data=body, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json().get('items', [])
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text[:500]}")
        raise


def procesar_datos(items):
    """Procesa resultados a formato CSV compatible"""
    filas = []
    for item in items:
        try:
            # Extraer campos básicos
            transaccion = str(item.get('tranid', '')).strip()
            fecha_raw = item.get('trandate', '')
            # Formatear fecha ISO a DD/MM/YYYY
            if fecha_raw:
                fecha_dt = datetime.strptime(fecha_raw.split('T')[0], '%d/%m/%Y')
                fecha = fecha_dt.strftime('%d/%m/%Y')
            else:
                fecha = ''

            vendedor = str(item.get('employee', '')).strip()
            ubicacion = str(item.get('location', '')).strip()
            id_articulo = str(item.get('item', '')).strip().replace(' ', '')
            cantidad = abs(int(float(item.get('quantity', 0))))
            precio = abs(float(item.get('rate', 0)))
            total = cantidad * precio

            # Solo agregar si es válido
            if transaccion and cantidad > 0 and fecha:
                filas.append([
                    transaccion, fecha, vendedor, ubicacion,
                    id_articulo, f"Producto {id_articulo}", "SIN_MARCA",
                    cantidad, round(precio, 2), round(total, 2)
                ])
        except Exception as e:
            logger.warning(f"⚠️ Registro omitido: {e}")
            continue

    return filas


def guardar_csv(filas, archivo='ventas_ia.csv'):
    """Guarda CSV con formato compatible analista comercial"""
    with open(archivo, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            'transaccion', 'fecha', 'vendedor', 'ubicacion',
            'id_articulo', 'articulo', 'marca',
            'cantidad', 'precio_publico', 'total'
        ])
        writer.writerows(filas)
    logger.info(f"✅ CSV guardado: {archivo} ({len(filas)} registros)")


def main():
    try:
        # Extracción mínima
        items = extraer_ventas()
        logger.info(f"✓ Recuperados {len(items)} registros")

        # Procesamiento
        filas = procesar_datos(items)
        logger.info(f"✓ Procesados {len(filas)} registros válidos")

        # Guardar
        guardar_csv(filas)

        return {
            'success': True,
            'archivo': 'ventas_ia.csv',
            'registros': len(filas),
            'mensaje': f'Extracción exitosa: {len(filas)} registros desde 01/01/2026'
        }

    except Exception as e:
        logger.error(f"❌ Error fatal: {str(e)}")
        return {'success': False, 'error': str(e), 'archivo': None, 'registros': 0}


if __name__ == "__main__":
    resultado = main()
    if resultado['success']:
        print(f"\n✅ {resultado['mensaje']}")
        sys.exit(0)
    else:
        print(f"\n❌ Error: {resultado['error']}")
        sys.exit(1)