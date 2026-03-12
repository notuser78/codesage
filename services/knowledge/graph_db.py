"""
Neo4j graph database interface
Manages code relationships and dependencies
"""

import os
from typing import Dict, List, Optional

import structlog
from neo4j import AsyncGraphDatabase

logger = structlog.get_logger()


class GraphDB:
    """Neo4j graph database manager"""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "neo4j_secret")
        self.driver = None
    
    async def connect(self):
        """Connect to Neo4j"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Test connection
            await self.driver.verify_connectivity()
            logger.info("Connected to Neo4j")
            
            # Create constraints and indexes
            await self._setup_schema()
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")
    
    async def is_connected(self) -> bool:
        """Check if connected to Neo4j"""
        if not self.driver:
            return False
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception:
            return False
    
    async def _setup_schema(self):
        """Setup database schema with constraints and indexes"""
        constraints = [
            "CREATE CONSTRAINT repo_id IF NOT EXISTS FOR (r:Repository) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT file_id IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT function_id IF NOT EXISTS FOR (fn:Function) REQUIRE fn.id IS UNIQUE",
            "CREATE CONSTRAINT class_id IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
        ]
        
        indexes = [
            "CREATE INDEX repo_name IF NOT EXISTS FOR (r:Repository) ON (r.name)",
            "CREATE INDEX file_path IF NOT EXISTS FOR (f:File) ON (f.path)",
            "CREATE INDEX function_name IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
            "CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)",
        ]
        
        async with self.driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    logger.warning(f"Constraint creation failed (may already exist): {e}")
            
            for index in indexes:
                try:
                    await session.run(index)
                except Exception as e:
                    logger.warning(f"Index creation failed (may already exist): {e}")
    
    async def create_repo(self, repo_id: str, repo_url: str, name: str) -> bool:
        """Create a repository node"""
        query = """
        MERGE (r:Repository {id: $repo_id})
        SET r.url = $repo_url,
            r.name = $name,
            r.created_at = datetime()
        RETURN r
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, repo_id=repo_id, repo_url=repo_url, name=name)
            record = await result.single()
            return record is not None
    
    async def create_file(
        self,
        file_id: str,
        repo_id: str,
        path: str,
        language: str,
        lines: int,
    ) -> bool:
        """Create a file node"""
        query = """
        MATCH (r:Repository {id: $repo_id})
        MERGE (f:File {id: $file_id})
        SET f.path = $path,
            f.language = $language,
            f.lines = $lines
        MERGE (r)-[:CONTAINS]->(f)
        RETURN f
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                file_id=file_id,
                repo_id=repo_id,
                path=path,
                language=language,
                lines=lines,
            )
            record = await result.single()
            return record is not None
    
    async def create_function(
        self,
        function_id: str,
        file_id: str,
        name: str,
        line_start: int,
        line_end: int,
        complexity: Optional[int] = None,
        parameters: Optional[List[str]] = None,
        return_type: Optional[str] = None,
    ) -> bool:
        """Create a function node"""
        query = """
        MATCH (f:File {id: $file_id})
        MERGE (fn:Function {id: $function_id})
        SET fn.name = $name,
            fn.line_start = $line_start,
            fn.line_end = $line_end,
            fn.complexity = $complexity,
            fn.parameters = $parameters,
            fn.return_type = $return_type
        MERGE (f)-[:DEFINES]->(fn)
        RETURN fn
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                function_id=function_id,
                file_id=file_id,
                name=name,
                line_start=line_start,
                line_end=line_end,
                complexity=complexity,
                parameters=parameters or [],
                return_type=return_type,
            )
            record = await result.single()
            return record is not None
    
    async def create_call_relationship(
        self,
        caller_id: str,
        callee_id: str,
        call_type: str = "direct",
    ) -> bool:
        """Create a CALLS relationship between functions"""
        query = """
        MATCH (caller:Function {id: $caller_id})
        MATCH (callee:Function {id: $callee_id})
        MERGE (caller)-[:CALLS {type: $call_type}]->(callee)
        RETURN caller, callee
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                caller_id=caller_id,
                callee_id=callee_id,
                call_type=call_type,
            )
            record = await result.single()
            return record is not None
    
    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search the graph using full-text search"""
        # This requires AOC plugin for full-text search
        # For now, use a simple name-based search
        cypher = """
        MATCH (n)
        WHERE n.name CONTAINS $query OR n.path CONTAINS $query
        RETURN n, labels(n) as types,
               CASE 
                   WHEN n.name CONTAINS $query THEN 1.0
                   ELSE 0.5
               END as score
        LIMIT $limit
        """
        
        results = []
        async with self.driver.session() as session:
            result = await session.run(cypher, query=query, limit=limit)
            async for record in result:
                node = record["n"]
                results.append({
                    "id": node.get("id"),
                    "type": record["types"][0] if record["types"] else "Unknown",
                    "name": node.get("name") or node.get("path", "Unknown"),
                    "file_path": node.get("path"),
                    "language": node.get("language"),
                    "score": record["score"],
                    "snippet": None,
                })
        
        return results
    
    async def get_function(self, function_id: str) -> Optional[Dict]:
        """Get function details"""
        query = """
        MATCH (fn:Function {id: $function_id})
        OPTIONAL MATCH (fn)<-[:DEFINES]-(f:File)
        OPTIONAL MATCH (fn)-[:CALLS]->(callee:Function)
        OPTIONAL MATCH (fn)<-[:CALLS]-(caller:Function)
        RETURN fn, f.path as file_path,
               collect(DISTINCT callee.id) as calls,
               collect(DISTINCT caller.id) as called_by
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, function_id=function_id)
            record = await result.single()
            
            if not record:
                return None
            
            fn = record["fn"]
            return {
                "id": fn.get("id"),
                "name": fn.get("name"),
                "file_path": record["file_path"],
                "language": fn.get("language"),
                "line_start": fn.get("line_start"),
                "line_end": fn.get("line_end"),
                "complexity": fn.get("complexity"),
                "calls": record["calls"],
                "called_by": record["called_by"],
            }
    
    async def get_call_graph(self, function_id: str, depth: int = 3) -> Dict:
        """Get the call graph for a function"""
        query = """
        MATCH path = (start:Function {id: $function_id})-[:CALLS*1..$depth]->(end:Function)
        WITH start, end, path
        LIMIT 100
        RETURN start, end, relationships(path) as rels, nodes(path) as nodes
        """
        
        nodes = {}
        edges = []
        
        async with self.driver.session() as session:
            result = await session.run(query, function_id=function_id, depth=depth)
            async for record in result:
                for node in record["nodes"]:
                    node_id = node.get("id")
                    if node_id not in nodes:
                        nodes[node_id] = {
                            "id": node_id,
                            "name": node.get("name"),
                            "type": "Function",
                        }
                
                for rel in record["rels"]:
                    edges.append({
                        "source": rel.start_node.get("id"),
                        "target": rel.end_node.get("id"),
                        "type": rel.get("type", "direct"),
                    })
        
        return {
            "root": function_id,
            "nodes": list(nodes.values()),
            "edges": edges,
        }
    
    async def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute a custom Cypher query"""
        parameters = parameters or {}
        
        results = []
        async with self.driver.session() as session:
            result = await session.run(query, **parameters)
            async for record in result:
                results.append(dict(record))
        
        return results
    
    async def get_repo_statistics(self, repo_id: str) -> Dict:
        """Get statistics for a repository"""
        queries = {
            "files": "MATCH (:Repository {id: $repo_id})-[:CONTAINS]->(f:File) RETURN count(f) as count",
            "functions": "MATCH (:Repository {id: $repo_id})-[:CONTAINS]->(:File)-[:DEFINES]->(fn:Function) RETURN count(fn) as count",
            "classes": "MATCH (:Repository {id: $repo_id})-[:CONTAINS]->(:File)-[:DEFINES]->(c:Class) RETURN count(c) as count",
            "languages": "MATCH (:Repository {id: $repo_id})-[:CONTAINS]->(f:File) RETURN f.language as lang, count(*) as count",
        }
        
        stats = {"repo_id": repo_id}
        
        async with self.driver.session() as session:
            for key, query in queries.items():
                result = await session.run(query, repo_id=repo_id)
                if key == "languages":
                    languages = {}
                    async for record in result:
                        languages[record["lang"]] = record["count"]
                    stats[key] = languages
                else:
                    record = await result.single()
                    stats[key] = record["count"] if record else 0
        
        return stats
    
    async def delete_repo(self, repo_id: str):
        """Delete a repository and all its nodes"""
        query = """
        MATCH (r:Repository {id: $repo_id})
        OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
        OPTIONAL MATCH (f)-[:DEFINES]->(fn:Function)
        OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
        DETACH DELETE r, f, fn, c
        """
        
        async with self.driver.session() as session:
            await session.run(query, repo_id=repo_id)
        
        logger.info(f"Deleted repository {repo_id} from graph")
    
    async def list_repos(self, page: int = 1, page_size: int = 20) -> Dict:
        """List all repositories"""
        skip = (page - 1) * page_size
        
        query = """
        MATCH (r:Repository)
        RETURN r.id as id, r.name as name, r.url as url, r.created_at as created_at
        ORDER BY r.created_at DESC
        SKIP $skip LIMIT $limit
        """
        
        count_query = "MATCH (r:Repository) RETURN count(r) as total"
        
        repos = []
        async with self.driver.session() as session:
            result = await session.run(query, skip=skip, limit=page_size)
            async for record in result:
                repos.append({
                    "id": record["id"],
                    "name": record["name"],
                    "url": record["url"],
                    "created_at": record["created_at"].isoformat() if record["created_at"] else None,
                })
            
            count_result = await session.run(count_query)
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0
        
        return {
            "items": repos,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
