"""
AST Parser for multiple programming languages
Uses tree-sitter for parsing
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import structlog
from tree_sitter import Language, Parser, Tree, Node

logger = structlog.get_logger()

# Language extensions mapping
LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "javascript": [".js", ".jsx", ".mjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "go": [".go"],
    "rust": [".rs"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
    "c": [".c", ".h"],
    "csharp": [".cs"],
    "php": [".php"],
    "ruby": [".rb"],
}


@dataclass
class FunctionInfo:
    """Information about a function/method"""

    name: str
    start_line: int
    end_line: int
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    complexity: int = 1
    docstring: Optional[str] = None


@dataclass
class ClassInfo:
    """Information about a class"""

    name: str
    start_line: int
    end_line: int
    methods: List[FunctionInfo] = field(default_factory=list)
    parent_classes: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class ImportInfo:
    """Information about an import statement"""

    module: str
    names: List[str] = field(default_factory=list)
    is_from_import: bool = False
    line: int = 0


@dataclass
class ParsedFile:
    """Result of parsing a source file"""

    language: str
    file_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    ast: Optional[Any] = None
    raw_tree: Optional[Tree] = None
    errors: List[str] = field(default_factory=list)


class ASTParser:
    """Multi-language AST parser using tree-sitter"""

    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}
        self._load_languages()

    def _load_languages(self):
        """Load tree-sitter language parsers"""
        try:
            # Try to import language modules
            languages_to_load = [
                ("python", "tree_sitter_python"),
                ("javascript", "tree_sitter_javascript"),
                ("java", "tree_sitter_java"),
                ("go", "tree_sitter_go"),
                ("rust", "tree_sitter_rust"),
                ("cpp", "tree_sitter_cpp"),
            ]

            for lang_name, module_name in languages_to_load:
                try:
                    module = __import__(module_name)
                    language = Language(module.language())
                    self.languages[lang_name] = language

                    parser = Parser()
                    parser.set_language(language)
                    self.parsers[lang_name] = parser

                    logger.debug(f"Loaded {lang_name} parser")
                except ImportError:
                    logger.warning(f"Could not load {lang_name} parser")

        except Exception as e:
            logger.error(f"Error loading languages: {e}")

    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        for lang, extensions in LANGUAGE_EXTENSIONS.items():
            if ext in extensions:
                return lang
        return None

    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse a source file"""
        language = self.detect_language(file_path)
        if not language:
            return ParsedFile(
                language="unknown",
                file_path=file_path,
                errors=[f"Unknown file type: {file_path}"],
            )

        if language not in self.parsers:
            return ParsedFile(
                language=language,
                file_path=file_path,
                errors=[f"Parser not available for {language}"],
            )

        try:
            if content is None:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
        except Exception as e:
            return ParsedFile(
                language=language,
                file_path=file_path,
                errors=[f"Could not read file: {e}"],
            )

        return self.parse_string(content, language, file_path)

    def parse_string(self, content: str, language: str, file_path: str = "<string>") -> ParsedFile:
        """Parse source code from string"""
        if language not in self.parsers:
            return ParsedFile(
                language=language,
                file_path=file_path,
                errors=[f"Parser not available for {language}"],
            )

        parser = self.parsers[language]
        tree = parser.parse(bytes(content, "utf8"))

        result = ParsedFile(
            language=language,
            file_path=file_path,
            raw_tree=tree,
        )

        # Extract information based on language
        if language == "python":
            self._extract_python_info(tree, content, result)
        elif language in ["javascript", "typescript"]:
            self._extract_javascript_info(tree, content, result)
        elif language == "java":
            self._extract_java_info(tree, content, result)
        elif language == "go":
            self._extract_go_info(tree, content, result)
        else:
            # Generic extraction
            self._extract_generic_info(tree, content, result)

        return result

    def _extract_python_info(self, tree: Tree, content: str, result: ParsedFile):
        """Extract information from Python AST"""
        root = tree.root_node

        def walk_node(node: Node):
            if node.type == "function_definition":
                func = self._parse_python_function(node, content)
                if func:
                    result.functions.append(func)

            elif node.type == "class_definition":
                cls = self._parse_python_class(node, content)
                if cls:
                    result.classes.append(cls)

            elif node.type == "import_statement":
                imp = self._parse_python_import(node, content)
                if imp:
                    result.imports.append(imp)

            elif node.type == "import_from_statement":
                imp = self._parse_python_from_import(node, content)
                if imp:
                    result.imports.append(imp)

            for child in node.children:
                walk_node(child)

        walk_node(root)

    def _parse_python_function(self, node: Node, content: str) -> Optional[FunctionInfo]:
        """Parse a Python function definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.children:
                if param.type in ("identifier", "typed_parameter", "default_parameter"):
                    param_text = content[param.start_byte : param.end_byte]
                    params.append(param_text)

        # Get return type
        return_type = None
        return_node = node.child_by_field_name("return_type")
        if return_node:
            return_type = content[return_node.start_byte : return_node.end_byte]

        # Calculate complexity
        complexity = self._calculate_complexity(node)

        return FunctionInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=params,
            return_type=return_type,
            complexity=complexity,
        )

    def _parse_python_class(self, node: Node, content: str) -> Optional[ClassInfo]:
        """Parse a Python class definition"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Get parent classes
        parents = []
        superclasses = node.child_by_field_name("superclasses")
        if superclasses:
            for child in superclasses.children:
                if child.type == "identifier":
                    parents.append(content[child.start_byte : child.end_byte])

        # Get methods
        body = node.child_by_field_name("body")
        methods = []
        if body:
            for child in body.children:
                if child.type == "function_definition":
                    func = self._parse_python_function(child, content)
                    if func:
                        methods.append(func)

        return ClassInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            methods=methods,
            parent_classes=parents,
        )

    def _parse_python_import(self, node: Node, content: str) -> Optional[ImportInfo]:
        """Parse Python import statement"""
        names = []
        for child in node.children:
            if child.type == "dotted_name" or child.type == "identifier":
                names.append(content[child.start_byte : child.end_byte])

        if names:
            return ImportInfo(
                module=names[0],
                names=names[1:],
                is_from_import=False,
                line=node.start_point[0] + 1,
            )
        return None

    def _parse_python_from_import(self, node: Node, content: str) -> Optional[ImportInfo]:
        """Parse Python from...import statement"""
        module = None
        names = []

        for child in node.children:
            if child.type == "dotted_name":
                if module is None:
                    module = content[child.start_byte : child.end_byte]
                else:
                    names.append(content[child.start_byte : child.end_byte])
            elif child.type == "identifier" and module is None:
                module = content[child.start_byte : child.end_byte]

        if module:
            return ImportInfo(
                module=module,
                names=names,
                is_from_import=True,
                line=node.start_point[0] + 1,
            )
        return None

    def _extract_javascript_info(self, tree: Tree, content: str, result: ParsedFile):
        """Extract information from JavaScript/TypeScript AST"""
        root = tree.root_node

        def walk_node(node: Node):
            if node.type in (
                "function_declaration",
                "function",
                "arrow_function",
                "method_definition",
            ):
                func = self._parse_javascript_function(node, content)
                if func:
                    result.functions.append(func)

            elif node.type == "class_declaration":
                cls = self._parse_javascript_class(node, content)
                if cls:
                    result.classes.append(cls)

            elif node.type in ("import_statement", "import_declaration"):
                imp = self._parse_javascript_import(node, content)
                if imp:
                    result.imports.append(imp)

            for child in node.children:
                walk_node(child)

        walk_node(root)

    def _parse_javascript_function(self, node: Node, content: str) -> Optional[FunctionInfo]:
        """Parse a JavaScript function"""
        name = "<anonymous>"

        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
        elif node.type == "method_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]

        params = []
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            params_node = node.child_by_field_name("params")

        if params_node:
            for param in params_node.children:
                if param.type in ("identifier", "formal_parameter"):
                    param_text = content[param.start_byte : param.end_byte]
                    params.append(param_text)

        complexity = self._calculate_complexity(node)

        return FunctionInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=params,
            complexity=complexity,
        )

    def _parse_javascript_class(self, node: Node, content: str) -> Optional[ClassInfo]:
        """Parse a JavaScript class"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Get parent class
        parents = []
        super_class = node.child_by_field_name("superclass")
        if super_class:
            parent_text = content[super_class.start_byte : super_class.end_byte]
            parents.append(parent_text)

        # Get methods
        body = node.child_by_field_name("body")
        methods = []
        if body:
            for child in body.children:
                if child.type == "method_definition":
                    func = self._parse_javascript_function(child, content)
                    if func:
                        methods.append(func)

        return ClassInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            methods=methods,
            parent_classes=parents,
        )

    def _parse_javascript_import(self, node: Node, content: str) -> Optional[ImportInfo]:
        """Parse JavaScript import statement"""
        source = node.child_by_field_name("source")
        if not source:
            return None

        module = content[source.start_byte : source.end_byte]
        module = module.strip("'\"")

        names = []
        clause = node.child_by_field_name("clause")
        if clause:
            for child in clause.children:
                if child.type == "identifier":
                    names.append(content[child.start_byte : child.end_byte])

        return ImportInfo(
            module=module,
            names=names,
            is_from_import=True,
            line=node.start_point[0] + 1,
        )

    def _extract_java_info(self, tree: Tree, content: str, result: ParsedFile):
        """Extract information from Java AST"""
        # Simplified Java parsing
        root = tree.root_node

        def walk_node(node: Node):
            if node.type == "method_declaration":
                func = self._parse_java_method(node, content)
                if func:
                    result.functions.append(func)

            elif node.type == "class_declaration":
                cls = self._parse_java_class(node, content)
                if cls:
                    result.classes.append(cls)

            for child in node.children:
                walk_node(child)

        walk_node(root)

    def _parse_java_method(self, node: Node, content: str) -> Optional[FunctionInfo]:
        """Parse a Java method"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.children:
                if param.type == "formal_parameter":
                    param_text = content[param.start_byte : param.end_byte]
                    params.append(param_text)

        return_type = None
        type_node = node.child_by_field_name("type")
        if type_node:
            return_type = content[type_node.start_byte : type_node.end_byte]

        return FunctionInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=params,
            return_type=return_type,
        )

    def _parse_java_class(self, node: Node, content: str) -> Optional[ClassInfo]:
        """Parse a Java class"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        return ClassInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
        )

    def _extract_go_info(self, tree: Tree, content: str, result: ParsedFile):
        """Extract information from Go AST"""
        # Simplified Go parsing
        root = tree.root_node

        def walk_node(node: Node):
            if node.type == "function_declaration":
                func = self._parse_go_function(node, content)
                if func:
                    result.functions.append(func)

            for child in node.children:
                walk_node(child)

        walk_node(root)

    def _parse_go_function(self, node: Node, content: str) -> Optional[FunctionInfo]:
        """Parse a Go function"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        return FunctionInfo(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
        )

    def _extract_generic_info(self, tree: Tree, content: str, result: ParsedFile):
        """Generic AST information extraction"""

        # Count total nodes as basic metric
        def count_nodes(node: Node) -> int:
            count = 1
            for child in node.children:
                count += count_nodes(child)
            return count

        total_nodes = count_nodes(tree.root_node)
        logger.debug(f"Parsed {result.file_path}: {total_nodes} AST nodes")

    def _calculate_complexity(self, node: Node) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1

        decision_points = [
            "if_statement",
            "for_statement",
            "while_statement",
            "except_clause",
            "with_statement",
            "assert_statement",
            "conditional_expression",
        ]

        def walk(node: Node):
            nonlocal complexity
            if node.type in decision_points:
                complexity += 1
            for child in node.children:
                walk(child)

        walk(node)
        return complexity

    def get_function_at_line(self, result: ParsedFile, line: int) -> Optional[FunctionInfo]:
        """Get function information at a specific line"""
        for func in result.functions:
            if func.start_line <= line <= func.end_line:
                return func
        return None

    def get_class_at_line(self, result: ParsedFile, line: int) -> Optional[ClassInfo]:
        """Get class information at a specific line"""
        for cls in result.classes:
            if cls.start_line <= line <= cls.end_line:
                return cls
        return None


# Global parser instance
_parser: Optional[ASTParser] = None


def get_parser() -> ASTParser:
    """Get or create global parser instance"""
    global _parser
    if _parser is None:
        _parser = ASTParser()
    return _parser
