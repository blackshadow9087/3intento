from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import IntegrityError

from conexion import consultar_uno, ejecutar

class Usuario:
    def __init__(self, nombre, apellido, correo, password=None, usuario_id=None):
        self.id = usuario_id
        self.nombre = nombre.strip()
        self.apellido = apellido.strip()
        self.correo = correo.strip().lower()
        self.password = password

    def guardar(self):
        """Registra un usuario en la base de datos."""

        if not self.nombre or not self.apellido or not self.correo or not self.password:
            raise ValueError("Todos los campos son obligatorios.")

        if len(self.password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")

        password_hash = generate_password_hash(self.password)

        try:
            ejecutar(
                """
                INSERT INTO usuarios (nombre, apellido, correo, password_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    self.nombre,
                    self.apellido,
                    self.correo,
                    password_hash
                )
            )

            return True

        except IntegrityError:
            raise ValueError("Ese correo ya está registrado.")

    @staticmethod
    def buscar_por_correo(correo):
        """Busca un usuario por su correo."""

        return consultar_uno(
            "SELECT * FROM usuarios WHERE correo = %s",
            (correo.strip().lower(),)
        )

    @staticmethod
    def autenticar(correo, password):
        """Comprueba el correo y la contraseña."""

        usuario = Usuario.buscar_por_correo(correo)

        if not usuario:
            return None

        if not check_password_hash(usuario["password_hash"], password):
            return None

        return usuario

    @staticmethod
    def buscar_por_id(usuario_id):
        """Busca un usuario por su ID."""

        return consultar_uno(
            """
            SELECT id, nombre, apellido, correo
            FROM usuarios
            WHERE id = %s
            """,
            (usuario_id,)
        )      
        
        
    if __name__ == "__main__":
        app.run(debug=True) 
        
  
        

        
        

        