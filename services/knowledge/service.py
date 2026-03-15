"""
CodeSage Knowledge Service
Manages code knowledge graph and vector search
"""

from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from graph_db import GraphDB
from indexer import CodeIndexer
from vector_db import VectorDB

logger = structlog.get_logger()

# Global instances
graph_db: Optional[GraphDB] = None
vector_db: Optional[VectorDB] = None
indexer: Optional[CodeIndexer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global graph_db, vector_db, indexer

    logger.info("Starting Knowledge Service")

    # Initialize databases
    graph_db = GraphDB()
    await graph_db.connect()

    vector_db = VectorDB()
    await vector_db.connect()

    indexer = CodeIndexer(graph_db, vector_db)

    logger.info("Knowledge Service ready")

    yield

    # Cleanup
    logger.info("Shutting down Knowledge Service")
    if graph_db:
        await graph_db.close()
    if vector_db:
        await vector_db.close()


app = FastAPI(
    title="CodeSage Knowledge Service",
    description="Knowledge graph and vector search for code",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    weaviate_connected: bool


class IndexRequest(BaseModel):
    repo_id: str
    repo_url: str
    files: List[Dict]
    analysis_results: Optional[Dict] = None


class IndexResponse(BaseModel):
    status: str
    repo_id: str
    nodes_created: int
    relationships_created: int
    vectors_indexed: int


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    search_type: str = "hybrid"  # semantic, graph, hybrid
    limit: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict] = None


class SearchResult(BaseModel):
    id: str
    type: str
    name: str
    file_path: Optional[str]
    language: Optional[str]
    score: float
    snippet: Optional[str]


class SimilarCodeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)


class GraphQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    parameters: Optional[Dict] = None


class FunctionNode(BaseModel):
    id: str
    name: str
    file_path: str
    language: str
    line_start: int
    line_end: int
    complexity: Optional[int]
    calls: List[str]
    called_by: List[str]


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    neo4j_ok = await graph_db.is_connected() if graph_db else False
    weaviate_ok = await vector_db.is_connected() if vector_db else False

    return HealthResponse(
        status="healthy" if (neo4j_ok and weaviate_ok) else "degraded",
        neo4j_connected=neo4j_ok,
        weaviate_connected=weaviate_ok,
    )


@app.post("/api/v1/index", response_model=IndexResponse)
async def index_repository(request: IndexRequest):
    """Index a repository for search"""
    if not indexer:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await indexer.index_repository(
            repo_id=request.repo_id,
            repo_url=request.repo_url,
            files=request.files,
            analysis_results=request.analysis_results,
        )

        return IndexResponse(
            status="completed",
            repo_id=request.repo_id,
            nodes_created=result.get("nodes_created", 0),
            relationships_created=result.get("relationships_created", 0),
            vectors_indexed=result.get("vectors_indexed", 0),
        )

    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/search", response_model=List[SearchResult])
async def search_code(request: SearchRequest):
    """Search code using semantic and/or graph search"""
    if not vector_db or not graph_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        results = []

        if request.search_type in ["semantic", "hybrid"]:
            semantic_results = await vector_db.search(
                query=request.query,
                limit=request.limit,
                filters=request.filters,
            )
            results.extend(semantic_results)

        if request.search_type in ["graph", "hybrid"]:
            graph_results = await graph_db.search(
                query=request.query,
                limit=request.limit,
            )
            results.extend(graph_results)

        # Deduplicate and sort by score
        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
            key = r.get("id")
            if key and key not in seen:
                seen.add(key)
                unique_results.append(SearchResult(**r))

        return unique_results[: request.limit]

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/similar")
async def find_similar_code(request: SimilarCodeRequest):
    """Find code similar to the provided snippet"""
    if not vector_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        results = await vector_db.find_similar(
            code=request.code,
            language=request.language,
            limit=request.limit,
        )

        return {
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"Similar code search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/functions/{function_id}")
async def get_function_details(function_id: str):
    """Get detailed information about a function"""
    if not graph_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        function = await graph_db.get_function(function_id)
        if not function:
            raise HTTPException(status_code=404, detail="Function not found")

        return function

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get function details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/functions/{function_id}/call-graph")
async def get_call_graph(function_id: str, depth: int = Query(3, ge=1, le=10)):
    """Get the call graph for a function"""
    if not graph_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        graph = await graph_db.get_call_graph(function_id, depth)
        return graph

    except Exception as e:
        logger.error(f"Failed to get call graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query/graph")
async def query_graph(request: GraphQueryRequest):
    """Execute a custom Cypher query"""
    if not graph_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        results = await graph_db.execute_query(request.query, request.parameters)
        return {"results": results}

    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/repos/{repo_id}/statistics")
async def get_repo_statistics(repo_id: str):
    """Get statistics for a repository"""
    if not graph_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        stats = await graph_db.get_repo_statistics(repo_id)
        return stats

    except Exception as e:
        logger.error(f"Failed to get repo statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/repos/{repo_id}")
async def delete_repository(repo_id: str):
    """Delete a repository and all its data"""
    if not graph_db or not vector_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Delete from graph database
        await graph_db.delete_repo(repo_id)

        # Delete from vector database
        await vector_db.delete_repo(repo_id)

        return {"status": "deleted", "repo_id": repo_id}

    except Exception as e:
        logger.error(f"Failed to delete repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/repos")
async def list_repositories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all indexed repositories"""
    if not graph_db:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        repos = await graph_db.list_repos(page, page_size)
        return repos

    except Exception as e:
        logger.error(f"Failed to list repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "service:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
