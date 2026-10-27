import mysql.connector
from mysql.connector import Error


def obtener_conexion():
    """Crea una conexión con la base de datos MySQL."""
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",  # Escribe aquí tu contraseña de MySQL
            database="sistema_misiones"
        )

        return conexion

    except Error as error:
        print(f"Error al conectar con MySQL: {error}")
        return None


def consultar_uno(sql, parametros=None):
    """Obtiene un solo registro de la base de datos."""
    conexion = obtener_conexion()

    if conexion is None:
        return None

    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(sql, parametros or ())
        resultado = cursor.fetchone()
        return resultado

    except Error as error:
        print(f"Error en la consulta: {error}")
        return None

    finally:
        cursor.close()
        conexion.close()


def consultar_todos(sql, parametros=None):
    """Obtiene todos los registros de la consulta."""
    conexion = obtener_conexion()

    if conexion is None:
        return []

    cursor = None

    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(sql, parametros or ())
        return cursor.fetchall()

    except Error as error:
        print(f"Error en la consulta: {error}")
        return []

    finally:
        if cursor:
            cursor.close()
        conexion.close()


def ejecutar(sql, parametros=None):
    """Ejecuta INSERT, UPDATE o DELETE."""
    conexion = obtener_conexion()

    if conexion is None:
        raise ConnectionError("No se pudo conectar con MySQL.")

    cursor = None

    try:
        cursor = conexion.cursor()
        cursor.execute(sql, parametros or ())
        conexion.commit()
        return cursor.lastrowid

    except Error as error:
        conexion.rollback()
        print(f"Error al ejecutar la operación: {error}")
        raise

    finally:
        if cursor:
            cursor.close()
        conexion.close()