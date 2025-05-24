from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class EmpleadoResponse(BaseModel):
    """Modelo SOLO para respuestas (GET)"""
    id_empleado: int
    nombre: str
    apellido: str
    tipo_identificacion: str
    numero_identificacion: str
    fecha_nacimiento: date  # Ajusta el tipo según tu BD
    correo_electronico: Optional[str] = None
    telefono: Optional[str] = None
    calle: Optional[str] = None
    numero_calle: Optional[str] = None
    localidad: Optional[str] = None
    partido: Optional[str] = None
    provincia: Optional[str] = None
    genero: Optional[str] = None
    nacionalidad: Optional[str] = None
    estado_civil: Optional[str] = None

class EmpleadoBase(BaseModel):
        nombre: str
        apellido: str
        tipo_identificacion: str
        numero_identificacion: str
        fecha_nacimiento: str
        correo_electronico: str
        telefono: str
        calle: str
        numero_calle: str
        localidad: str
        partido: str
        provincia: str
        genero: str
        pais_nacimiento: str
        estado_civil: str

class EmpleadoUpdate(BaseModel):
        telefono: Optional[str] = None
        correo_electronico: Optional[str] = None
        calle: Optional[str] = None
        numero_calle: Optional[str] = None
        localidad: Optional[str] = None
        partido: Optional[str] = None  # Nueva variable agregada
        provincia: Optional[str] = None

class NominaBase(BaseModel):
    id_nomina: int
    id_empleado: int
    periodo: str
    fecha_de_pago: date

class NominaResponse(NominaBase):
    salario_base: float
    bono_presentismo: Optional[float] = None
    bono_antiguedad: Optional[float] = None
    horas_extra: Optional[float] = None
    descuento_jubilacion: Optional[float] = None
    descuento_obra_social: Optional[float] = None
    descuento_anssal: Optional[float] = None
    descuento_ley_19032: Optional[float] = None
    impuesto_ganancias: Optional[float] = None
    descuento_sindical: Optional[float] = None
    sueldo_bruto: float
    sueldo_neto: float


class NominaListResponse(BaseModel):
    nominas: list[NominaResponse]

class CalculoNominaRequest(BaseModel):
    id_empleado: int
    periodo: str
    fecha_calculo: date

class EmpleadoNominaRequest(BaseModel):
    id_empleado: int
    periodo: Optional[str] = None