import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"


@dataclass
class CodeElement:
    type: str
    name: str
    start_line: int
    end_line: int
    signature: Optional[str] = None
    body_hash: Optional[str] = None


@dataclass
class SemanticChange:
    change_type: ChangeType
    element: CodeElement
    old_element: Optional[CodeElement] = None
    details: Optional[str] = None


class SemanticDiffer:
    SUPPORTED_LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rs': 'rust'
    }
    
    def __init__(self):
        self.parsers = {
            'python': self._parse_python,
            'javascript': self._parse_javascript,
            'java': self._parse_java,
        }
    
    def detect_language(self, file_path: str) -> Optional[str]:
        ext = Path(file_path).suffix.lower()
        return self.SUPPORTED_LANGUAGES.get(ext)
    
    def diff_semantic(self, content1: str, content2: str, language: str) -> List[SemanticChange]:
        if language not in self.parsers:
            return self._fallback_diff(content1, content2)
        
        elements1 = self.parsers[language](content1)
        elements2 = self.parsers[language](content2)
        
        changes = []
        
        elements1_dict = {e.name: e for e in elements1}
        elements2_dict = {e.name: e for e in elements2}
        
        for name, elem1 in elements1_dict.items():
            if name not in elements2_dict:
                changes.append(SemanticChange(ChangeType.REMOVED, elem1))
            else:
                elem2 = elements2_dict[name]
                if self._has_changed(elem1, elem2):
                    changes.append(SemanticChange(
                        ChangeType.MODIFIED,
                        elem2,
                        old_element=elem1,
                        details=self._get_change_details(elem1, elem2)
                    ))
        
        for name, elem2 in elements2_dict.items():
            if name not in elements1_dict:
                if possible_rename := self._find_possible_rename(elem2, elements1):
                    changes.append(SemanticChange(
                        ChangeType.RENAMED,
                        elem2,
                        old_element=possible_rename,
                        details=f"Renamed from {possible_rename.name}"
                    ))
                else:
                    changes.append(SemanticChange(ChangeType.ADDED, elem2))
        
        return sorted(changes, key=lambda c: c.element.start_line)
    
    def _parse_python(self, content: str) -> List[CodeElement]:
        elements = []
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    elements.append(CodeElement(
                        type="function",
                        name=node.name,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        signature=self._get_python_function_signature(node)
                    ))
                elif isinstance(node, ast.ClassDef):
                    elements.append(CodeElement(
                        type="class",
                        name=node.name,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        signature=self._get_python_class_signature(node)
                    ))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        elements.append(CodeElement(
                            type="import",
                            name=alias.name,
                            start_line=node.lineno,
                            end_line=node.lineno
                        ))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        elements.append(CodeElement(
                            type="import",
                            name=f"{module}.{alias.name}",
                            start_line=node.lineno,
                            end_line=node.lineno
                        ))
        except:
            pass
        
        return elements
    
    def _parse_javascript(self, content: str) -> List[CodeElement]:
        elements = []
        
        function_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>)'
        class_pattern = r'class\s+(\w+)'
        import_pattern = r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            if match := re.search(function_pattern, line):
                name = match.group(1) or match.group(2)
                elements.append(CodeElement(
                    type="function",
                    name=name,
                    start_line=i,
                    end_line=i
                ))
            
            if match := re.search(class_pattern, line):
                elements.append(CodeElement(
                    type="class",
                    name=match.group(1),
                    start_line=i,
                    end_line=i
                ))
            
            if match := re.search(import_pattern, line):
                elements.append(CodeElement(
                    type="import",
                    name=match.group(1),
                    start_line=i,
                    end_line=i
                ))
        
        return elements
    
    def _parse_java(self, content: str) -> List[CodeElement]:
        elements = []
        
        class_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*class\s+(\w+)'
        method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*{'
        import_pattern = r'import\s+([\w.]+);'
        
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            if match := re.search(class_pattern, line):
                elements.append(CodeElement(
                    type="class",
                    name=match.group(1),
                    start_line=i,
                    end_line=i
                ))
            
            if match := re.search(method_pattern, line):
                if match.group(1) not in ['if', 'while', 'for', 'switch', 'catch']:
                    elements.append(CodeElement(
                        type="method",
                        name=match.group(1),
                        start_line=i,
                        end_line=i
                    ))
            
            if match := re.search(import_pattern, line):
                elements.append(CodeElement(
                    type="import",
                    name=match.group(1),
                    start_line=i,
                    end_line=i
                ))
        
        return elements
    
    def _get_python_function_signature(self, node: ast.FunctionDef) -> str:
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        return f"({', '.join(args)})"
    
    def _get_python_class_signature(self, node: ast.ClassDef) -> str:
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
        return f"({', '.join(bases)})" if bases else ""
    
    def _has_changed(self, elem1: CodeElement, elem2: CodeElement) -> bool:
        if elem1.signature != elem2.signature:
            return True
        
        if elem1.type in ['function', 'method', 'class']:
            return elem1.end_line - elem1.start_line != elem2.end_line - elem2.start_line
        
        return False
    
    def _get_change_details(self, elem1: CodeElement, elem2: CodeElement) -> str:
        details = []
        
        if elem1.signature != elem2.signature:
            details.append(f"Signature changed from {elem1.signature} to {elem2.signature}")
        
        size_change = (elem2.end_line - elem2.start_line) - (elem1.end_line - elem1.start_line)
        if size_change > 0:
            details.append(f"Body grew by {size_change} lines")
        elif size_change < 0:
            details.append(f"Body shrank by {-size_change} lines")
        
        return "; ".join(details)
    
    def _find_possible_rename(self, elem: CodeElement, old_elements: List[CodeElement]) -> Optional[CodeElement]:
        candidates = [
            e for e in old_elements
            if e.type == elem.type and e.signature == elem.signature
        ]
        
        if len(candidates) == 1:
            return candidates[0]
        
        return None
    
    def _fallback_diff(self, content1: str, content2: str) -> List[SemanticChange]:
        return []
    
    def format_semantic_diff(self, changes: List[SemanticChange]) -> str:
        output = []
        
        for change in changes:
            elem = change.element
            
            if change.change_type == ChangeType.ADDED:
                output.append(f"+ {elem.type} {elem.name} (line {elem.start_line})")
            elif change.change_type == ChangeType.REMOVED:
                output.append(f"- {elem.type} {elem.name} (line {elem.start_line})")
            elif change.change_type == ChangeType.MODIFIED:
                output.append(f"~ {elem.type} {elem.name} (line {elem.start_line})")
                if change.details:
                    output.append(f"  {change.details}")
            elif change.change_type == ChangeType.RENAMED:
                output.append(f"R {elem.type} {change.old_element.name} -> {elem.name}")
        
        return "\n".join(output)