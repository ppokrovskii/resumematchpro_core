import os
from pathlib import Path

import pytest
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")


@pytest.fixture(scope="session")
def cosmos_client():
    """Create a session-scoped Cosmos DB client for testing."""
    endpoint = os.getenv("COSMOS_ENDPOINT", "https://localhost:8081")
    key = os.getenv(
        "COSMOS_KEY",
        "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
    )
    client = CosmosClient(endpoint, key, connection_verify=False)
    database = client.create_database_if_not_exists("resumematchpro_test")
    return database
