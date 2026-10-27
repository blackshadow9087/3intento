
from datetime import date
from functools import wraps
import os

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import IntegrityError

from conexion import consultar_uno, consultar_todos, ejecutar

app = Flask(__name__)
app.secret_key = os.getenv(
    "SECRET_KEY",
    "cambia-esta-clave-en-produccion"
)


# Verifica que el usuario haya iniciado sesión
def iniciar_sesion_requerido(funcion):
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión para ver esa página.", "error")
            return redirect(url_for("index"))
        return funcion(*args, **kwargs)
    return envoltura


# Busca una misión en MySQL
def obtener_mision(mision_id):
    return consultar_uno("""
        SELECT m.*,
               CONCAT(u.nombre, ' ', u.apellido) AS lider,
               u.id AS lider_id,
               (SELECT COUNT(*)
                FROM voluntarios v
                WHERE v.mision_id = m.id) AS total_voluntarios
        FROM misiones m
        JOIN usuarios u ON u.id = m.lider_id
        WHERE m.id = %s
    """, (mision_id,))


# Valida los datos de una misión
def validar_mision(formulario):
    nombre = formulario.get("nombre", "").strip()
    fecha_texto = formulario.get("fecha", "").strip()
    descripcion = formulario.get("descripcion", "").strip()
    cantidad_texto = formulario.get(
        "voluntarios_necesarios", ""
    ).strip()

    if not nombre or not fecha_texto or not descripcion or not cantidad_texto:
        return None, "Completa todos los campos."

    try:
        fecha_mision = date.fromisoformat(fecha_texto)
        cantidad = int(cantidad_texto)
    except ValueError:
        return None, "La fecha o la cantidad no son válidas."

    if fecha_mision < date.today():
        return None, "La fecha no puede estar en el pasado."

    if not 2 <= cantidad <= 20:
        return None, "La cantidad debe estar entre 2 y 20 voluntarios."

    if len(nombre) > 120:
        return None, "El nombre no puede superar los 120 caracteres."

    return (nombre, fecha_mision, cantidad, descripcion), None


# Inicio de sesión
@app.route("/", methods=["GET", "POST"])
def index():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")

        usuario = consultar_uno(
            "SELECT * FROM usuarios WHERE correo = %s",
            (correo,)
        )

        if (
            not usuario
            or not check_password_hash(
                usuario["password_hash"], password
            )
        ):
            flash("Correo o contraseña incorrectos.", "error")
            return render_template("index.html")

        session.clear()
        session["usuario_id"] = usuario["id"]
        session["usuario_nombre"] = usuario["nombre"]

        return redirect(url_for("dashboard"))

    return render_template("index.html")


# Registro de usuarios
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar_password", "")

        if not all([nombre, apellido, correo, password, confirmar]):
            flash("Completa todos los campos.", "error")

        elif "@" not in correo or "." not in correo.split("@")[-1]:
            flash("Ingresa un correo válido.", "error")

        elif password != confirmar:
            flash("Las contraseñas no coinciden.", "error")

        elif len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")

        else:
            try:
                ejecutar("""
                    INSERT INTO usuarios
                    (nombre, apellido, correo, password_hash)
                    VALUES (%s, %s, %s, %s)
                """, (
                    nombre,
                    apellido,
                    correo,
                    generate_password_hash(password)
                ))

                flash("Cuenta creada. Ahora puedes iniciar sesión.", "ok")
                return redirect(url_for("index"))

            except IntegrityError:
                flash("Ese correo ya está registrado.", "error")

    return render_template("registro.html")


# Panel principal: esta ruta faltaba en tu código
@app.route("/dashboard")
@iniciar_sesion_requerido
def dashboard():
    misiones = consultar_todos("""
        SELECT m.*,
               CONCAT(u.nombre, ' ', u.apellido) AS lider,
               u.id AS lider_id,
               (SELECT COUNT(*)
                FROM voluntarios v
                WHERE v.mision_id = m.id) AS total_voluntarios
        FROM misiones m
        JOIN usuarios u ON u.id = m.lider_id
        ORDER BY m.fecha ASC
    """)

    return render_template(
        "dashboard.html",
        misiones=misiones,
        usuario_nombre=session.get("usuario_nombre")
    )


# Crear una misión
@app.route("/nueva", methods=["GET", "POST"])
@iniciar_sesion_requerido
def nueva():
    if request.method == "POST":
        datos, error = validar_mision(request.form)

        if error:
            flash(error, "error")
        else:
            nombre, fecha_mision, cantidad, descripcion = datos

            ejecutar("""
                INSERT INTO misiones
                (nombre, fecha, voluntarios_necesarios,
                 descripcion, lider_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                nombre,
                fecha_mision,
                cantidad,
                descripcion,
                session["usuario_id"]
            ))

            flash("Misión creada correctamente.", "ok")
            return redirect(url_for("dashboard"))

    return render_template(
        "nueva.html",
        hoy=date.today().isoformat()
    )


# Ver los detalles de una misión
@app.route("/ver/<int:mision_id>")
@iniciar_sesion_requerido
def ver_mision(mision_id):
    mision = obtener_mision(mision_id)

    if not mision:
        flash("La misión no existe.", "error")
        return redirect(url_for("dashboard"))

    voluntarios = consultar_todos("""
        SELECT u.id,
               CONCAT(u.nombre, ' ', u.apellido) AS nombre_completo
        FROM voluntarios v
        JOIN usuarios u ON u.id = v.usuario_id
        WHERE v.mision_id = %s
        ORDER BY v.fecha_inscripcion ASC
    """, (mision_id,))

    ya_se_unio = any(
        v["id"] == session["usuario_id"]
        for v in voluntarios
    )

    return render_template(
        "ver_mision.html",
        mision=mision,
        voluntarios=voluntarios,
        ya_se_unio=ya_se_unio
    )


# Editar una misión
@app.route("/editar/<int:mision_id>", methods=["GET", "POST"])
@iniciar_sesion_requerido
def editar(mision_id):
    mision = obtener_mision(mision_id)

    if not mision:
        flash("La misión no existe.", "error")
        return redirect(url_for("dashboard"))

    if mision["lider_id"] != session["usuario_id"]:
        flash("Solo el líder puede editar esta misión.", "error")
        return redirect(url_for("ver_mision", mision_id=mision_id))

    hoy = date.today().isoformat()

    if request.method == "POST":
        datos, error = validar_mision(request.form)

        if error:
            flash(error, "error")
            return render_template(
                "editar.html",
                mision=mision,
                hoy=hoy
            )

        nombre, fecha_mision, cantidad, descripcion = datos

        ejecutar("""
            UPDATE misiones
            SET nombre = %s,
                fecha = %s,
                voluntarios_necesarios = %s,
                descripcion = %s
            WHERE id = %s AND lider_id = %s
        """, (
            nombre,
            fecha_mision,
            cantidad,
            descripcion,
            mision_id,
            session["usuario_id"]
        ))

        flash("Misión actualizada correctamente.", "ok")
        return redirect(url_for("ver_mision", mision_id=mision_id))

    return render_template(
        "editar.html",
        mision=mision,
        hoy=hoy
    )


# Eliminar una misión
@app.route("/eliminar/<int:mision_id>", methods=["POST"])
@iniciar_sesion_requerido
def eliminar(mision_id):
    mision = obtener_mision(mision_id)

    if not mision:
        flash("La misión no existe.", "error")

    elif mision["lider_id"] != session["usuario_id"]:
        flash("Solo el líder puede eliminar esta misión.", "error")

    else:
        ejecutar(
            "DELETE FROM misiones WHERE id = %s AND lider_id = %s",
            (mision_id, session["usuario_id"])
        )
        flash("Misión eliminada.", "ok")

    return redirect(url_for("dashboard"))


# Inscribirse como voluntario
@app.route("/voluntarme/<int:mision_id>", methods=["POST"])
@iniciar_sesion_requerido
def voluntarme(mision_id):
    mision = obtener_mision(mision_id)

    if not mision:
        flash("La misión no existe.", "error")
        return redirect(url_for("dashboard"))

    if mision["total_voluntarios"] >= mision["voluntarios_necesarios"]:
        flash("Esta misión ya completó sus cupos.", "error")
    else:
        try:
            ejecutar("""
                INSERT INTO voluntarios (mision_id, usuario_id)
                VALUES (%s, %s)
            """, (mision_id, session["usuario_id"]))

            flash("Te has inscrito como voluntario.", "ok")

        except IntegrityError:
            flash("Ya estás inscrito en esta misión.", "error")

    return redirect(url_for("ver_mision", mision_id=mision_id))


# Cancelar inscripción de voluntario
@app.route("/desvoluntarme/<int:mision_id>", methods=["POST"])
@iniciar_sesion_requerido
def desvoluntarme(mision_id):
    ejecutar("""
        DELETE FROM voluntarios
        WHERE mision_id = %s AND usuario_id = %s
    """, (mision_id, session["usuario_id"]))

    flash("Has cancelado tu participación.", "ok")
    return redirect(url_for("ver_mision", mision_id=mision_id))


# Cerrar sesión
@app.route("/cerrar-sesion", methods=["POST"])
def cerrar_sesion():
    session.clear()
    flash("Sesión cerrada correctamente.", "ok")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
