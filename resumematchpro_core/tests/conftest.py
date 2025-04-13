from pathlib import Path

import pytest
from azure.cosmos import CosmosClient, DatabaseProxy
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")


@pytest.fixture(scope="session")  # type: ignore[misc]
def cosmos_client() -> DatabaseProxy:
    """Create a test database client."""
    endpoint = "https://127.0.0.1:8081"
    key = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
    client = CosmosClient(endpoint, key, connection_verify=False)
    return client.create_database_if_not_exists("resumematchpro_test")
