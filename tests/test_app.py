import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


@pytest.fixture
def client():
    import app as flask_app_module

    db_fd, db_path = tempfile.mkstemp()
    flask_app_module.DB_PATH = db_path
    flask_app_module.init_db()

    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_crear_y_listar_producto(client):
    res = client.post("/api/productos", json={
        "nombre": "Guineo", "precio": 0.5, "stock": 100, "stock_minimo": 10
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["nombre"] == "Guineo"

    res = client.get("/api/productos")
    assert res.status_code == 200
    assert len(res.get_json()) == 1


def test_crear_producto_sin_nombre_falla(client):
    res = client.post("/api/productos", json={"precio": 1.0})
    assert res.status_code == 400


def test_actualizar_producto(client):
    creado = client.post("/api/productos", json={
        "nombre": "Plátano", "precio": 0.3, "stock": 50
    }).get_json()

    res = client.put(f"/api/productos/{creado['id']}", json={"stock": 20})
    assert res.status_code == 200
    assert res.get_json()["stock"] == 20


def test_eliminar_producto(client):
    creado = client.post("/api/productos", json={
        "nombre": "Yuca", "precio": 0.8, "stock": 10
    }).get_json()

    res = client.delete(f"/api/productos/{creado['id']}")
    assert res.status_code == 200

    res = client.get(f"/api/productos/{creado['id']}")
    assert res.status_code == 404


def test_registrar_venta_descuenta_stock(client):
    creado = client.post("/api/productos", json={
        "nombre": "Cacao", "precio": 2.0, "stock": 10, "stock_minimo": 8
    }).get_json()

    res = client.post(f"/api/productos/{creado['id']}/venta", json={"cantidad": 3})
    assert res.status_code == 200
    body = res.get_json()
    assert body["stock_restante"] == 7
    assert body["alerta_stock_bajo"] is True


def test_registrar_venta_stock_insuficiente(client):
    creado = client.post("/api/productos", json={
        "nombre": "Maíz", "precio": 1.0, "stock": 2
    }).get_json()

    res = client.post(f"/api/productos/{creado['id']}/venta", json={"cantidad": 5})
    assert res.status_code == 400


def test_login_exitoso(client):
    res = client.post("/api/login", json={
        "email": "admin@inventario.com", "password": "admin123"
    })
    assert res.status_code == 200
    assert res.get_json()["usuario"]["rol"] == "admin"


def test_login_credenciales_invalidas(client):
    res = client.post("/api/login", json={
        "email": "admin@inventario.com", "password": "incorrecta"
    })
    assert res.status_code == 401


def test_session_y_logout(client):
    res = client.get("/api/session")
    assert res.get_json()["autenticado"] is False

    client.post("/api/login", json={
        "email": "vendedor@inventario.com", "password": "vendedor123"
    })
    res = client.get("/api/session")
    assert res.get_json()["autenticado"] is True

    client.post("/api/logout")
    res = client.get("/api/session")
    assert res.get_json()["autenticado"] is False
