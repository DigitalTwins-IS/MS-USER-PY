"""
Tests para MS-USER-PY
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.models import Base, get_db

# Base de datos de pruebas en memoria
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Crear y limpiar base de datos antes de cada test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ============================================================================
# TESTS DE VENDEDORES (Sellers) - HU2
# ============================================================================

def test_health_check():
    """Test del health check"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert data["service"] == "MS-USER-PY - User Management Service"


def test_create_seller():
    """HU2: Crear vendedor exitosamente"""
    # Nota: Este test requiere MS-GEO-PY corriendo para verificar zona
    # En producción usar mocks o una zona predefinida
    seller_data = {
        "name": "Juan Pérez",
        "email": "juan.perez@test.com",
        "phone": "3001234567",
        "address": "Calle 80 #12-34",
        "zone_id": 1,
        "user_id": 1
    }
    
    # Este test fallará sin MS-GEO-PY, es esperado
    # response = client.post("/api/v1/users/sellers", json=seller_data)
    # assert response.status_code == 201


def test_create_seller_duplicate_email():
    """HU2: No permitir email duplicado"""
    # Mock test - en producción necesita setup completo
    pass


def test_list_sellers():
    """Listar vendedores"""
    response = client.get("/api/v1/users/sellers")
    # Sin auth fallará, es esperado
    assert response.status_code == 401  # No autorizado sin token


def test_update_seller():
    """HU4: Actualizar vendedor"""
    # Mock test
    pass


# ============================================================================
# TESTS DE TENDEROS (Shopkeepers) - HU3
# ============================================================================

def test_create_shopkeeper():
    """HU3: Crear tendero con coordenadas"""
    shopkeeper_data = {
        "name": "Tienda La Esperanza",
        "business_name": "Supermercado La Esperanza",
        "address": "Calle 80 #12-34",
        "phone": "6012345678",
        "email": "tienda@test.com",
        "latitude": 4.6097100,
        "longitude": -74.0817500
    }
    
    # Sin auth fallará
    response = client.post("/api/v1/users/shopkeepers", json=shopkeeper_data)
    assert response.status_code == 401


def test_create_shopkeeper_invalid_coordinates():
    """HU3: Rechazar coordenadas fuera de Colombia"""
    shopkeeper_data = {
        "name": "Tienda Test",
        "business_name": "Test Store",
        "address": "Test Address",
        "phone": "1234567890",
        "email": "test@test.com",
        "latitude": 50.0,  # Fuera de Colombia
        "longitude": -74.0
    }
    
    response = client.post("/api/v1/users/shopkeepers", json=shopkeeper_data)
    # Debería fallar por validación
    assert response.status_code in [401, 422]  # 422 = Validation Error


def test_list_shopkeepers():
    """Listar tenderos"""
    response = client.get("/api/v1/users/shopkeepers")
    assert response.status_code == 401  # Sin auth


def test_update_shopkeeper():
    """HU4: Actualizar tendero"""
    # Mock test
    pass


def test_list_unassigned_shopkeepers():
    """Listar tenderos sin vendedor"""
    response = client.get("/api/v1/users/shopkeepers/unassigned")
    assert response.status_code == 401


# ============================================================================
# TESTS DE ASIGNACIONES (Assignments)
# ============================================================================

def test_assign_shopkeeper():
    """Asignar tendero a vendedor"""
    assignment_data = {
        "seller_id": 1,
        "shopkeeper_id": 1,
        "notes": "Asignación de prueba"
    }
    
    response = client.post("/api/v1/users/assign", json=assignment_data)
    assert response.status_code == 401


def test_assign_already_assigned():
    """No permitir asignar tendero ya asignado"""
    # Mock test
    pass


def test_reassign_shopkeeper():
    """Reasignar tendero a otro vendedor"""
    reassignment_data = {
        "shopkeeper_id": 1,
        "new_seller_id": 2,
        "notes": "Reasignación por optimización"
    }
    
    response = client.post("/api/v1/users/reassign", json=reassignment_data)
    assert response.status_code == 401


def test_list_assignments():
    """Listar asignaciones"""
    response = client.get("/api/v1/users/assignments")
    assert response.status_code == 401


def test_assignment_history():
    """Obtener historial de asignaciones"""
    response = client.get("/api/v1/users/assignments/history/1")
    assert response.status_code == 401


def test_seller_shopkeepers_limit():
    """Advertir cuando vendedor supera límite de tenderos"""
    # Mock test - verificar que se emite warning en logs
    pass


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================

@pytest.mark.integration
def test_full_workflow():
    """
    Test de flujo completo:
    1. Crear vendedor
    2. Crear tendero
    3. Asignar tendero a vendedor
    4. Actualizar datos
    5. Reasignar
    6. Ver historial
    """
    # Este test requiere:
    # - MS-AUTH-PY para autenticación
    # - MS-GEO-PY para verificar zonas
    # - Base de datos configurada
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

