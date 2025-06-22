import os

from pydantic import field_validator
#import cv2
#import face_recognition
import numpy as np

from fastapi import FastAPI, HTTPException, Depends

from auth.jwt import crear_token
from crud import crudEmpleado, crudAdmintrador
import uuid
from typing import Optional
from datetime import datetime, timedelta, date, time

from crud.crudAdmintrador import AdminCRUD
from crud.crudEmpleado import RegistroHorario
from crud.crudEmpleado import Empleado
from crud.crudNomina import NominaCRUD
from crud.crudUsuario import Usuario
from pydantic import BaseModel, Field
from typing import List
from typing import Tuple, List
from .schemas import (EmpleadoResponse, EmpleadoBase, EmpleadoUpdate, NominaResponse,
                      NominaBase, NominaListResponse, EmpleadoNominaRequest, EmpleadoConsulta,
                      EmpleadoIDRequest, EmpleadoPeriodoRequest, EmpleadoIDIntRequest,
                      BuscarEmpleadoRequest, HorasRequest, CalculoNominaRequest, LoginResponse, LoginResponse,
                      LoginRequest, RegistroUpdate, CrearUsuarioRequest, CuentaBancariaInput, CuentaBancariaModificar,
                      SalarioInput, ConceptoInput, ConceptoOutput, ConceptoUpdate, JornadaRequest,
                      JornadaParcialRequest, IncidenciaAsistenciaRequest, AsistenciaBiometricaRequest)
from fastapi import APIRouter, HTTPException
from crud.database import db
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, status
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
import traceback



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


@app.post("/crear-empleado/")
def crear_empleado(request: EmpleadoBase):
    try:
        id_empleado = AdminCRUD.crear_empleado(request)

        return {
            "mensaje": "Empleado creado correctamente",
            "id_empleado": id_empleado
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        import traceback
        print("[ERROR] Error inesperado:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/empleados/{numero_identificacion}")
def obtener_empleado(numero_identificacion: str):
    empleado = AdminCRUD.obtener_detalle_empleado(numero_identificacion)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado

# No puedo probarlo porque no hay hs laborales
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
def obtener_todos_los_registros(empleado_id: str):

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
        empleado_actualizado = AdminCRUD.actualizar_datos_personales2(
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

# --- POST Endpoints -----------------------------------------
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

#VERSIONES PUT CRUD DE EMPLEADOS------------------------------------------------------------------


@app.put("/registros/{registro_id}")
async def actualizar_registro_horario(
    registro_id: int,
    registro: RegistroUpdate,
    # current_user: dict = Depends(verificar_admin)
):
    """
    Actualiza un registro horario existente.
    """
    try:
        registro_actualizado = RegistroHorario.actualizar_registro(
            registro_id=registro_id,
            nuevos_datos=registro
        )
        if not registro_actualizado:
            raise HTTPException(
                status_code=404,
                detail="Registro no encontrado"
            )
        return registro_actualizado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/empleados/{empleado_id}/datos-personales", response_model=EmpleadoBase)
async def actualizar_datos_personales(
        empleado_id: int,
        datos: EmpleadoUpdate
):
    """
    Endpoint PATCH que utiliza tu función actualizar_datos_personales2
    """
    try:
        # Extraer solo los campos que no son None
        campos_actualizar = {k: v for k, v in datos.dict().items() if v is not None}

        if not campos_actualizar:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar"
            )

        # Llamada a tu función CRUD existente
        empleado_actualizado = AdminCRUD.actualizar_datos_personales2(
            id_empleado=empleado_id,
            **campos_actualizar
        )

        if not empleado_actualizado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado"
            )

        return empleado_actualizado

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

#FOTO-------------------------------------------------------------------------------------------


cloudinary.config(
    cloud_name="dgl2tcayr",
    api_key="519574358682122",
    api_secret="47PafwZ4aSgVEg8eGWsyacM7QP0"
)

@app.post("/cargar-image/")
async def cargar_imagen(image: UploadFile = File(...), usuario_id: int = Form(...)):
    try:
        contents = await image.read()

        # Debug opcional
        print(f"Archivo recibido: {image.filename}, tamaño: {len(contents)} bytes")

        image_url = AdminCRUD.actualizar_imagen_perfil(contents, usuario_id)
        return {"url": image_url}

    except Exception as e:
        print(f"Error al cargar imagen: {e}")
        return {"error": str(e)}

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


# Obtener nómina específica por ID (GET)
@app.get("/nominas/{id_nomina}", response_model=NominaResponse)
async def obtener_nomina(id_nomina: int):
    try:
        nomina = NominaCRUD.obtener_nomina(id_nomina)
        if not nomina:
            raise HTTPException(status_code=404, detail="Nómina no encontrada")
        return nomina
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Calcular Nomina
@app.post("/calcular_nomina", response_model=NominaResponse)
async def calcular_nomina_endpoint(request: CalculoNominaRequest):
    try:
        return NominaCRUD.calcular_nomina(
            id_empleado=request.id_empleado,
            periodo_texto=request.periodo,
            fecha_calculo=request.fecha_calculo,
            tipo=request.tipo
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


@app.get("/descargar-recibo/{id_nomina}")
def descargar_recibo(id_nomina: int):
    nomina = NominaCRUD.obtener_nomina(id_nomina)
    if not nomina:
        raise HTTPException(status_code=404, detail="Nómina no encontrada")

    path_pdf = f"./pdfs/recibo_{id_nomina}.pdf"
    if not os.path.exists(path_pdf):
        # Llamada explícita sin usar dict()
        path_pdf = NominaCRUD.generar_recibo_pdf(
            id_nomina=id_nomina,
            nombre_empleado=nomina.nombre,
            periodo=nomina.periodo,
            fecha_de_pago=str(nomina.fecha_de_pago),
            salario_base=nomina.salario_base,
            bono_presentismo=nomina.bono_presentismo,
            horas_extra=nomina.horas_extra,
            descuento_jubilacion=nomina.descuento_jubilacion,
            descuento_obra_social=nomina.descuento_obra_social,
            sueldo_neto=nomina.sueldo_neto
        )

    return FileResponse(
        path_pdf,
        media_type='application/pdf',
        filename=f"recibo_{id_nomina}.pdf"
    )

#user--------------------------------------------------------------

@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    #  Buscar usuario
    usuario = Usuario.obtener_usuario_por_username(request.username)

    if not usuario or not Usuario.verificar_password(request.password, usuario.contrasena):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Verificar si el usuario está activo
    if not usuario.esta_activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    # Obtener el id_rol desde empleado
    id_rol = AdminCRUD.obtener_id_rol_por_id_empleado(usuario.id_empleado)
    if id_rol is None:
        raise HTTPException(status_code=404, detail="Rol no asignado al empleado")

    #  Obtener permisos desde tabla rol
    permisos = Usuario.obtener_permisos_por_id_rol(id_rol)
    numero_identificacion = AdminCRUD.obtener_numero_identificacion(usuario.id_empleado)

    # Crear token
    token_data = {
        "sub": usuario.nombre_usuario,
        "id_empleado": usuario.id_empleado,
        "id_rol": id_rol,
        "permisos": permisos.model_dump()
    }

    token = crear_token(token_data)

    # Devolver token y permisos
    return {
        "access_token": token,
        "permisos": permisos,
        "rol": str(usuario.id_rol),
        "id_empleado": usuario.id_empleado,
        "numero_identificacion": numero_identificacion

    }


@app.post("/crear-usuario/")
def crear_usuario(request: CrearUsuarioRequest):
    try:
        id_usuario = Usuario.crear_usuario(
            id_empleado=request.id_empleado,
            id_rol=request.id_rol,
            nombre_usuario=request.nombre_usuario,
            contrasena=request.contrasena,
            motivo=request.motivo
        )
        return {"mensaje": "Usuario creado correctamente", "id_usuario": id_usuario}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

#CUENTA BANCARIA---------------------------------------------------------------------------------

# Obtener datos
@app.get("/empleado/{id_empleado}/cuenta-bancaria")
def get_cuenta_bancaria(id_empleado: int):
    cuenta = AdminCRUD.obtener_cuenta_bancaria(id_empleado)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    return cuenta

# Crear cuenta
@app.post("/empleado/{id_empleado}/cuenta-bancaria")
def post_cuenta_bancaria(id_empleado: int, datos: CuentaBancariaInput):
    id_cuenta = AdminCRUD.crear_cuenta_bancaria(
        id_empleado=id_empleado,
        codigo_banco=datos.codigo_banco,
        numero_cuenta=datos.numero_cuenta,
        tipo_cuenta=datos.tipo_cuenta
    )
    return {"mensaje": "Cuenta bancaria creada", "id_cuenta": id_cuenta}

#Actualiza cuenta
@app.put("/empleado/{id_empleado}/cuenta-bancaria")
def put_cuenta_bancaria(id_empleado: int, datos: CuentaBancariaModificar):
    try:
        filas_afectadas = AdminCRUD.actualizar_cuenta_bancaria(
            id_empleado=id_empleado,
            nombre_banco=datos.nombre_banco,
            numero_cuenta=datos.numero_cuenta,
            tipo_cuenta=datos.tipo_cuenta
        )
        if filas_afectadas == 0:
            raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada para actualizar")
        return {"mensaje": "Cuenta bancaria actualizada"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("[ERROR INTERNO]", traceback.format_exc())  # Log completo
        raise HTTPException(status_code=500, detail="Error interno del servidor")


#SALARIO
@app.get("/api/salarios/historial")
def historial_salarios(puesto_id: int, departamento_id: int, categoria_id: int):
    historial = AdminCRUD.obtener_historial_salarios(puesto_id, departamento_id, categoria_id)
    if not historial:
        raise HTTPException(status_code=404, detail="No se encontró historial para esta combinación")
    return historial

@app.put("/api/salarios/actualizarSalario")
def actualizar_salario(datos: SalarioInput):
    try:
        AdminCRUD.actualizar_salario(
            datos.puesto_id,
            datos.departamento_id,
            datos.categoria_id,
            datos.valor_por_defecto,
            datos.fecha_inicio
        )
        return {"mensaje": "Salario actualizado correctamente"}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")
     


@app.post("/api/conceptos/agregar")
def agregar_concepto(datos: ConceptoInput):
    try:
        AdminCRUD.agregar_concepto(
            datos.descripcion,
            datos.tipo_concepto,
            datos.valor_por_defecto,
            datos.es_porcentaje
        )
        return {"mensaje": "✅ Concepto agregado correctamente"}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.get("/api/conceptos/", response_model=list[ConceptoOutput])
def listar_conceptos():
    try:
        return AdminCRUD.listar_conceptos()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al listar conceptos")

@app.delete("/api/conceptos/{codigo}")
def eliminar_concepto(codigo: str):
    try:
        AdminCRUD.eliminar_concepto(codigo)
        return {"mensaje": f"🗑 Concepto {codigo} eliminado correctamente"}

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al eliminar concepto")

@app.put("/api/conceptos/{codigo}")
def modificar_concepto(codigo: str, datos: ConceptoUpdate):
    try:
        AdminCRUD.modificar_concepto(codigo, datos)
        return {"mensaje": f"✏️ Concepto {codigo} modificado correctamente"}

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al modificar concepto")

@app.post("/api/documentos/subir-titulo")
async def subir_documento(
    archivo: UploadFile = File(...),
    tipo: str = Form(...),
    empleado_id: int = Form(...),
    descripcion: str = Form(None)):
    try:
        contenido = await archivo.read()

        print(f"Archivo recibido: {archivo.filename}, tamaño: {len(contenido)} bytes")

        url_titulo = AdminCRUD.guardar_documento_tipo(
            empleado_id,
            contenido,
            tipo,
            descripcion
        )
        return {"mensaje": f"{tipo} subido correctamente", "url": url_titulo}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"❌ Error al subir título: {e}")
        raise HTTPException(status_code=500, detail="Error al subir el título")


@app.get("/api/documentos/cv/{empleado_id}")
def obtener_documento(empleado_id: int, tipo: str):
    try:
        return AdminCRUD.obtener_documento_tipo(empleado_id, tipo)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el {tipo}")


@app.get("/api/biometrico/tiene-vector/{empleado_id}")
def verificar_vectores(empleado_id: int):
    try:
        tiene = AdminCRUD.tiene_vectores_faciales(empleado_id)
        return {"empleado_id": empleado_id, "tiene_vectores_completos": tiene}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al verificar vectores biométricos")


#Jornada------------------------------------------------------------------------------

@app.post("/registrar-jornada")
def registrar_jornada(request: JornadaRequest):
    try:
        AdminCRUD.registrar_jornada(
            id_empleado=request.id_empleado,
            fecha=request.fecha,
            dia=request.dia,
            hora_entrada=request.hora_entrada,
            hora_salida=request.hora_salida,
            estado_jornada=request.estado_jornada,
            horas_normales_trabajadas=request.horas_normales_trabajadas,
            horas_extra=request.horas_extra,
            motivo=request.motivo
        )
        return {"mensaje": "Jornada registrada correctamente"}
    
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/registrar-jornada-parcial")
def registrar_jornada_parcial(request: JornadaParcialRequest):
    try:
        AdminCRUD.registrar_jornada_parcial(
            id_empleado=request.id_empleado,
            fecha=request.fecha,
            hora_entrada=request.hora_entrada,
            hora_salida=request.hora_salida,
            motivo=request.motivo
        )
        return {"mensaje": "Registro parcial de jornada realizado correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/registrar-incidencia/")
def registrar_incidencia_asistencia_endpoint(datos: IncidenciaAsistenciaRequest):
    try:
        AdminCRUD.registrar_incidencia_asistencia(
            id_empleado=datos.id_empleado,
            fecha=datos.fecha,
            dia=datos.dia,
            tipo=datos.tipo,
            descripcion=datos.descripcion
        )
        return {"mensaje": "Incidencia registrada correctamente"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
@app.post("/registrar-asistenciaBiometrica/")
def registrar_asistencia_biometrica(datos: AsistenciaBiometricaRequest):
    try: 
        AdminCRUD.registrar_asistencia_biometrica(
            id_empleado=datos.id_empleado,
            fecha=datos.fecha,
            tipo=datos.tipo,
            hora=datos.hora,
            estado_asistencia=datos.estado_asistencia,
            turno_asistencia=datos.turno_asistencia
        )
        return {"mensaje": "Asistencia biometrica registrada correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except Exception as e:
        print("❌ Error en endpoint:", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")