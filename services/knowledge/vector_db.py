"""
Weaviate vector database interface
Manages code embeddings and semantic search
"""

import hashlib
import os
from typing import Dict, List, Optional

import structlog
import weaviate
from weaviate.classes.config import Configure, DataType, Property

logger = structlog.get_logger()


class VectorDB:
    """Weaviate vector database manager"""

    def __init__(self):
        self.url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
        self.client = None
        self.collection_name = "CodeSnippet"

    async def connect(self):
        """Connect to Weaviate"""
        try:
            self.client = weaviate.connect_to_custom(
                http_host=self.url.replace("http://", "").replace("https://", "").split(":")[0],
                http_port=8080,
                http_secure=False,
                grpc_host=self.url.replace("http://", "").replace("https://", "").split(":")[0],
                grpc_port=50051,
                grpc_secure=False,
            )

            # Test connection
            if not self.client.is_ready():
                raise ConnectionError("Weaviate is not ready")

            logger.info("Connected to Weaviate")

            # Setup schema
            await self._setup_schema()

        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise

    async def close(self):
        """Close Weaviate connection"""
        if self.client:
            self.client.close()
            logger.info("Weaviate connection closed")

    async def is_connected(self) -> bool:
        """Check if connected to Weaviate"""
        if not self.client:
            return False
        try:
            return self.client.is_ready()
        except Exception:
            return False

    async def _setup_schema(self):
        """Setup Weaviate schema"""
        try:
            # Check if collection exists
            if not self.client.collections.exists(self.collection_name):
                # Create collection
                self.client.collections.create(
                    name=self.collection_name,
                    vectorizer_config=Configure.Vectorizer.none(),
                    properties=[
                        Property(name="content", data_type=DataType.TEXT),
                        Property(name="language", data_type=DataType.TEXT),
                        Property(name="file_path", data_type=DataType.TEXT),
                        Property(name="repo_id", data_type=DataType.TEXT),
                        Property(name="function_name", data_type=DataType.TEXT),
                        Property(name="start_line", data_type=DataType.INT),
                        Property(name="end_line", data_type=DataType.INT),
                        Property(name="snippet_type", data_type=DataType.TEXT),
                    ],
                )
                logger.info(f"Created Weaviate collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to setup schema: {e}")
            raise

    async def index_code(
        self,
        content: str,
        embedding: List[float],
        repo_id: str,
        file_path: str,
        language: str,
        function_name: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        snippet_type: str = "function",
    ) -> str:
        """Index a code snippet with its embedding"""
        # Generate unique ID
        doc_id = hashlib.md5(
            f"{repo_id}:{file_path}:{function_name or start_line}".encode()
        ).hexdigest()

        try:
            collection = self.client.collections.get(self.collection_name)

            # Check if already exists
            try:
                existing = collection.query.fetch_object_by_id(doc_id)
                if existing:
                    # Delete existing
                    collection.data.delete_by_id(doc_id)
            except Exception:
                pass

            # Insert new document
            obj = {
                "content": content,
                "language": language,
                "file_path": file_path,
                "repo_id": repo_id,
                "function_name": function_name or "",
                "start_line": start_line or 0,
                "end_line": end_line or 0,
                "snippet_type": snippet_type,
            }

            collection.data.insert(
                properties=obj,
                vector=embedding,
                uuid=doc_id,
            )

            return doc_id

        except Exception as e:
            logger.error(f"Failed to index code: {e}")
            raise

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search code using vector similarity"""
        # Note: This requires an embedding model to convert query to vector
        # For now, return an empty list - in production, use the LLM service
        # to generate embeddings
        logger.warning("Vector search requires embeddings - implement with LLM service")
        return []

    async def find_similar(
        self,
        code: str,
        embedding: List[float],
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Find code similar to the provided embedding"""
        try:
            collection = self.client.collections.get(self.collection_name)

            # Build filter
            filter_clause = None
            if language:
                from weaviate.classes.query import Filter

                filter_clause = Filter.by_property("language").equal(language)

            # Perform vector search
            results = collection.query.near_vector(
                near_vector=embedding,
                limit=limit,
                filters=filter_clause,
                return_metadata=["distance"],
            )

            similar = []
            for obj in results.objects:
                similar.append(
                    {
                        "id": str(obj.uuid),
                        "content": obj.properties.get("content"),
                        "language": obj.properties.get("language"),
                        "file_path": obj.properties.get("file_path"),
                        "function_name": obj.properties.get("function_name"),
                        "score": 1.0 - (obj.metadata.distance or 0),
                    }
                )

            return similar

        except Exception as e:
            logger.error(f"Similar code search failed: {e}")
            return []

    async def delete_repo(self, repo_id: str):
        """Delete all vectors for a repository"""
        try:
            collection = self.client.collections.get(self.collection_name)

            from weaviate.classes.query import Filter

            filter_clause = Filter.by_property("repo_id").equal(repo_id)

            # Delete all matching objects
            collection.data.delete_many(
                where=filter_clause,
            )

            logger.info(f"Deleted vectors for repo {repo_id}")

        except Exception as e:
            logger.error(f"Failed to delete repo vectors: {e}")
            raise

    async def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            collection = self.client.collections.get(self.collection_name)

            # Get count
            agg = collection.aggregate.over_all()
            total_count = agg.total_count

            return {
                "total_vectors": total_count,
                "collection": self.collection_name,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_vectors": 0, "error": str(e)}
