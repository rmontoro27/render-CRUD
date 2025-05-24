import psycopg2
from datetime import datetime, timedelta, date
from typing import Optional, List
from api.schemas import NominaBase, NominaResponse
from .database import db

class NominaCRUD:
    def __init__(self):

        self.db = db


    def calcular_nomina(self, id_empleado: int, periodo_texto: str, fecha_calculo: date):
        """
        Calcula la nómina completa para un empleado en un período específico
        """
        with self.db.get_connection() as conn:

            try:
                conn = self.db.get_connection()
                cur = conn.cursor()

                # Establecer periodo y fecha de pago
                fecha_calculo_dt = datetime.strptime(fecha_calculo, '%Y-%m-%d').date()
                fecha_de_pago = fecha_calculo_dt + timedelta(days=7)

                # Obtener id_periodo
                cur.execute(
                    "SELECT id_periodo FROM periodo_empleado WHERE id_empleado=%s AND periodo_texto=%s",
                    (id_empleado, periodo_texto)
                )
                cur.execute(
                    "INSERT INTO nominas (fecha) VALUES (%s)",
                    (fecha_calculo,)  # Psycopg2 maneja la conversión
                )
                periodo_result = cur.fetchone()
                if not periodo_result:
                    raise ValueError("Período no encontrado para el empleado")
                id_periodo = periodo_result[0]

                # Obtener salario base
                cur.execute("""
                    SELECT s.valor_por_defecto 
                    FROM salario_base s 
                    INNER JOIN informacion_laboral i ON 
                        i.id_puesto = s.id_puesto AND 
                        i.id_categoria = s.id_categoria AND 
                        i.id_departamento = s.id_departamento
                    WHERE i.id_empleado=%s AND %s BETWEEN s.fecha_inicio AND COALESCE(s.fecha_fin, CURRENT_DATE)
                    ORDER BY s.fecha_inicio DESC
                    LIMIT 1
                """, (id_empleado, fecha_calculo_dt))
                salario_base_result = cur.fetchone()
                if not salario_base_result:
                    raise ValueError("Salario base no encontrado")
                salario_base = float(salario_base_result[0])

                #Obtener conceptos de liquidación
                conceptos = {}
                cur.execute("""
                    SELECT cl.descripcion, cl.tipo_concepto, cl.valor_por_defecto, cl.es_porcentaje 
                    FROM empleado_concepto ec 
                    INNER JOIN concepto_liquidacion cl ON cl.codigo = ec.codigo_concepto
                    WHERE ec.id_empleado=%s
                """, (id_empleado,))

                for descripcion, tipo, valor, es_porcentaje in cur.fetchall():
                    conceptos[descripcion] = {
                        'tipo': tipo,
                        'valor': float(valor),
                        'es_porcentaje': es_porcentaje
                    }

                #Verificar presentismo
                cur.execute(
                    "SELECT presentismo FROM periodo_empleado WHERE id_periodo=%s",
                    (id_periodo,)
                )
                presentismo_result = cur.fetchone()
                tiene_presentismo = presentismo_result[0] if presentismo_result else False

                # Calcular bono antigüedad
                cur.execute(
                    "SELECT fecha_ingreso FROM informacion_laboral WHERE id_empleado=%s",
                    (id_empleado,)
                )
                fecha_ingreso = cur.fetchone()[0]
                antiguedad_anos = (fecha_calculo_dt - fecha_ingreso).days // 365

                cur.execute(
                    "SELECT porcentaje FROM bono_antiguedad WHERE años=%s",
                    (antiguedad_anos,)
                )
                bono_antiguedad_result = cur.fetchone()
                bono_antiguedad_porcentaje = float(bono_antiguedad_result[0]) if bono_antiguedad_result else 0.0

                # Calcular horas extras
                # Obtener total horas normales trabajadas
                cur.execute(
                    "SELECT SUM(horas_normales_trabajadas) FROM registro_jornada WHERE id_periodo=%s",
                    (id_periodo,)
                )
                total_horas_result = cur.fetchone()
                total_horas = float(total_horas_result[0]) if total_horas_result and total_horas_result[0] else 0.0

                if total_horas <= 0:
                    raise ValueError("No se registraron horas trabajadas para el período")

                valor_hora = salario_base / total_horas
                valor_hora = round(valor_hora, 2)

                # Actualizar valor_hora en periodo_empleado
                cur.execute(
                    "UPDATE periodo_empleado SET valor_hora=%s WHERE id_periodo=%s",
                    (valor_hora, id_periodo)
                )

                # Calcular monto horas extras
                cur.execute("""
                    SELECT rhe.cantidad_horas, rhe.tipo_hora_extra 
                    FROM registro_hora_extra rhe 
                    JOIN registro_jornada rj ON rj.id_registro_jornada = rhe.id_registro_jornada
                    WHERE rj.id_periodo=%s
                """, (id_periodo,))

                horas_extra = 0.0
                for cantidad, tipo in cur.fetchall():
                    cantidad = float(cantidad)
                    if tipo == '50%':
                        horas_extra += cantidad * valor_hora * 1.5
                    elif tipo == '100%':
                        horas_extra += cantidad * valor_hora * 2

                horas_extra = round(horas_extra, 2)

                #  Calcular montos finales
                #  Aplicar bonos (asignaciones)
                bono_presentismo = 0.0
                if tiene_presentismo and 'Presentismo' in conceptos:
                    presentismo = conceptos['Presentismo']
                    if presentismo['es_porcentaje']:
                        bono_presentismo = salario_base * (presentismo['valor'] / 100)
                    else:
                        bono_presentismo = presentismo['valor']
                    bono_presentismo = round(bono_presentismo, 2)

                bono_antiguedad = salario_base * (bono_antiguedad_porcentaje / 100)
                bono_antiguedad = round(bono_antiguedad, 2)

                sueldo_bruto = salario_base + bono_presentismo + bono_antiguedad + horas_extra

                # Aplicar descuentos
                descuentos = {
                    'Jubilación': 0.0,
                    'Obra Social': 0.0,
                    'ANSSAL': 0.0,
                    'Ley 19032': 0.0,
                    'Impuesto a las Ganancias': 0.0,
                    'Aporte Sindical': 0.0
                }

                for nombre, datos in conceptos.items():
                    if datos['tipo'] == 'Descuento':
                        if datos['es_porcentaje']:
                            descuentos[nombre] = sueldo_bruto * (datos['valor'] / 100)
                        else:
                            descuentos[nombre] = datos['valor']
                        descuentos[nombre] = round(descuentos[nombre], 2)

                total_descuentos = sum(descuentos.values())
                sueldo_neto = sueldo_bruto - total_descuentos
                sueldo_neto = round(sueldo_neto, 2)

                # 8. Insertar nómina
                nomina_data = {
                    'id_empleado': id_empleado,
                    'id_periodo': id_periodo,
                    'fecha_de_pago': fecha_de_pago,
                    'salario_base': salario_base,
                    'bono_presentismo': bono_presentismo if bono_presentismo else None,
                    'bono_antiguedad': bono_antiguedad if bono_antiguedad else None,
                    'horas_extra': horas_extra if horas_extra else None,
                    'descuento_jubilacion': descuentos.get('Jubilación'),
                    'descuento_obra_social': descuentos.get('Obra Social'),
                    'descuento_anssal': descuentos.get('ANSSAL'),
                    'descuento_ley_19032': descuentos.get('Ley 19032'),
                    'impuesto_ganancias': descuentos.get('Impuesto a las Ganancias'),
                    'descuento_sindical': descuentos.get('Aporte Sindical'),
                    'sueldo_bruto': sueldo_bruto,
                    'sueldo_neto': sueldo_neto,
                    'estado': 'Pendiente'
                }

                columns = ', '.join(nomina_data.keys())
                placeholders = ', '.join(['%s'] * len(nomina_data))

                cur.execute(
                    f"INSERT INTO nomina ({columns}) VALUES ({placeholders}) RETURNING id_nomina",
                    list(nomina_data.values())
                )

                id_nomina = cur.fetchone()[0]
                conn.commit()

                # Obtener nómina completa para respuesta
                cur.execute("""
                    SELECT * FROM recibo_sueldo WHERE id_nomina=%s
                """, (id_nomina,))

                columns = [desc[0] for desc in cur.description]
                nomina_completa = dict(zip(columns, cur.fetchone()))

                return nomina_completa

            except psycopg2.Error as e:
                if conn:
                    conn.rollback()
                raise ValueError(f"Error de base de datos: {str(e)}")
            except Exception as e:
                if conn:
                    conn.rollback()
                raise ValueError(f"Error al calcular nómina: {str(e)}")
            finally:
                if conn:
                    self.db.return_connection(conn)


    def obtener_nomina(self, id_nomina: int) -> Optional[NominaResponse]:
        """Devuelve una nómina como Pydantic model"""
        conn = None
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()

            cur.execute("SELECT * FROM recibo_sueldo WHERE id_nomina=%s", (id_nomina,))
            result = cur.fetchone()

            if not result:
                return None

            columns = [desc[0] for desc in cur.description]
            nomina_dict = dict(zip(columns, result))
            return NominaResponse(**nomina_dict)

        finally:
            if conn:
                self.db.return_connection(conn)

    def obtener_nominas_empleado(self, id_empleado: int) -> List[NominaResponse]:
        """Devuelve todas las nóminas del empleado como Pydantic models"""
        conn = None
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM recibo_sueldo 
                WHERE id_empleado=%s
                ORDER BY fecha_de_pago DESC
            """, (id_empleado,))

            columns = [desc[0] for desc in cur.description]
            return [NominaResponse(**dict(zip(columns, row))) for row in cur.fetchall()]


        finally:

            if conn:
                self.return_connection(conn)


