import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DiffType(Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"


@dataclass
class DiffWord:
    type: DiffType
    text: str
    line_number: Optional[int] = None
    
    def to_ansi(self) -> str:
        if self.type == DiffType.INSERT:
            return f"\033[32m{self.text}\033[0m"
        elif self.type == DiffType.DELETE:
            return f"\033[31m{self.text}\033[0m"
        else:
            return self.text


class WordDiffer:
    def __init__(self, word_delimiter: str = r'\s+|(?=[^\w])|(?<=[^\w])'):
        self.word_delimiter = word_delimiter
    
    def tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        
        tokens = re.split(f'({self.word_delimiter})', text)
        return [token for token in tokens if token]
    
    def diff_words(self, text1: str, text2: str) -> List[DiffWord]:
        words1 = self.tokenize(text1)
        words2 = self.tokenize(text2)
        
        m, n = len(words1), len(words2)
        
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if words1[i-1] == words2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        result = []
        i, j = m, n
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and words1[i-1] == words2[j-1]:
                result.append(DiffWord(DiffType.EQUAL, words1[i-1]))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
                result.append(DiffWord(DiffType.INSERT, words2[j-1]))
                j -= 1
            else:
                result.append(DiffWord(DiffType.DELETE, words1[i-1]))
                i -= 1
        
        result.reverse()
        return result
    
    def diff_lines_with_words(self, text1: str, text2: str) -> List[Tuple[int, List[DiffWord]]]:
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        result = []
        line_num = 1
        
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, lines1, lines2)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for i in range(i1, i2):
                    result.append((line_num, [DiffWord(DiffType.EQUAL, lines1[i])]))
                    line_num += 1
            elif tag == 'delete':
                for i in range(i1, i2):
                    word_diff = self.diff_words(lines1[i], "")
                    result.append((line_num, word_diff))
                    line_num += 1
            elif tag == 'insert':
                for j in range(j1, j2):
                    word_diff = self.diff_words("", lines2[j])
                    result.append((line_num, word_diff))
                    line_num += 1
            elif tag == 'replace':
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    word_diff = self.diff_words(lines1[i], lines2[j])
                    result.append((line_num, word_diff))
                    line_num += 1
                
                if i2 - i1 < j2 - j1:
                    for j in range(j1 + (i2 - i1), j2):
                        word_diff = self.diff_words("", lines2[j])
                        result.append((line_num, word_diff))
                        line_num += 1
                elif i2 - i1 > j2 - j1:
                    for i in range(i1 + (j2 - j1), i2):
                        word_diff = self.diff_words(lines1[i], "")
                        result.append((line_num, word_diff))
                        line_num += 1
        
        return result
    
    def format_word_diff(self, diff: List[DiffWord], use_color: bool = True) -> str:
        result = []
        for word in diff:
            if use_color:
                result.append(word.to_ansi())
            else:
                if word.type == DiffType.INSERT:
                    result.append(f"+{word.text}")
                elif word.type == DiffType.DELETE:
                    result.append(f"-{word.text}")
                else:
                    result.append(word.text)
        return ''.join(result)