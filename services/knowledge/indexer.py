"""
Code indexer for building knowledge graph and vector index
"""

import hashlib
from typing import Dict, List, Optional

import httpx
import structlog

from graph_db import GraphDB
from vector_db import VectorDB

logger = structlog.get_logger()


class CodeIndexer:
    """Indexes code into graph and vector databases"""
    
    def __init__(self, graph_db: GraphDB, vector_db: VectorDB):
        self.graph_db = graph_db
        self.vector_db = vector_db
        self.llm_service_url = "http://llm:8000"  # Configurable
    
    async def index_repository(
        self,
        repo_id: str,
        repo_url: str,
        files: List[Dict],
        analysis_results: Optional[Dict] = None,
    ) -> Dict:
        """Index an entire repository"""
        logger.info(f"Indexing repository {repo_id}")
        
        nodes_created = 0
        relationships_created = 0
        vectors_indexed = 0
        
        # Create repository node
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        await self.graph_db.create_repo(repo_id, repo_url, repo_name)
        nodes_created += 1
        
        # Index each file
        for file_info in files:
            file_nodes, file_rels = await self._index_file(repo_id, file_info)
            nodes_created += file_nodes
            relationships_created += file_rels
        
        # Create call relationships from analysis results
        if analysis_results:
            await self._index_analysis_results(repo_id, analysis_results)
        
        return {
            "nodes_created": nodes_created,
            "relationships_created": relationships_created,
            "vectors_indexed": vectors_indexed,
        }
    
    async def _index_file(self, repo_id: str, file_info: Dict) -> tuple:
        """Index a single file"""
        nodes_created = 0
        relationships_created = 0
        
        file_path = file_info.get("path", "")
        language = file_info.get("language", "unknown")
        content = file_info.get("content", "")
        lines = file_info.get("lines", 0)
        
        # Generate file ID
        file_id = hashlib.md5(f"{repo_id}:{file_path}".encode()).hexdigest()
        
        # Create file node
        await self.graph_db.create_file(file_id, repo_id, file_path, language, lines)
        nodes_created += 1
        
        # Index functions
        for func in file_info.get("functions", []):
            func_id = hashlib.md5(
                f"{repo_id}:{file_path}:{func['name']}".encode()
            ).hexdigest()
            
            await self.graph_db.create_function(
                function_id=func_id,
                file_id=file_id,
                name=func["name"],
                line_start=func.get("line_start", 0),
                line_end=func.get("line_end", 0),
                complexity=func.get("complexity"),
                parameters=func.get("parameters"),
                return_type=func.get("return_type"),
            )
            nodes_created += 1
            
            # Get embedding and index in vector DB
            try:
                func_content = self._extract_function_content(content, func)
                embedding = await self._get_embedding(func_content)
                
                if embedding:
                    await self.vector_db.index_code(
                        content=func_content,
                        embedding=embedding,
                        repo_id=repo_id,
                        file_path=file_path,
                        language=language,
                        function_name=func["name"],
                        start_line=func.get("line_start"),
                        end_line=func.get("line_end"),
                    )
            except Exception as e:
                logger.warning(f"Failed to index function {func['name']}: {e}")
        
        # Index classes
        for cls in file_info.get("classes", []):
            cls_id = hashlib.md5(
                f"{repo_id}:{file_path}:{cls['name']}".encode()
            ).hexdigest()
            
            # Create class node (would need to add to graph_db)
            nodes_created += 1
        
        return nodes_created, relationships_created
    
    async def _index_analysis_results(self, repo_id: str, analysis_results: Dict):
        """Index analysis results into the graph"""
        # Index security findings
        security = analysis_results.get("security", {})
        for finding in security.get("findings", []):
            # Could create Vulnerability nodes
            pass
        
        # Index call graph
        call_graph = analysis_results.get("call_graph", {})
        for caller_id, callees in call_graph.get("edges", {}).items():
            for callee_id in callees:
                await self.graph_db.create_call_relationship(caller_id, callee_id)
    
    def _extract_function_content(self, file_content: str, func: Dict) -> str:
        """Extract function content from file"""
        lines = file_content.split("\n")
        start = func.get("line_start", 1) - 1
        end = func.get("line_end", len(lines))
        
        return "\n".join(lines[start:end])
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from LLM service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.llm_service_url}/embeddings",
                    json={"texts": [text[:5000]]},  # Limit text length
                    timeout=30.0,
                )
                response.raise_for_status()
                
                data = response.json()
                embeddings = data.get("embeddings", [])
                
                return embeddings[0] if embeddings else None
                
        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
            return None
    
    async def update_index(self, repo_id: str, changed_files: List[Dict]):
        """Update index for changed files"""
        logger.info(f"Updating index for {len(changed_files)} files in {repo_id}")
        
        for file_info in changed_files:
            # Delete old file data
            file_path = file_info.get("path", "")
            file_id = hashlib.md5(f"{repo_id}:{file_path}".encode()).hexdigest()
            
            # Re-index file
            await self._index_file(repo_id, file_info)
    
    async def delete_index(self, repo_id: str):
        """Delete all index data for a repository"""
        logger.info(f"Deleting index for {repo_id}")
        
        await self.graph_db.delete_repo(repo_id)
        await self.vector_db.delete_repo(repo_id)
