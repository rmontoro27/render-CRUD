import bcrypt
from.database import db
from datetime import datetime





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