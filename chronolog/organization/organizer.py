import os
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
import mimetypes


@dataclass
class FileCategory:
    name: str
    extensions: Set[str]
    patterns: List[str]
    description: str


@dataclass
class OrganizationSuggestion:
    file_path: Path
    current_location: Path
    suggested_location: Path
    reason: str
    category: str


class FileOrganizer:
    """Smart file organization and categorization for ChronoLog repositories."""
    
    # Built-in project templates and categories
    PROJECT_TEMPLATES = {
        'python': {
            'markers': ['setup.py', 'pyproject.toml', 'requirements.txt'],
            'structure': {
                'src': ['*.py'],
                'tests': ['test_*.py', '*_test.py'],
                'docs': ['*.md', '*.rst'],
                'scripts': ['*.py', '*.sh'],
                'config': ['*.ini', '*.cfg', '*.yaml', '*.toml']
            }
        },
        'javascript': {
            'markers': ['package.json', 'node_modules'],
            'structure': {
                'src': ['*.js', '*.jsx', '*.ts', '*.tsx'],
                'tests': ['*.test.js', '*.spec.js', '*.test.ts', '*.spec.ts'],
                'dist': ['*.min.js', '*.bundle.js'],
                'docs': ['*.md'],
                'config': ['*.json', '*.yml', '*.yaml']
            }
        },
        'java': {
            'markers': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'structure': {
                'src/main/java': ['*.java'],
                'src/test/java': ['*.java'],
                'src/main/resources': ['*.properties', '*.xml', '*.yml'],
                'docs': ['*.md'],
                'lib': ['*.jar']
            }
        },
        'web': {
            'markers': ['index.html', 'index.htm'],
            'structure': {
                'js': ['*.js', '*.jsx', '*.ts', '*.tsx'],
                'css': ['*.css', '*.scss', '*.sass', '*.less'],
                'images': ['*.jpg', '*.png', '*.gif', '*.svg', '*.webp'],
                'fonts': ['*.ttf', '*.otf', '*.woff', '*.woff2'],
                'assets': ['*']
            }
        }
    }
    
    FILE_CATEGORIES = {
        'source_code': FileCategory(
            name='Source Code',
            extensions={'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php'},
            patterns=['*.py', '*.js', '*.java', '*.cpp'],
            description='Programming language source files'
        ),
        'documentation': FileCategory(
            name='Documentation',
            extensions={'.md', '.rst', '.txt', '.pdf', '.doc', '.docx'},
            patterns=['README*', 'CHANGELOG*', 'LICENSE*', '*.md'],
            description='Documentation and text files'
        ),
        'configuration': FileCategory(
            name='Configuration',
            extensions={'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.env'},
            patterns=['.*rc', '.*config', '*.json', '*.yaml'],
            description='Configuration and settings files'
        ),
        'data': FileCategory(
            name='Data',
            extensions={'.csv', '.json', '.xml', '.sql', '.db', '.sqlite'},
            patterns=['*.csv', '*.json', 'data/*'],
            description='Data and database files'
        ),
        'media': FileCategory(
            name='Media',
            extensions={'.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', '.mp3', '.wav'},
            patterns=['*.jpg', '*.png', '*.svg'],
            description='Image, video, and audio files'
        ),
        'archives': FileCategory(
            name='Archives',
            extensions={'.zip', '.tar', '.gz', '.rar', '.7z'},
            patterns=['*.zip', '*.tar.gz'],
            description='Compressed archive files'
        )
    }
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.file_stats = defaultdict(int)
        self.category_stats = defaultdict(int)
        
    def analyze_repository(self) -> Dict[str, any]:
        """Analyze repository structure and file organization."""
        analysis = {
            'project_type': self.detect_project_type(),
            'file_stats': {},
            'category_distribution': {},
            'organization_score': 0,
            'suggestions': []
        }
        
        # Scan all files
        all_files = []
        for root, dirs, files in os.walk(self.repo_path):
            # Skip .chronolog directory
            if '.chronolog' in root:
                continue
                
            for file in files:
                file_path = Path(root) / file
                all_files.append(file_path)
                
                # Update stats
                ext = file_path.suffix.lower()
                self.file_stats[ext] += 1
                
                category = self.categorize_file(file_path)
                self.category_stats[category] += 1
        
        analysis['file_stats'] = dict(self.file_stats)
        analysis['category_distribution'] = dict(self.category_stats)
        analysis['total_files'] = len(all_files)
        
        # Calculate organization score
        analysis['organization_score'] = self.calculate_organization_score(all_files)
        
        # Generate suggestions
        analysis['suggestions'] = self.generate_suggestions(all_files)
        
        return analysis
    
    def detect_project_type(self) -> Optional[str]:
        """Detect the type of project based on marker files."""
        for project_type, config in self.PROJECT_TEMPLATES.items():
            markers = config['markers']
            for marker in markers:
                if (self.repo_path / marker).exists():
                    return project_type
        return None
    
    def categorize_file(self, file_path: Path) -> str:
        """Categorize a file based on its extension and name."""
        ext = file_path.suffix.lower()
        name = file_path.name.lower()
        
        for category_name, category in self.FILE_CATEGORIES.items():
            if ext in category.extensions:
                return category_name
            
            # Check patterns
            for pattern in category.patterns:
                if self._matches_pattern(name, pattern):
                    return category_name
        
        return 'other'
    
    def calculate_organization_score(self, files: List[Path]) -> float:
        """Calculate a score representing how well organized the repository is."""
        if not files:
            return 100.0
        
        score = 100.0
        penalties = 0
        
        # Check for files in root that should be in subdirectories
        root_files = [f for f in files if f.parent == self.repo_path]
        for file in root_files:
            if file.suffix.lower() in ['.py', '.js', '.java', '.cpp']:
                penalties += 5  # Source files in root
            elif file.name not in ['README.md', 'LICENSE', 'setup.py', 'package.json']:
                penalties += 2  # Other files in root
        
        # Check for mixed file types in same directory
        dir_contents = defaultdict(set)
        for file in files:
            dir_contents[file.parent].add(self.categorize_file(file))
        
        for dir_path, categories in dir_contents.items():
            if len(categories) > 3:
                penalties += 3  # Too many different file types in one directory
        
        # Check for deeply nested structures
        for file in files:
            depth = len(file.relative_to(self.repo_path).parts)
            if depth > 5:
                penalties += 1  # Too deeply nested
        
        score = max(0, score - penalties)
        return score
    
    def generate_suggestions(self, files: List[Path]) -> List[OrganizationSuggestion]:
        """Generate organization suggestions for the repository."""
        suggestions = []
        project_type = self.detect_project_type()
        
        if project_type and project_type in self.PROJECT_TEMPLATES:
            template = self.PROJECT_TEMPLATES[project_type]
            structure = template['structure']
            
            for file in files:
                category = self.categorize_file(file)
                ext = file.suffix.lower()
                
                # Find appropriate directory from template
                for dir_pattern, file_patterns in structure.items():
                    for pattern in file_patterns:
                        if self._matches_pattern(file.name, pattern):
                            suggested_dir = self.repo_path / dir_pattern
                            if file.parent != suggested_dir:
                                suggestions.append(OrganizationSuggestion(
                                    file_path=file,
                                    current_location=file.parent,
                                    suggested_location=suggested_dir,
                                    reason=f"Based on {project_type} project structure",
                                    category=category
                                ))
                            break
        
        # General suggestions
        for file in files:
            if file.parent == self.repo_path:
                category = self.categorize_file(file)
                if category in ['source_code', 'data', 'media']:
                    suggested_dir = self.repo_path / category.replace('_', '-')
                    suggestions.append(OrganizationSuggestion(
                        file_path=file,
                        current_location=file.parent,
                        suggested_location=suggested_dir,
                        reason=f"Move {category} files to dedicated directory",
                        category=category
                    ))
        
        return suggestions[:20]  # Limit to top 20 suggestions
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Simple pattern matching (not full glob)."""
        if pattern.startswith('*'):
            return filename.endswith(pattern[1:])
        elif pattern.endswith('*'):
            return filename.startswith(pattern[:-1])
        else:
            return filename == pattern
    
    def apply_suggestions(self, suggestions: List[OrganizationSuggestion], dry_run: bool = True) -> List[Tuple[Path, Path]]:
        """Apply organization suggestions by moving files."""
        moves = []
        
        for suggestion in suggestions:
            src = suggestion.file_path
            dst_dir = suggestion.suggested_location
            dst = dst_dir / src.name
            
            if dry_run:
                moves.append((src, dst))
            else:
                # Create directory if needed
                dst_dir.mkdir(parents=True, exist_ok=True)
                
                # Move file
                src.rename(dst)
                moves.append((src, dst))
        
        return moves
    
    def export_organization_report(self, analysis: Dict[str, any], output_path: Path):
        """Export organization analysis report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'repository': str(self.repo_path),
            'analysis': analysis,
            'recommendations': []
        }
        
        # Add recommendations based on score
        if analysis['organization_score'] < 50:
            report['recommendations'].append(
                "Consider reorganizing your repository structure. "
                "Many files could be better organized into subdirectories."
            )
        
        if analysis['project_type']:
            report['recommendations'].append(
                f"Detected {analysis['project_type']} project. "
                f"Consider following standard {analysis['project_type']} project structure."
            )
        
        # Write report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)