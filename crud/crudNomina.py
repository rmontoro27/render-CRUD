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
                cur.execute("""
                    SELECT id_periodo, presentismo 
                    FROM periodo_empleado 
                    WHERE id_empleado = %s AND periodo_texto = %s
                """, (id_empleado, periodo_texto))
                periodo_result = cur.fetchone()

                if not periodo_result:
                    raise ValueError("Período no encontrado para el empleado")

                id_periodo, tiene_presentismo = periodo_result

                # ELIMINAMOS EL INSERT PREMATURO QUE ESTABA AQUÍ

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

                # 1. Obtener total de horas normales trabajadas en el período
                cur.execute("""
                    SELECT SUM(rj.horas_normales_trabajadas)
                    FROM registro_jornada rj
                    WHERE rj.id_periodo = %s
                """, (id_periodo,))
                horas_normales_result = cur.fetchone()
                horas_normales_trabajadas = horas_normales_result[0] or 0

                if horas_normales_trabajadas == 0:
                    raise ValueError("No se registraron horas normales trabajadas en el período")

                #  Calcular valor hora (redondeado a 2 decimales)
                valor_hora = round(salario_base / horas_normales_trabajadas, 2)

                # Actualizar tabla periodo_empleado con el valor_hora
                cur.execute("""
                    UPDATE periodo_empleado
                    SET valor_hora = %s
                    WHERE id_periodo = %s
                """, (valor_hora, id_periodo))

                #  Calcular monto de horas extras
                cur.execute("""
                    SELECT rhe.cantidad_horas, rhe.tipo_hora_extra
                    FROM registro_hora_extra rhe
                    JOIN registro_jornada rj ON rj.id_registro_jornada = rhe.id_registro_jornada
                    WHERE rj.id_periodo = %s
                """, (id_periodo,))

                horas_extra_rows = cur.fetchall()
                monto_horas_extra = 0.0

                for cantidad_horas, tipo in horas_extra_rows:
                    if tipo == "50%":
                        monto_horas_extra += cantidad_horas * valor_hora * 1.5
                    elif tipo == "100%":
                        monto_horas_extra += cantidad_horas * valor_hora * 2

                monto_horas_extra = round(monto_horas_extra, 2)  # Redondear a 2 decimales
                bono_presentismo_val = None
                bono_antiguedad_val = None
                horas_extra_val = None

                descuentos_def = {
                    'Jubilación': 0.0,
                    'Obra Social': 0.0,
                    'ANSSAL': 0.0,
                    'Ley 19032': 0.0,
                    'Impuesto a las Ganancias': 0.0,
                    'Aporte Sindical': 0.0
                }

                descuentos = {
                    'Jubilación': 0.11 * salario_base,
                    'Obra Social': 0.03 * salario_base,
                    'ANSSAL': 0.01 * salario_base,
                    'Ley 19032': 0.02 * salario_base,
                    'Impuesto a las Ganancias': 0.5 * salario_base,
                    'Aporte Sindical': 0.02 * salario_base
                }

                bono_presentismo = 0.833 * salario_base if tiene_presentismo else 0.0
                bono_antiguedad = 0.0
                horas_extra = 0.0

                bono_presentismo_val = bono_presentismo
                bono_antiguedad_val = bono_antiguedad
                horas_extra_val = horas_extra

                descuentos_final = {**descuentos_def, **descuentos}

                sueldo_bruto = salario_base + bono_presentismo + bono_antiguedad + horas_extra
                total_descuentos = sum(descuentos_final.values())
                sueldo_neto = sueldo_bruto - total_descuentos

                # Combinar con los descuentos calculados
                descuentos_final = {**descuentos_def, **descuentos}

                # Construcción del diccionario final
                nomina_data = {
                    'id_empleado': id_empleado,
                    'id_periodo': id_periodo,
                    'fecha_de_pago': fecha_de_pago,
                    'salario_base': salario_base,
                    'bono_presentismo': bono_presentismo_val,
                    'bono_antiguedad': bono_antiguedad_val,
                    'horas_extra': monto_horas_extra,
                    'descuento_jubilacion': descuentos_final['Jubilación'],
                    'descuento_obra_social': descuentos_final['Obra Social'],
                    'descuento_anssal': descuentos_final['ANSSAL'],
                    'descuento_ley_19032': descuentos_final['Ley 19032'],
                    'impuesto_ganancias': descuentos_final['Impuesto a las Ganancias'],
                    'descuento_sindical': descuentos_final['Aporte Sindical'],
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

                # Obtener nómina directamente desde la tabla base
                cur.execute("""SELECT * FROM nomina WHERE id_nomina=%s""", (id_nomina,))
                row = cur.fetchone()

                if not row:
                    raise ValueError(f"No se encontró la nómina recién insertada con ID {id_nomina}")

                columns = [desc[0] for desc in cur.description]
                nomina_completa = dict(zip(columns, row))

                cur.execute("""
                    SELECT p.periodo_texto
                    FROM periodo_empleado p
                    WHERE p.id_periodo = %s
                """, (id_periodo,))
                periodo_row = cur.fetchone()
                if periodo_row:
                    nomina_completa['periodo'] = periodo_row[0]

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
                self.db.return_connection(conn)


