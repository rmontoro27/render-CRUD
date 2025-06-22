import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from crud.crudAdmintrador import AdminCRUD


load_dotenv()

EMAIL_ORIGEN = os.getenv("miraisolutions@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def enviar_notificacion_pago(nombre, correo, periodo, sueldo_neto, fecha_pago):
    cuerpo = f"""
    Hola {nombre},

    Tu recibo de sueldo correspondiente al periodo {periodo} ya está disponible.

    Sueldo neto: ${sueldo_neto}
    Fecha de pago: {fecha_pago}

    Podés revisarlo ingresando al sistema.

    Saludos,  
    RRHH - Mirai Solutions
    """

    msg = MIMEText(cuerpo)
    msg['Subject'] = f'Recibo de sueldo - {periodo}'
    msg['From'] = EMAIL_ORIGEN
    msg['To'] = correo

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
        server.send_message(msg)

def enviar_correo_generico(tipo, id_empleado, mensaje):
    empleado = AdminCRUD.obtener_empleado_por_id(id_empleado)
    if not empleado:
        raise ValueError("Empleado no encontrado")

    asunto = f'Notificación - {tipo.capitalize()}'

    msg = MIMEText(mensaje)
    msg['Subject'] = asunto
    msg['From'] = EMAIL_ORIGEN
    msg['To'] = empleado.correo

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
        server.send_message(msg)
