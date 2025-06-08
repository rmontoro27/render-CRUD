import bcrypt
import psycopg2

from.database import db
from datetime import datetime
from api.schemas import Permisos
from fastapi import Depends, HTTPException






class Usuario:

    @staticmethod
    def crear_usuario(id_empleado: int, id_rol: int, nombre_usuario: str,
                      contraseña: str, motivo: str = None):
        conn = None
        try:
            conn = db.get_connection()
            cur = conn.cursor()

            # Verificar si ya existe un usuario con ese nombre
            cur.execute("SELECT 1 FROM usuario WHERE nombre_usuario = %s", (nombre_usuario,))
            if cur.fetchone():
                raise ValueError("El nombre de usuario ya está en uso.")

            # Hashear la contraseña
            contraseña_hash = bcrypt.hashpw(contraseña.encode('utf-8'), bcrypt.gensalt())

            # Insertar el nuevo usuario
            cur.execute("""
                    INSERT INTO usuario (
                        id_empleado, id_rol, nombre_usuario, contraseña,
                        esta_activo, fecha_activacion, fecha_creacion, motivo
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id_usuario
                """, (
                id_empleado, id_rol, nombre_usuario, contraseña_hash.decode('utf-8'),
                True, datetime.utcnow(), datetime.utcnow(), motivo
            ))

            nuevo_id = cur.fetchone()[0]
            conn.commit()
            return nuevo_id

        finally:
            if conn:
                conn.close()

    def verificar_password(password_plano: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password_plano.encode('utf-8'), password_hash.encode('utf-8'))

    @staticmethod
    def obtener_permisos_por_id_rol(id_rol: int) -> Permisos:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                online_login, offline_login,
                ver_datos_personales, editar_datos_personales,
                ver_datos_laborales, agregar_datos_laborales, editar_datos_laborales,
                agregar_empleado, ver_registro_asistencia,
                ver_informacion_bancaria, editar_informacion_bancaria,
                ingresar_asistencia, ingresar_inasistencia,
                ver_historial_nominas, calcular_nomina_manualmente, calcular_nomina_automaticamente,
                agregar_concepto, agregar_departamento, agregar_puesto, agregar_categoria,
                agregar_salario_con_vigencia,
                ver_vista_previa_recibo_sueldo, descargar_recibo_sueldo,
                ver_reportes, cerrar_sesion
            FROM rol WHERE id_rol = %s
        """, (id_rol,))
        row = cur.fetchone()

        if not row:
            raise ValueError("Rol no encontrado")

        permisos = Permisos(**dict(zip(Permisos.__fields__.keys(), row)))
        return permisos

    @staticmethod
    def obtener_usuario_por_username(username: str) -> dict | None:
        conn = db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT 
                    id_usuario, id_empleado, id_rol, 
                    nombre_usuario, contraseña AS password_hash,
                    esta_activo, fecha_activacion, fecha_creacion, motivo
                FROM usuario 
                WHERE nombre_usuario = %s
            """, (username,))
            row = cur.fetchone()
            if not row:
                return None

            columns = [desc[0] for desc in cur.description]
            return dict(zip(columns, row))
        finally:
            cur.close()
            conn.close()

    def requiere_permiso(nombre_permiso: str):
        def validador(usuario: Usuario = Depends(Usuario.obtener_usuario_desde_token)):
            permisos: Permisos = Usuario.obtener_permisos_por_id_rol(usuario.id_rol)
            if not getattr(permisos, nombre_permiso, False):
                raise HTTPException(status_code=403, detail=f"Permiso requerido: {nombre_permiso}")
            return usuario

        return validador