import os

from pydantic import field_validator
#import cv2
#import face_recognition
import numpy as np

from fastapi import FastAPI, HTTPException, Depends
from crud import crudEmpleado, crudAdmintrador
import uuid
from typing import Optional
from datetime import datetime, timedelta, date, time

from crud.crudAdmintrador import AdminCRUD
from crud.crudEmpleado import RegistroHorario
from crud.crudEmpleado import Empleado
from crud.crudNomina import NominaCRUD
from pydantic import BaseModel, Field
from typing import List
from typing import Tuple, List
from .schemas import (EmpleadoResponse, EmpleadoBase, EmpleadoUpdate, NominaResponse,
                      NominaBase, NominaListResponse, EmpleadoNominaRequest, EmpleadoConsulta,
                      EmpleadoIDRequest, EmpleadoPeriodoRequest, EmpleadoIDIntRequest,
                      BuscarEmpleadoRequest, HorasRequest, CalculoNominaRequest)
from fastapi import APIRouter, HTTPException
from crud.database import db
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, status



# Dato biometrico, lo voy a usar para probar el endpoint regitrar horario
# Funcion que tengo en la versión 3 del reco (otro repo)
#def extraer_vector(imagen_bytes: bytes):
#    np_arr = np.frombuffer(imagen_bytes, np.uint8)
 #   imagen_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
  #  vectores = face_recognition.face_encodings(imagen_np)
   # if vectores:
    #    return vectores[0]
    #return None


#def obtenerDatoBiometrico():
 #   ruta_base = os.path.dirname(os.path.abspath(__file__))
  #  ruta_imagen = os.path.join(ruta_base, "../personas/personaAutorizada1.jpg")
   # with open(ruta_imagen, "rb") as imagen:
    #    contenido = imagen.read()
     #   vector_neutro = extraer_vector(contenido)
    #return vector_neutro






class AsistenciaManual(BaseModel):
    id_empleado: int
    tipo: str
    fecha: date
    hora: time
    estado_asistencia: Optional[str] = None

class CalculoNominaRequest(BaseModel):
    id_empleado: int
    periodo: str
    fecha_calculo: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los headers
)


@app.get("/health")
def health_check():
    """
    Verifica el estado de la API y conexión a la base de datos
    Returns:
        {
            "status": "healthy"|"unhealthy",
            "database": true|false,
            "timestamp": "ISO-8601",
            "details": {
                "database_status": "string"
            }
        }
    """
    try:
        # Verificar conexión a la base de datos
        db_ok = db.health_check()

        status = "healthy" if db_ok else "unhealthy"

        return {
            "status": status,
            "database": db_ok,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "database_status": "Connected" if db_ok else "Disconnected"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
""""
@app.post("/empleados/", response_model=EmpleadoResponse)
def crear_empleado(empleado: EmpleadoBase):
    try:
        empleado_creado = AdminCRUD.crear_empleado(empleado)
        return {
            "nombre": empleado.nombre,
            "apellido": empleado.apellido,
            "tipo_identificacion": empleado.tipo_identificacion,
            "numero_identificacion": empleado.numero_identificacion,
            "fecha_nacimiento": empleado.fecha_nacimiento,
            "correo_electronico": empleado.correo_electronico,
            "telefono": empleado.telefono,
            "calle": empleado.calle,
            "numero_calle": empleado.numero_calle,
            "localidad": empleado.localidad,
            "partido": empleado.partido,
            "provincia": empleado.provincia,
            "genero": empleado.genero,
            "pais_nacimiento": empleado.pais_nacimiento,
            "estado_civil": empleado.estado_civil
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
"""


@app.post("/empleados/", response_model=EmpleadoBase)
async def crear_empleado(empleado: EmpleadoBase):
    try:
        print(f"[API] Inicio creación empleado - Datos recibidos:")
        print(f"Nombre: {empleado.nombre}")
        print(f"Apellido: {empleado.apellido}")
        # Agrega logs para otros campos importantes

        empleado_creado = AdminCRUD.crear_empleado(empleado)
        print("[API] Empleado creado exitosamente")
        return empleado_creado
    except ValueError as e:
        print(f"[API] Error de valor: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[API] Error inesperado:\n{tb}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@app.get("/empleados/{numero_identificacion}")
def obtener_empleado(numero_identificacion: str):
    empleado = AdminCRUD.obtener_detalle_empleado(numero_identificacion)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado

# No puedo probarlo porque no hay registros laborales
#@app.post("/registros/")
#def registrar_horario(empleado_id: str, vectorBiometrico: str):
#    try:
 #       registro = RegistroHorario.registrar_asistencia(empleado_id, obtenerDatoBiometrico()) #Voy a probar con un vector predeterminado
  #      return registro
   # except ValueError as e:
    #    raise HTTPException(status_code=400, detail=str(e))

@app.post("/obtener-empleado")
def obtener_empleado(data: EmpleadoConsulta):
    empleado = AdminCRUD.obtener_detalle_empleado(data.numero_identificacion)
    if not empleado:
        return {"mensaje": "Empleado no encontrado"}
    return empleado


@app.delete("/empleados/{id_empleado}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_empleado(
        id_empleado: int,
        empleado_crud: Empleado = Depends()
):
    """
    Elimina un empleado por su ID.

    Devuelve:
    - 204 No Content si se borró correctamente
    - 404 Not Found si el empleado no existe
    - 400 Bad Request si hay un error en la operación
    """
    try:
        borrado_exitoso = empleado_crud.borrar_por_id(id_empleado)
        if not borrado_exitoso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado"
            )
        return EmpleadoResponse(status_code=status.HTTP_204_NO_CONTENT)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/registros/{empleado_id}")
def obtener_registros(
    empleado_id: str,
    año: Optional[int] = None,
    mes: Optional[int] = None
):
    if año and mes:
        registros = RegistroHorario.obtener_registros_mensuales(empleado_id, año, mes)
    else:
        registros = RegistroHorario.obtener_todos_los_registros(empleado_id)
    return [r for r in registros]

@app.get("/registroscompleto/{empleado_id}")
def obtener_registros(empleado_id: str):

    registros = RegistroHorario.obtener_todos_los_registros(empleado_id)
    return [r for r in registros]

# Creo que está bien, tengo que verificarlo con un registro de la base de datos
@app.get("/horas/{empleado_id}")
def calcular_horas(empleado_id: str, año: int, mes: int):
    horas = RegistroHorario.calcular_horas_mensuales(empleado_id, año, mes)
    return {"horas_trabajadas": horas}

# Actualizar datos de empleado
@app.put("/empleados/{empleado_id}/datos-personales")
def actualizar_datos_empleado(
    empleado_id: int,
    datos: EmpleadoUpdate,
    # Agregar autenticación para que solo el empleado o admin pueda actualizar
):
    try:
        empleado_actualizado = Empleado.actualizar_datos_personales(
            id_empleado=empleado_id,
            telefono=datos.telefono,
            correo_electronico=datos.correo_electronico,
            calle=datos.calle,
            numero_calle=datos.numero_calle,
            localidad=datos.localidad,
            partido=datos.partido,  # Nueva variable agregada
            provincia=datos.provincia
        )
        return empleado_actualizado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



# Registro manual de asistencia (admin)
@app.post("/admin/registros/manual", tags=["Admin"])
def registrar_asistencia_manual(
    registro: AsistenciaManual,
    # Agrega dependencia de autenticación de admin:
    # current_user: dict = Depends(verificar_admin)
):
    try:
        nuevo_registro = RegistroHorario.registrar_asistencia_manual(
            id_empleado=registro.id_empleado,
            tipo=registro.tipo,
            fecha=registro.fecha,
            hora=registro.hora,
            estado_asistencia=registro.estado_asistencia
        )
        return nuevo_registro
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

# Obtener todos los empleados (para listados)
@app.get("/empleados/")
def listar_empleados():
    try:
        empleados = AdminCRUD.obtener_empleado()
        return [e for e in empleados]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Búsqueda avanzada de empleados
@app.get("/empleados/buscar/", response_model=Tuple[List[EmpleadoResponse], int])  # <- Cambiado a Tuple
def buscar_empleados(
    nombre: Optional[str] = None,
    apellido: Optional[str] = None,
    dni: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 10
):
    return AdminCRUD.buscar_avanzado(nombre, apellido, dni, pagina, por_pagina)

@app.get("/empleados/{empleado_id}/informacion-laboral")
def obtener_informacion_laboral(empleado_id: int):
    try:
        info = AdminCRUD.buscar_informacion_laboral_por_id_empleado(empleado_id)
        if info:
            return {
                "departamento": info[0],
                "puesto": info[1],
                "turno": info[2],
                "horario_entrada": str(info[3]),
                "horario_salida": str(info[4]),
                "fecha_ingreso": info[5].strftime('%Y-%m-%d'),
                "tipo_contrato": info[6]
            }
        raise HTTPException(status_code=404, detail="No encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- POST Endpoints ---
@app.post("/registros/")
def obtener_registros_post(request: EmpleadoPeriodoRequest):
    if request.año and request.mes:
        registros = RegistroHorario.obtener_registros_mensuales(request.empleado_id, request.año, request.mes)
    else:
        registros = RegistroHorario.obtener_todos_los_registros(request.empleado_id)
    return [r for r in registros]

@app.post("/registroscompleto/")
def obtener_registros_completo_post(request: EmpleadoIDRequest):
    registros = RegistroHorario.obtener_todos_los_registros(request.empleado_id)
    return [r for r in registros]

@app.post("/horas/")
def calcular_horas_post(request: HorasRequest):
    horas = RegistroHorario.calcular_horas_mensuales(request.empleado_id, request.año, request.mes)
    return {"horas_trabajadas": horas}

@app.post("/empleados/listar")
def listar_empleados_post():
    try:
        empleados = AdminCRUD.obtener_empleado()
        return [e for e in empleados]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/empleados/buscar/")
def buscar_empleados_post(request: BuscarEmpleadoRequest):
    return AdminCRUD.buscar_avanzado(request.nombre, request.apellido, request.dni, request.pagina, request.por_pagina)

@app.post("/empleados/informacion-laboral")
def obtener_info_laboral_post(request: EmpleadoIDIntRequest):
    try:
        info = AdminCRUD.buscar_informacion_laboral_por_id_empleado(request.empleado_id)
        if info:
            return {
                "departamento": info[0],
                "puesto": info[1],
                "turno": info[2],
                "horario_entrada": str(info[3]),
                "horario_salida": str(info[4]),
                "fecha_ingreso": info[5].strftime('%Y-%m-%d'),
                "tipo_contrato": info[6]
            }
        raise HTTPException(status_code=404, detail="No encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


#NOMINAS----------------------------------------------------------------------------------------

# Obtener última nómina de un empleado (GET)
@app.get("/nominas/empleado/{id_empleado}/ultima", response_model=NominaResponse)
async def obtener_ultima_nomina_empleado(id_empleado: int):
    try:
        nominas = NominaCRUD.obtener_nominas_empleado(id_empleado)
        if not nominas:
            raise HTTPException(status_code=404, detail="No se encontraron nóminas para este empleado")
        return nominas[0]  # La más reciente
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Obtener todas las nóminas de un empleado (GET)
@app.get("/nominas/empleado/{id_empleado}", response_model=NominaListResponse)
async def obtener_nominas_empleado(id_empleado: int):
    try:
        nominas = NominaCRUD.obtener_nominas_empleado(id_empleado)
        return {"nominas": nominas}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# POST para obtener las nóminas de un empleado
@app.post("/nominas/empleado", response_model=NominaListResponse)
async def obtener_nominas_empleado_post(data: EmpleadoIDIntRequest):
    try:
        nominas = NominaCRUD.obtener_nominas_empleado(data.empleado_id)
        return {"nominas": nominas}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/nominas/empleado/buscar", response_model=NominaListResponse)
async def buscar_nominas_empleado(
    request: EmpleadoNominaRequest,
    nomina_crud: NominaCRUD = Depends()
):
    try:
        nominas = nomina_crud.obtener_nominas_empleado(request.id_empleado)

        if request.periodo:
            nominas = [n for n in nominas if n.periodo == request.periodo]

        return {"nominas": nominas}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Opción 4: Obtener nómina específica por ID (GET)
@app.get("/nominas/{id_nomina}", response_model=NominaResponse)
async def obtener_nomina(id_nomina: int):
    try:
        nomina = NominaCRUD.obtener_nomina(id_nomina)
        if not nomina:
            raise HTTPException(status_code=404, detail="Nómina no encontrada")
        return nomina
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/calcular", response_model=NominaResponse)
async def calcular_nomina_endpoint(
        request: CalculoNominaRequest,
        nomina_crud: NominaCRUD = Depends()
):
    """
    Calcula la nómina para un empleado en un período específico.

    Parámetros desde el frontend:
    - id_empleado: ID del empleado
    - periodo: Período a calcular (ej. "MAYO 2024")
    - fecha_calculo (opcional): Fecha de cálculo (default: hoy)
    """
    try:
        return nomina_crud.calcular_nomina(
            id_empleado=request.id_empleado,
            periodo_texto=request.periodo,
            fecha_calculo=request.fecha_calculo
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/{empleado_id}/puesto")
def obtener_puesto_empleado(empleado_id: int):
    try:
        puesto = AdminCRUD.obtener_puesto_por_id_empleado(empleado_id)
        if puesto:
            return {"puesto": puesto}
        raise HTTPException(status_code=404, detail="Puesto no encontrado para el empleado especificado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/{empleado_id}/categoria")
def obtener_categoria_empleado(empleado_id: int):
    try:
        categoria = AdminCRUD.obtener_categoria_por_id_empleado(empleado_id)
        if categoria:
            return {"categoria": categoria}
        raise HTTPException(status_code=404, detail="Categoría no encontrada para el empleado especificado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/{empleado_id}/departamento")
def obtener_departamento_empleado(empleado_id: int):
    try:
        departamento_info = AdminCRUD.obtener_departamento_por_id_empleado(empleado_id)
        if departamento_info:
            return {
                "departamento": departamento_info[0],
                "descripcion": departamento_info[1] if departamento_info[1] else "Sin descripción"
            }
        raise HTTPException(status_code=404, detail="Departamento no encontrado para el empleado especificado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
