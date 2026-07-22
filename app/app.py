"""
Plataforma SaaS de Gestión de Inventarios para Pequeñas Empresas
Módulo principal: Gestión de Inventario (CRUD de productos)

Proyecto final de materia - Implementación básica del módulo principal
Stack: Flask + SQLite
"""
from flask import Flask, jsonify, request, g, send_from_directory
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "inventario.db")

app = Flask(__name__, static_folder="static")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 5
        )
        """
    )
    db.commit()
    db.close()


# ---------- Rutas de la API REST ----------

@app.route("/api/productos", methods=["GET"])
def listar_productos():
    db = get_db()
    productos = db.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    return jsonify([dict(p) for p in productos])


@app.route("/api/productos/<int:producto_id>", methods=["GET"])
def obtener_producto(producto_id):
    db = get_db()
    producto = db.execute(
        "SELECT * FROM productos WHERE id = ?", (producto_id,)
    ).fetchone()
    if producto is None:
        return jsonify({"error": "Producto no encontrado"}), 404
    return jsonify(dict(producto))


@app.route("/api/productos", methods=["POST"])
def crear_producto():
    data = request.get_json(force=True)
    nombre = (data.get("nombre") or "").strip()
    precio = data.get("precio")
    stock = data.get("stock", 0)
    stock_minimo = data.get("stock_minimo", 5)

    if not nombre or precio is None:
        return jsonify({"error": "nombre y precio son obligatorios"}), 400
    if precio < 0 or stock < 0:
        return jsonify({"error": "precio y stock deben ser >= 0"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO productos (nombre, precio, stock, stock_minimo) VALUES (?, ?, ?, ?)",
        (nombre, precio, stock, stock_minimo),
    )
    db.commit()
    nuevo = db.execute(
        "SELECT * FROM productos WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(dict(nuevo)), 201


@app.route("/api/productos/<int:producto_id>", methods=["PUT"])
def actualizar_producto(producto_id):
    db = get_db()
    existente = db.execute(
        "SELECT * FROM productos WHERE id = ?", (producto_id,)
    ).fetchone()
    if existente is None:
        return jsonify({"error": "Producto no encontrado"}), 404

    data = request.get_json(force=True)
    nombre = data.get("nombre", existente["nombre"])
    precio = data.get("precio", existente["precio"])
    stock = data.get("stock", existente["stock"])
    stock_minimo = data.get("stock_minimo", existente["stock_minimo"])

    db.execute(
        "UPDATE productos SET nombre=?, precio=?, stock=?, stock_minimo=? WHERE id=?",
        (nombre, precio, stock, stock_minimo, producto_id),
    )
    db.commit()
    actualizado = db.execute(
        "SELECT * FROM productos WHERE id = ?", (producto_id,)
    ).fetchone()
    return jsonify(dict(actualizado))


@app.route("/api/productos/<int:producto_id>", methods=["DELETE"])
def eliminar_producto(producto_id):
    db = get_db()
    existente = db.execute(
        "SELECT * FROM productos WHERE id = ?", (producto_id,)
    ).fetchone()
    if existente is None:
        return jsonify({"error": "Producto no encontrado"}), 404

    db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    db.commit()
    return jsonify({"mensaje": "Producto eliminado"}), 200


@app.route("/api/productos/<int:producto_id>/venta", methods=["POST"])
def registrar_venta(producto_id):
    """Descuenta stock al registrar una venta (HU-04)."""
    data = request.get_json(force=True)
    cantidad = data.get("cantidad", 1)

    db = get_db()
    producto = db.execute(
        "SELECT * FROM productos WHERE id = ?", (producto_id,)
    ).fetchone()
    if producto is None:
        return jsonify({"error": "Producto no encontrado"}), 404
    if producto["stock"] < cantidad:
        return jsonify({"error": "Stock insuficiente"}), 400

    nuevo_stock = producto["stock"] - cantidad
    db.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, producto_id))
    db.commit()

    alerta = nuevo_stock <= producto["stock_minimo"]
    return jsonify({
        "mensaje": "Venta registrada",
        "stock_restante": nuevo_stock,
        "alerta_stock_bajo": alerta,
    })


@app.route("/api/reportes/resumen", methods=["GET"])
def resumen_dashboard():
    """Datos para el dashboard (HU-05)."""
    db = get_db()
    total_productos = db.execute("SELECT COUNT(*) c FROM productos").fetchone()["c"]
    stock_bajo = db.execute(
        "SELECT COUNT(*) c FROM productos WHERE stock <= stock_minimo"
    ).fetchone()["c"]
    valor_inventario = db.execute(
        "SELECT COALESCE(SUM(precio * stock), 0) v FROM productos"
    ).fetchone()["v"]
    return jsonify({
        "total_productos": total_productos,
        "productos_con_stock_bajo": stock_bajo,
        "valor_total_inventario": round(valor_inventario, 2),
    })


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
else:
    # asegura que la DB exista cuando se importa (p.ej. en tests)
    init_db()
