import logging
from typing import Any
from uuid import UUID

from azure.cosmos import DatabaseProxy, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError

from resumematchpro_core.repositories.models import JobDescriptionDb
from resumematchpro_core.shared.exceptions import PermissionDeniedError


class JobDescriptionRepository:
    """Repository class for managing job descriptions in Azure Cosmos DB.

    This class provides methods for creating, reading, updating, and deleting job descriptions
    in a Cosmos DB container. It handles data persistence and retrieval while ensuring proper
    data validation and access control.

    Attributes:
        container: The Cosmos DB container instance used for storing job descriptions.

    Note:
        The container is created with a unique key policy enforcing uniqueness of
        (user_id, title, company) combinations and uses user_id as the partition key.
    """

    def __init__(self, db_client: DatabaseProxy):
        """Initialize the JobDescriptionRepository.

        Args:
            db_client: A DatabaseProxy instance for connecting to Cosmos DB.
        """
        container_id = "job_descriptions"
        unique_key_policy = {
            "uniqueKeys": [{"paths": ["/user_id", "/title", "/company"]}]
        }
        partition_key = PartitionKey(path="/user_id")
        self.container = db_client.create_container_if_not_exists(
            id=container_id,
            unique_key_policy=unique_key_policy,
            partition_key=partition_key,
        )

    def upsert_job_description(self, job_description: dict[str, Any]) -> JobDescriptionDb:
        """Create or update a job description in the database.

        This method will either create a new job description or update an existing one
        based on the combination of user_id, title, and company. If a matching document
        exists, it will be updated; otherwise, a new document will be created.

        Args:
            job_description: A dictionary containing the job description data.
                Must include 'user_id', 'title', and 'company' keys.

        Returns:
            JobDescriptionDb: The created or updated job description.

        Raises:
            CosmosHttpResponseError: If there's an error communicating with Cosmos DB.
        """
        logging.info(f"Upserting job description: {job_description}")
        # Convert is_active to string if it's a boolean
        if "is_active" in job_description and isinstance(job_description["is_active"], bool):
            job_description["is_active"] = str(job_description["is_active"]).lower()

        # Query to check if a document with the same user_id, title and company exists
        query = """
            SELECT * FROM c
            WHERE c.user_id = @user_id
            AND c.title = @title
            AND c.company = @company
        """
        parameters: list[dict[str, Any]] = [
            {"name": "@user_id", "value": job_description["user_id"]},
            {"name": "@title", "value": job_description["title"]},
            {"name": "@company", "value": job_description["company"]},
        ]
        items = list(self.container.query_items(query, parameters=parameters))
        if items:
            # Update the existing document
            job_description["id"] = items[0]["id"]
            result = self.container.upsert_item(job_description)
        else:
            # Create a new document
            result = self.container.upsert_item(job_description)
        logging.info(f"Upserted job description result: {result}")
        return JobDescriptionDb(**result)

    def get_job_descriptions(
        self, user_id: str, is_active: bool | None = None
    ) -> list[JobDescriptionDb]:
        """Retrieve all job descriptions for a specific user.

        Args:
            user_id: The ID of the user whose job descriptions to retrieve.
            is_active: Optional filter for active/inactive job descriptions.
                If None, returns all job descriptions regardless of status.

        Returns:
            list[JobDescriptionDb]: A list of job descriptions matching the criteria.

        Raises:
            CosmosHttpResponseError: If there's an error communicating with Cosmos DB.
        """
        query = "SELECT * FROM c WHERE c.user_id = @user_id"
        parameters: list[dict[str, Any]] = [{"name": "@user_id", "value": user_id}]

        if is_active is not None:
            query += " AND c.is_active = @is_active"
            parameters.append({"name": "@is_active", "value": str(is_active).lower()})

        logging.info(f"Executing query: {query} with parameters: {parameters}")
        items = list(self.container.query_items(query=query, parameters=parameters))
        logging.info(f"Found {len(items)} items: {items}")
        return [JobDescriptionDb(**item) for item in items]

    def delete_all(self) -> None:
        """Delete all job descriptions from the container.

        Warning:
            This is a destructive operation that removes all documents from the container.
            Use with caution, typically only in testing environments.

        Raises:
            CosmosHttpResponseError: If there's an error communicating with Cosmos DB.
        """
        items = list(self.container.read_all_items())
        for item in items:
            self.container.delete_item(item, partition_key=item["user_id"])

    def delete_job_description(
        self, user_id: str, job_description_id: str | UUID
    ) -> bool:
        """Delete a specific job description.

        Args:
            user_id: The ID of the user who owns the job description.
            job_description_id: The ID of the job description to delete.
                Can be either a string or UUID.

        Returns:
            bool: True if the job description was deleted, False if it wasn't found.

        Raises:
            PermissionDeniedError: If the job description exists but belongs to a different user.
            CosmosHttpResponseError: If there's an error communicating with Cosmos DB.
        """
        if isinstance(job_description_id, UUID):
            job_description_id = str(job_description_id)

        try:
            # First check if job description exists for any user
            query = "SELECT * FROM c WHERE c.id = @job_description_id"
            parameters: list[dict[str, Any]] = [
                {"name": "@job_description_id", "value": job_description_id}
            ]
            items = list(
                self.container.query_items(
                    query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            if not items:
                return False

            job_description = JobDescriptionDb(**items[0])
            if job_description.user_id != user_id:
                raise PermissionDeniedError(
                    "You don't have permission to access this job description"
                )

            self.container.delete_item(item=job_description_id, partition_key=user_id)
            return True

        except CosmosHttpResponseError as e:
            raise e

    def get_job_description_by_id(
        self, user_id: str, job_description_id: str | UUID
    ) -> JobDescriptionDb | None:
        """Retrieve a specific job description by its ID.

        Args:
            user_id: The ID of the user who owns the job description.
            job_description_id: The ID of the job description to retrieve.
                Can be either a string or UUID.

        Returns:
            JobDescriptionDb | None: The job description if found, None otherwise.

        Raises:
            PermissionDeniedError: If the job description exists but belongs to a different user.
            CosmosHttpResponseError: If there's an error communicating with Cosmos DB.
        """
        if isinstance(job_description_id, UUID):
            job_description_id = str(job_description_id)

        try:
            # First check if job description exists for any user
            query = "SELECT * FROM c WHERE c.id = @job_description_id"
            parameters: list[dict[str, Any]] = [
                {"name": "@job_description_id", "value": job_description_id}
            ]
            items = list(
                self.container.query_items(
                    query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            if not items:
                return None

            job_description = JobDescriptionDb(**items[0])
            if job_description.user_id != user_id:
                raise PermissionDeniedError(
                    "You don't have permission to access this job description"
                )
            return job_description

        except CosmosHttpResponseError as e:
            raise e
