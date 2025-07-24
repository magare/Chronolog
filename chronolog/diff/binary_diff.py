import hashlib
import mimetypes
import struct
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class BinaryDiffResult:
    is_identical: bool
    size1: int
    size2: int
    hash1: str
    hash2: str
    mime_type: Optional[str] = None
    hex_diff: Optional[List[Tuple[int, bytes, bytes]]] = None
    similarity_percent: Optional[float] = None


class BinaryDiffer:
    MAX_HEX_DIFF_SIZE = 1024 * 10
    
    def __init__(self):
        self.image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico'}
        self.text_extensions = {'.txt', '.md', '.rst', '.log', '.csv', '.json', '.xml', '.yaml', '.yml'}
    
    def diff_binary(self, content1: bytes, content2: bytes, file_path: Optional[str] = None) -> BinaryDiffResult:
        size1 = len(content1)
        size2 = len(content2)
        
        hash1 = hashlib.sha256(content1).hexdigest()
        hash2 = hashlib.sha256(content2).hexdigest()
        
        is_identical = hash1 == hash2
        
        mime_type = None
        if file_path:
            mime_type, _ = mimetypes.guess_type(file_path)
        
        result = BinaryDiffResult(
            is_identical=is_identical,
            size1=size1,
            size2=size2,
            hash1=hash1[:16],
            hash2=hash2[:16],
            mime_type=mime_type
        )
        
        if not is_identical:
            if size1 <= self.MAX_HEX_DIFF_SIZE and size2 <= self.MAX_HEX_DIFF_SIZE:
                result.hex_diff = self._compute_hex_diff(content1, content2)
            
            result.similarity_percent = self._compute_similarity(content1, content2)
        
        return result
    
    def _compute_hex_diff(self, content1: bytes, content2: bytes) -> List[Tuple[int, bytes, bytes]]:
        diffs = []
        chunk_size = 16
        
        max_len = max(len(content1), len(content2))
        
        for offset in range(0, max_len, chunk_size):
            chunk1 = content1[offset:offset + chunk_size] if offset < len(content1) else b''
            chunk2 = content2[offset:offset + chunk_size] if offset < len(content2) else b''
            
            if chunk1 != chunk2:
                diffs.append((offset, chunk1, chunk2))
        
        return diffs[:20]
    
    def _compute_similarity(self, content1: bytes, content2: bytes) -> float:
        if len(content1) == 0 and len(content2) == 0:
            return 100.0
        
        if len(content1) == 0 or len(content2) == 0:
            return 0.0
        
        sample_size = min(1024, len(content1), len(content2))
        
        matches = 0
        for i in range(sample_size):
            if content1[i] == content2[i]:
                matches += 1
        
        base_similarity = (matches / sample_size) * 100
        
        size_ratio = min(len(content1), len(content2)) / max(len(content1), len(content2))
        
        return base_similarity * size_ratio
    
    def format_binary_diff(self, diff: BinaryDiffResult) -> str:
        lines = []
        
        if diff.is_identical:
            lines.append("Binary files are identical")
        else:
            lines.append("Binary files differ")
            lines.append(f"Size: {diff.size1} bytes -> {diff.size2} bytes ({diff.size2 - diff.size1:+d})")
            lines.append(f"SHA256: {diff.hash1}... -> {diff.hash2}...")
            
            if diff.mime_type:
                lines.append(f"Type: {diff.mime_type}")
            
            if diff.similarity_percent is not None:
                lines.append(f"Similarity: {diff.similarity_percent:.1f}%")
            
            if diff.hex_diff:
                lines.append("\nFirst differences (hex):")
                for offset, chunk1, chunk2 in diff.hex_diff[:5]:
                    hex1 = chunk1.hex()
                    hex2 = chunk2.hex()
                    lines.append(f"  @{offset:04x}: {hex1:<32} -> {hex2:<32}")
        
        return "\n".join(lines)
    
    def get_image_dimensions(self, content: bytes, file_ext: str) -> Optional[Tuple[int, int]]:
        if file_ext == '.png':
            if len(content) >= 24 and content[:8] == b'\x89PNG\r\n\x1a\n':
                width = struct.unpack('>I', content[16:20])[0]
                height = struct.unpack('>I', content[20:24])[0]
                return (width, height)
        
        elif file_ext in ['.jpg', '.jpeg']:
            if len(content) >= 2 and content[:2] == b'\xff\xd8':
                i = 2
                while i < len(content) - 1:
                    if content[i] == 0xff:
                        marker = content[i+1]
                        if marker in [0xc0, 0xc1, 0xc2]:
                            if i + 9 < len(content):
                                height = struct.unpack('>H', content[i+5:i+7])[0]
                                width = struct.unpack('>H', content[i+7:i+9])[0]
                                return (width, height)
                        
                        if i + 3 < len(content):
                            length = struct.unpack('>H', content[i+2:i+4])[0]
                            i += length + 2
                        else:
                            break
                    else:
                        i += 1
        
        return None
    
    def format_image_diff(self, diff: BinaryDiffResult, file_path: str) -> str:
        lines = [self.format_binary_diff(diff)]
        
        file_ext = Path(file_path).suffix.lower()
        if file_ext in self.image_extensions:
            lines.append("\nImage analysis:")
            lines.append("  (Consider using an image diff tool for visual comparison)")
        
        return "\n".join(lines)