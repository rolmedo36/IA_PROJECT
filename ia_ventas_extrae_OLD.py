import sqlite3
import sys

import requests
import json
import pandas as pd
import msal
from oauthlib import oauth1
from requests_oauthlib import OAuth1Session
from datetime import date
from datetime import timedelta, datetime
import csv
import openpyxl
from openpyxl.styles import Font  # Import the Font class for styling
from openpyxl.chart import BarChart, Reference  # Import the chart classes
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os


def parse_suiteql_response(response, archivo_out, results):
    response_json = json.loads(response.text)

    items = response_json['items']
    offset = response_json['offset']
    count = response_json['count']
    total = response_json['totalResults']

    for ventas in items:
        vtransaccion = ' '
        vestatus = ' '
        vfecha = ' '
        vcliente = ' '
        vubicacion = ' '
        vid_articulo = ' '
        varticulo = ' '
        vmarca = ' '
        vcantidad = ' '
        vimporte_neto = ' '
        vimporte_total = 0
        vid_woocommerce = ''
        vimporte_efectivo = ' '
        vimporte_efectivo_ok = ' '
        vimporte_efectivo_clip = ' '
        vimporte_banorte = ' '
        vimporte_clip_ok = ' '
        vimporte_rappi = ' '
        vimporte_banregio = ' '
        vvendedor = ''
        vid_pos = ''
        vid_pos_tmp = ''
        vprecio_publico = 0

        if 'id_woocommerce' in ventas: vid_woocommerce = ventas['id_woocommerce']
        if 'transaccion' in ventas: vtransaccion = ventas['transaccion']
        if 'estatus' in ventas: vestatus = ventas['estatus']
        if 'fecha' in ventas: vfecha = ventas['fecha']
        if 'cliente' in ventas: vcliente = ventas['cliente']
        if 'ubicacion' in ventas: vubicacion = ventas['ubicacion']
        if 'id_articulo' in ventas: vid_articulo = ventas['id_articulo']
        if 'articulo' in ventas: varticulo = ventas['articulo']
        if 'marca' in ventas: vmarca = ventas['marca']
        if 'tipo_venta' in ventas: vtipo_venta = ventas['tipo_venta']
        if 'cantidad' in ventas: vcantidad = abs(int(ventas['cantidad']))
        if 'importe_neto' in ventas: vimporte_neto = abs(float(ventas['importe_neto']))
        if 'importe_efectivo' in ventas: vimporte_efectivo = ventas['importe_efectivo']
        if 'importe_efectivo_ok' in ventas: vimporte_efectivo_ok = ventas['importe_efectivo_ok']
        if 'importe_efectivo_clip' in ventas: vimporte_efectivo_clip = ventas['importe_efectivo_clip']
        if 'importe_banorte' in ventas: vimporte_banorte = ventas['importe_banorte']
        if 'importe_clip_ok' in ventas: vimporte_clip_ok = ventas['importe_clip_ok']
        if 'importe_rappi' in ventas: vimporte_rappi = ventas['importe_rappi']
        if 'importe_banregio' in ventas: vimporte_banregio = ventas['importe_banregio']
        if 'importe_total' in ventas: vimporte_total = float(ventas['importe_total'])
        if 'vendedor' in ventas: vvendedor = ventas['vendedor']
        if 'id_pos' in ventas: vid_pos_tmp = ventas['id_pos']
        if 'precio_publico' in ventas: vprecio_publico = float(ventas['precio_publico'])

        if len(vid_pos_tmp.split("-")) < 4:
            vid_pos = ''
        else:
            version, serie, vid_pos, f2 = vid_pos_tmp.split("-")
            vid_pos = str(vid_pos[1:])

        varticulo = varticulo.replace(",", " ")
        vtotal = vcantidad * vprecio_publico

        results.append(
            [ vtransaccion, vfecha, vvendedor, vubicacion, vid_articulo, varticulo, vmarca, vcantidad, vprecio_publico, vtotal])

    if response_json["hasMore"]:
        next_link = next(link for link in response_json["links"] if link["rel"] == "next")["href"]
    else:
        next_link = None

    print(next_link)
    return items, offset, count, total, next_link


def run_suiteql_query(query, archivo_out, results):
    client = OAuth1Session(
        # client_key='260a11f980c7a6ef0b46ce5a9777165e31a2ede3c8ed7c39ef254ad3a0bf5cac',
        # client_secret='84e44cea03651c2e1f88082f5726e50615e3b9a04c6ca9e33751b7cbd31b6a11',
        # resource_owner_key='6ef95b3344bf72a309a4ec9756273fc6c70112a836823075de213d1631493b25',
        # resource_owner_secret='62a01a9216a4af5cab43bb0a18a7bfef7cef1d19c25eed2fb1c1d9b74ef59021',
        # signature_type='auth_header',
        # signature_method=oauth1.SIGNATURE_HMAC_SHA256,
        # realm='6248386_SB1',

        client_key='260a11f980c7a6ef0b46ce5a9777165e31a2ede3c8ed7c39ef254ad3a0bf5cac',
        client_secret='81718e06b11c7ab902b20d46cda47c5ab5a8502619294f9a042b6e74ea1d88b9',
        resource_owner_key='445b99a0f9f38ef9284107aded99855b5cfe2631f944e0f724c78d6ab69c1df9',
        resource_owner_secret='6376e567eba2524babf2515b0308b15d9a5fc857d0870e3535ed7b3c30edf245',
        signature_type='auth_header',
        signature_method='HMAC-SHA256',
        # signature_method=oauth1.SIGNATURE_HMAC_SHA256,
        realm='6248386',

    )

    # url = f"https://6248386-sb1.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql"
    url = f"https://6248386.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql"

    headers = {
        "Prefer": "transient",
        "Content-Type": "application/json"
    }

    body = json.dumps({"q": query})
    data = []

    while True:
        response = client.post(url=url, data=body, headers=headers)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"SuiteQL request failed. {e}. Response Body: {response.text}")

        # print(response.text)
        items, offset, count, total, next_link = parse_suiteql_response(response, archivo_out, results)
        print(f"Retrieved {offset + count} of {total} results next_link {next_link}")

        data = data + items

        if next_link:
            url = next_link
        else:
            break

        # return pd.json_normalize(data)
    return pd.json_normalize(data)

def main():
    # mes_ini = datetime.today().replace(day=1).strftime("%d/%m/%Y")
    mes_ini = '09/02/2026'
    archivo = 'ventas_ia.csv'
    results = []

    print("AQUI")
    qry = f"""
        SELECT
            t.tranid as transaccion,
            t.trandate as fecha,
            BUILTIN.DF( t.employee ) as vendedor,
            BUILTIN.DF( tl.location ) as ubicacion,
            REPLACE(tl.item,'"','') as id_articulo,
            BUILTIN.DF( tl.item ) as articulo,
            BUILTIN.DF( i.custitem_ctr_marca ) as marca,
            tl.quantity as cantidad,
            ( SELECT TOP 1 NVL(price,'0') FROM itemPrice ip WHERE ip.item = tl.item AND ip.priceLevelName = 'PRECIO PUBLICO') as precio_publico
        FROM 
            transaction t,
            transactionline tl,
            item i
        WHERE 1=1
            AND (t.type = 'CashSale')
            AND t.trandate >= '{mes_ini}'
            AND tl.transaction = t.id
            AND tl.taxLine = 'F'
            AND tl.mainLine = 'F'
            AND tl.netAmount <> 0
            AND tl.quantity <> 0
            AND i.id = tl.item
            --AND tl.location <> 139 AND tl.location <> 354
        ORDER BY t.trandate, t.id
    """

    run_suiteql_query(qry, archivo, results)
    # Define the CSV file name
    csv_file = archivo

    # Write results to CSV
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)

        # Write header
        writer.writerow(['transaccion', 'fecha', 'vendedor', 'ubicacion', 'id_articulo', 'articulo', 'marca',
                         'cantidad', 'precio_publico', 'total'])
        # Write data rows
        writer.writerows(results)


if __name__ == '__main__':
    results = []
    main()
