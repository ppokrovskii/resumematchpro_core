import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from azure.cosmos import DatabaseProxy
from azure.cosmos.exceptions import CosmosHttpResponseError
from dotenv import load_dotenv

from resumematchpro_core.repositories.jds_repository import JobDescriptionRepository
from resumematchpro_core.repositories.models import JobDescriptionDb
from resumematchpro_core.shared.exceptions import PermissionDeniedError

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")

# add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))


@pytest.fixture  # type: ignore[misc]
def repository(cosmos_client: DatabaseProxy) -> JobDescriptionRepository:
    """Create a JobDescriptionRepository instance for testing.

    Args:
        cosmos_client: The Cosmos DB client fixture.

    Returns:
        JobDescriptionRepository: A repository instance for testing.
    """
    return JobDescriptionRepository(cosmos_client)


@pytest.fixture(autouse=True)  # type: ignore[misc]
def run_around_tests(repository: JobDescriptionRepository) -> None:
    """Delete all items from the container before each test.

    Args:
        repository: The repository fixture.
    """
    repository.delete_all()


@pytest.fixture  # type: ignore[misc]
def sample_job_description() -> JobDescriptionDb:
    """Create a sample job description for testing.

    Returns:
        JobDescriptionDb: A sample job description model.
    """
    return JobDescriptionDb(
        id=str(uuid4()),
        user_id="test-user-id",
        title="Software Engineer",
        company="Test Company",
        location=None,
        description="Test job description",
        requirements=["Python", "Azure"],
        skills=["Python", "Azure", "Cloud"],
        experience_level=None,
        salary_range=None,
        employment_type=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        is_active=True,
        metadata=None,
    )


def test_upsert_job_description(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    # Create a sample job description
    jd = sample_job_description

    # Add the job description to the repository
    repository.upsert_job_description(jd.model_dump(mode="json"))

    # Retrieve the job description from the repository
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    assert len(jds) == 1
    assert jds[0].title == jd.title
    assert jds[0].company == jd.company


def test_upsert_job_description_empty_fields(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    # Create a sample job description with some empty fields
    jd = sample_job_description
    jd.location = None
    jd.salary_range = None

    # Add the job description to the repository
    repository.upsert_job_description(jd.model_dump(mode="json"))

    # Retrieve the job description from the repository
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    assert len(jds) == 1
    assert jds[0].title == jd.title
    assert jds[0].location is None
    assert jds[0].salary_range is None


def test_get_job_descriptions(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    # Create a sample job description
    jd = sample_job_description

    # Add the job description to the repository
    repository.upsert_job_description(jd.model_dump(mode="json"))

    # Retrieve the job description from the repository
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    assert len(jds) == 1
    assert jds[0].title == jd.title
    assert jds[0].company == jd.company


def test_get_job_descriptions_by_active_status(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    # Create two job descriptions - one active, one inactive
    jd_active = sample_job_description.model_copy()
    jd_inactive = sample_job_description.model_copy()
    jd_inactive.is_active = False
    jd_inactive.title = "Inactive Job"
    jd_inactive.id = str(uuid4())  # Set a different ID for the inactive job

    # Add both job descriptions to the repository
    active_dump = jd_active.model_dump(mode="json")
    inactive_dump = jd_inactive.model_dump(mode="json")
    logging.info(f"Active JD dump: {active_dump}")
    logging.info(f"Inactive JD dump: {inactive_dump}")

    repository.upsert_job_description(active_dump)
    repository.upsert_job_description(inactive_dump)

    # Query all items to see what's in the database
    all_items = list(repository.container.read_all_items())
    logging.info(f"All items in database: {all_items}")

    # Test getting only active job descriptions
    active_jds = repository.get_job_descriptions(
        user_id=jd_active.user_id, is_active=True
    )
    logging.info(f"Active JDs: {active_jds}")
    assert len(active_jds) == 1
    assert active_jds[0].title == jd_active.title

    # Test getting only inactive job descriptions
    inactive_jds = repository.get_job_descriptions(
        user_id=jd_active.user_id, is_active=False
    )
    logging.info(f"Inactive JDs: {inactive_jds}")
    assert len(inactive_jds) == 1
    assert inactive_jds[0].title == jd_inactive.title


def test_delete_job_description(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    # Create a sample job description
    jd = sample_job_description

    # Add the job description to the repository
    repository.upsert_job_description(jd.model_dump(mode="json"))

    # Get the job description ID
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    jd_id = jds[0].id

    # Delete the job description
    repository.delete_job_description(user_id=jd.user_id, job_description_id=jd_id)

    # Verify it's deleted
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    assert len(jds) == 0


def test_get_job_description_by_id(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    # Create a sample job description
    jd = sample_job_description

    # Add the job description to the repository
    repository.upsert_job_description(jd.model_dump(mode="json"))

    # Get the job description ID
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    jd_id = jds[0].id

    # Retrieve the job description by ID
    retrieved_jd = repository.get_job_description_by_id(
        user_id=jd.user_id, job_description_id=jd_id
    )
    assert retrieved_jd is not None
    assert retrieved_jd.title == jd.title
    assert retrieved_jd.company == jd.company


def test_get_job_description_by_id_not_found(
    repository: JobDescriptionRepository
) -> None:
    # Try to retrieve a non-existent job description
    jd = repository.get_job_description_by_id(
        user_id=str(uuid4()), job_description_id=str(uuid4())
    )
    assert jd is None


def test_get_job_description_by_id_wrong_user(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    # Create a sample job description
    jd = sample_job_description

    # Add the job description to the repository
    repository.upsert_job_description(jd.model_dump(mode="json"))

    # Get the job description ID
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    jd_id = jds[0].id

    # Try to retrieve with wrong user ID
    with pytest.raises(PermissionDeniedError):
        repository.get_job_description_by_id(
            user_id=str(uuid4()), job_description_id=jd_id
        )


def test_delete_job_description_not_found(
    repository: JobDescriptionRepository
) -> None:
    # Try to delete a non-existent job description
    result = repository.delete_job_description(
        user_id=str(uuid4()),
        job_description_id=str(uuid4()),
    )
    assert result is False


def test_delete_job_description_cosmos_error(
    repository: JobDescriptionRepository,
    monkeypatch: pytest.MonkeyPatch,
    sample_job_description: JobDescriptionDb,
) -> None:
    # Create a sample job description
    jd = sample_job_description
    repository.upsert_job_description(jd.model_dump(mode="json"))
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    jd_id = jds[0].id

    # Mock the delete_item method to raise CosmosHttpResponseError
    def mock_delete_item(*args: Any, **kwargs: Any) -> None:
        raise CosmosHttpResponseError(message="Test error")

    monkeypatch.setattr(repository.container, "delete_item", mock_delete_item)

    # Try to delete the job description
    with pytest.raises(CosmosHttpResponseError):
        repository.delete_job_description(user_id=jd.user_id, job_description_id=jd_id)


def test_get_job_description_by_id_cosmos_error(
    repository: JobDescriptionRepository,
    monkeypatch: pytest.MonkeyPatch,
    sample_job_description: JobDescriptionDb,
) -> None:
    # Create a sample job description
    jd = sample_job_description
    repository.upsert_job_description(jd.model_dump(mode="json"))
    jds = repository.get_job_descriptions(user_id=jd.user_id)
    jd_id = jds[0].id

    # Mock the query_items method to raise CosmosHttpResponseError
    def mock_query_items(*args: Any, **kwargs: Any) -> None:
        raise CosmosHttpResponseError(message="Test error")

    monkeypatch.setattr(repository.container, "query_items", mock_query_items)

    # Try to get the job description
    with pytest.raises(CosmosHttpResponseError):
        repository.get_job_description_by_id(user_id=jd.user_id, job_description_id=jd_id)


def test_upsert_job_description_cosmos_error(
    repository: JobDescriptionRepository,
    monkeypatch: pytest.MonkeyPatch,
    sample_job_description: JobDescriptionDb,
) -> None:
    # Create a sample job description
    jd = sample_job_description

    # Mock the upsert_item method to raise CosmosHttpResponseError
    def mock_upsert_item(*args: Any, **kwargs: Any) -> None:
        raise CosmosHttpResponseError(message="Test error")

    monkeypatch.setattr(repository.container, "upsert_item", mock_upsert_item)

    # Try to upsert the job description
    with pytest.raises(CosmosHttpResponseError):
        repository.upsert_job_description(jd.model_dump(mode="json"))


def test_delete_job_description_with_uuid(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    """Test deleting a job description with UUID."""
    # Arrange
    repository.upsert_job_description(sample_job_description.model_dump())
    job_descriptions = repository.get_job_descriptions(sample_job_description.user_id)
    assert len(job_descriptions) == 1

    # Act
    result = repository.delete_job_description(
        sample_job_description.user_id,
        sample_job_description.id
    )

    # Assert
    assert result is True
    job_descriptions = repository.get_job_descriptions(sample_job_description.user_id)
    assert len(job_descriptions) == 0


def test_get_job_description_by_id_with_uuid(
    repository: JobDescriptionRepository, sample_job_description: JobDescriptionDb
) -> None:
    """Test getting a job description by ID with UUID."""
    # Arrange
    repository.upsert_job_description(sample_job_description.model_dump())
    job_descriptions = repository.get_job_descriptions(sample_job_description.user_id)
    assert len(job_descriptions) == 1

    # Act
    result = repository.get_job_description_by_id(
        sample_job_description.user_id,
        sample_job_description.id
    )

    # Assert
    assert result is not None
    assert result.id == sample_job_description.id
    assert result.user_id == sample_job_description.user_id
    assert result.title == sample_job_description.title
    assert result.company == sample_job_description.company
