from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db.sessions import get_session
from app.main import app
from app.routers.rpn import Calculator

# Setup in-memory database for testing


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# Test cases for stack CRUD operations


def test_create_stack(client):
    response = client.post("/rpn/stack", json={"content": [1.0, 2.0, 3.0]})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "created_at" in data
    assert data["content"] == [1.0, 2.0, 3.0]


def test_create_invalid_stack(client):
    # Test with non-numeric values
    response = client.post("/rpn/stack", json={"content": [1, "two", 3]})
    assert response.status_code == 422


def test_get_stacks(client):
    # Create some test stacks
    stack1 = client.post("/rpn/stack", json={"content": [1.0, 2.0]}).json()
    stack2 = client.post("/rpn/stack", json={"content": [3.0, 4.0]}).json()

    response = client.get("/rpn/stack")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(stack["id"] == stack1["id"] for stack in data)
    assert any(stack["id"] == stack2["id"] for stack in data)


def test_get_stack(client):
    # Create a test stack
    stack = client.post("/rpn/stack", json={"content": [1.0, 2.0]}).json()
    stack_id = stack["id"]

    response = client.get(f"/rpn/stack/{stack_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == stack_id
    assert data["content"] == [1.0, 2.0]


def test_get_nonexistent_stack(client):
    response = client.get(
        f"/rpn/stack/{UUID('00000000-0000-0000-0000-000000000000')}"
    )
    assert response.status_code == 404


def test_delete_stack(client):
    # Create a test stack
    stack = client.post("/rpn/stack", json={"content": [1.0, 2.0]}).json()
    stack_id = stack["id"]

    # Delete the stack
    response = client.delete(f"/rpn/stack/{stack_id}")
    assert response.status_code == 200

    # Verify stack is deleted
    response = client.get(f"/rpn/stack/{stack_id}")
    assert response.status_code == 404


def test_stack_not_found(client):
    stack_id = UUID("00000000-0000-0000-0000-000000000000")
    op = "add"

    # update
    response = client.post(f"/rpn/stack/{stack_id}?new_value=3.0")
    assert response.status_code == 404

    # delete
    response = client.delete(f"rpn/stack/{stack_id}")
    assert response.status_code == 404

    # apply operand
    response = client.post(f"/rpn/op/{op}/stack/{stack_id}")
    assert response.status_code == 404


def test_push_value_to_stack(client):
    # Create a test stack
    stack = client.post("/rpn/stack", json={"content": [1.0, 2.0]}).json()
    stack_id = stack["id"]

    # Push new value
    response = client.post(f"/rpn/stack/{stack_id}?new_value=3.0")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == [1.0, 2.0, 3.0]


def test_get_available_operands(client):
    response = client.get("/rpn/op")
    assert response.status_code == 200
    operands = response.json()
    assert all(
        op in operands for op in ["add", "multiply", "substract", "divide"]
    )


@pytest.mark.parametrize(
    "op,initial,expected",
    [
        ("add", [2.0, 3.0], [5.0]),
        ("substract", [5.0, 3.0], [2.0]),
        ("multiply", [2.0, 3.0], [6.0]),
        ("divide", [6.0, 2.0], [3.0]),
    ],
)
def test_apply_operand(client, op, initial, expected):
    # Create a test stack
    stack = client.post("/rpn/stack", json={"content": initial}).json()
    stack_id = stack["id"]

    # Apply operation
    response = client.post(f"/rpn/op/{op}/stack/{stack_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == expected


def test_division_by_zero(client):
    # Create a test stack with division by zero scenario
    stack = client.post("/rpn/stack", json={"content": [5.0, 0.0]}).json()
    stack_id = stack["id"]

    # Attempt division by zero
    response = client.post(f"/rpn/op/divide/stack/{stack_id}")
    assert response.status_code == 405


def test_invalid_operation(client):
    # Create a test stack
    stack = client.post("/rpn/stack", json={"content": [1.0, 2.0]}).json()
    stack_id = stack["id"]

    # Attempt invalid operation
    response = client.post(f"/rpn/op/invalid/stack/{stack_id}")
    assert response.status_code == 422


def test_pagination(client):
    # Create multiple stacks
    for i in range(5):
        client.post("/rpn/stack", json={"content": [float(i), float(i + 1)]})

    # Test with limit
    response = client.get("/rpn/stack?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Test with offset
    response = client.get("/rpn/stack?offset=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_calculator_edge_cases():
    input = ""
    with pytest.raises(HTTPException) as exc_info:
        Calculator(input)
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Stack content should be a list"

    input = [1, "two", 3]
    with pytest.raises(HTTPException) as exc_info:
        Calculator(input)
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "All elements in the stack should be float or integer"
    )

    input = [
        1,
    ]
    with pytest.raises(HTTPException) as exc_info:
        Calculator(input)
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail == "stack should contain at least twos elements"
    )


def test_operation_not_implemented():
    input = [1, 2, 3]
    op = "notimplemented"
    with pytest.raises(HTTPException) as exc_info:
        Calculator(input).apply_operand(op)
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 501
    assert exc_info.value.detail == "Operation not implemented"
