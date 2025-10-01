"""
Text parser for processing uploaded files and extracting TTS samples
"""
import re
import io
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd
import json
from pathlib import Path

from dataset import TestSample

@dataclass
class ParsedText:
    """Represents parsed text with metadata"""
    content: str
    source_file: str
    line_number: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = None

class TextParser:
    """Parses various text file formats and extracts TTS samples"""
    
    def __init__(self):
        self.supported_formats = ['.txt', '.csv', '.json', '.md', '.py', '.js', '.html']
        self.sentence_endings = ['.', '!', '?', '...']
        
    def parse_uploaded_file(self, file_content: Union[str, bytes], filename: str) -> List[ParsedText]:
        """Parse uploaded file and extract text content"""
        
        # Convert bytes to string if needed
        if isinstance(file_content, bytes):
            try:
                file_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    file_content = file_content.decode('latin-1')
                except UnicodeDecodeError:
                    raise ValueError("Unable to decode file. Please ensure it's a text file.")
        
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == '.txt':
            return self._parse_text_file(file_content, filename)
        elif file_ext == '.csv':
            return self._parse_csv_file(file_content, filename)
        elif file_ext == '.json':
            return self._parse_json_file(file_content, filename)
        elif file_ext == '.md':
            return self._parse_markdown_file(file_content, filename)
        elif file_ext in ['.py', '.js']:
            return self._parse_code_file(file_content, filename)
        elif file_ext == '.html':
            return self._parse_html_file(file_content, filename)
        else:
            # Default to text parsing
            return self._parse_text_file(file_content, filename)
    
    def _parse_text_file(self, content: str, filename: str) -> List[ParsedText]:
        """Parse plain text file"""
        parsed_texts = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and len(line) > 10:  # Skip very short lines
                parsed_texts.append(ParsedText(
                    content=line,
                    source_file=filename,
                    line_number=i,
                    metadata={'type': 'text_line'}
                ))
        
        return parsed_texts
    
    def _parse_csv_file(self, content: str, filename: str) -> List[ParsedText]:
        """Parse CSV file - look for text columns"""
        parsed_texts = []
        
        try:
            # Try to read as CSV
            df = pd.read_csv(io.StringIO(content))
            
            # Look for text columns (columns with string data and reasonable length)
            text_columns = []
            for col in df.columns:
                if df[col].dtype == 'object':  # String columns
                    avg_length = df[col].astype(str).str.len().mean()
                    if avg_length > 20:  # Reasonable text length
                        text_columns.append(col)
            
            if not text_columns:
                # If no obvious text columns, use all string columns
                text_columns = [col for col in df.columns if df[col].dtype == 'object']
            
            # Extract text from identified columns
            for idx, row in df.iterrows():
                for col in text_columns:
                    text = str(row[col]).strip()
                    if text and len(text) > 10 and text != 'nan':
                        parsed_texts.append(ParsedText(
                            content=text,
                            source_file=filename,
                            line_number=idx + 2,  # +2 for header and 0-indexing
                            section=col,
                            metadata={'type': 'csv_cell', 'column': col}
                        ))
        
        except Exception as e:
            # If CSV parsing fails, treat as plain text
            return self._parse_text_file(content, filename)
        
        return parsed_texts
    
    def _parse_json_file(self, content: str, filename: str) -> List[ParsedText]:
        """Parse JSON file - extract string values"""
        parsed_texts = []
        
        try:
            data = json.loads(content)
            
            def extract_strings(obj, path=""):
                """Recursively extract string values from JSON"""
                if isinstance(obj, str) and len(obj) > 10:
                    parsed_texts.append(ParsedText(
                        content=obj,
                        source_file=filename,
                        section=path,
                        metadata={'type': 'json_string', 'path': path}
                    ))
                elif isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        extract_strings(value, new_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        new_path = f"{path}[{i}]" if path else f"[{i}]"
                        extract_strings(item, new_path)
            
            extract_strings(data)
        
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as plain text
            return self._parse_text_file(content, filename)
        
        return parsed_texts
    
    def _parse_markdown_file(self, content: str, filename: str) -> List[ParsedText]:
        """Parse Markdown file - extract text content"""
        parsed_texts = []
        lines = content.split('\n')
        current_section = None
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Track sections (headers)
            if line.startswith('#'):
                current_section = line.lstrip('#').strip()
                continue
            
            # Skip code blocks
            if line.startswith('```') or line.startswith('    '):
                continue
            
            # Skip links and images
            if line.startswith('[') or line.startswith('!['):
                continue
            
            # Extract meaningful text
            if line and len(line) > 10:
                # Remove markdown formatting
                clean_line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Bold
                clean_line = re.sub(r'\*(.*?)\*', r'\1', clean_line)  # Italic
                clean_line = re.sub(r'`(.*?)`', r'\1', clean_line)  # Code
                clean_line = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_line)  # Links
                
                if clean_line.strip():
                    parsed_texts.append(ParsedText(
                        content=clean_line.strip(),
                        source_file=filename,
                        line_number=i,
                        section=current_section,
                        metadata={'type': 'markdown_text', 'section': current_section}
                    ))
        
        return parsed_texts
    
    def _parse_code_file(self, content: str, filename: str) -> List[ParsedText]:
        """Parse code file - extract comments and strings"""
        parsed_texts = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Extract comments
            comment_patterns = [
                r'#\s*(.*)',      # Python comments
                r'//\s*(.*)',     # JavaScript/C++ comments
                r'/\*\s*(.*?)\s*\*/',  # Block comments
            ]
            
            for pattern in comment_patterns:
                match = re.search(pattern, line)
                if match:
                    comment_text = match.group(1).strip()
                    if len(comment_text) > 10:
                        parsed_texts.append(ParsedText(
                            content=comment_text,
                            source_file=filename,
                            line_number=i,
                            metadata={'type': 'code_comment'}
                        ))
            
            # Extract string literals
            string_patterns = [
                r'"([^"]{10,})"',    # Double quoted strings
                r"'([^']{10,})'",    # Single quoted strings
                r'`([^`]{10,})`',    # Template literals
            ]
            
            for pattern in string_patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    parsed_texts.append(ParsedText(
                        content=match,
                        source_file=filename,
                        line_number=i,
                        metadata={'type': 'code_string'}
                    ))
        
        return parsed_texts
    
    def _parse_html_file(self, content: str, filename: str) -> List[ParsedText]:
        """Parse HTML file - extract text content"""
        parsed_texts = []
        
        # Remove script and style tags
        content = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract text from common tags
        text_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span', 'li', 'td', 'th']
        
        for tag in text_tags:
            pattern = f'<{tag}[^>]*>(.*?)</{tag}>'
            matches = re.findall(pattern, content, flags=re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                # Remove HTML tags from content
                clean_text = re.sub(r'<[^>]+>', '', match)
                clean_text = clean_text.strip()
                
                if len(clean_text) > 10:
                    parsed_texts.append(ParsedText(
                        content=clean_text,
                        source_file=filename,
                        metadata={'type': 'html_text', 'tag': tag}
                    ))
        
        return parsed_texts
    
    def create_test_samples_from_parsed(
        self, 
        parsed_texts: List[ParsedText], 
        auto_categorize: bool = True,
        max_samples: Optional[int] = None
    ) -> List[TestSample]:
        """Convert parsed texts to TestSample objects"""
        
        test_samples = []
        
        for i, parsed_text in enumerate(parsed_texts):
            if max_samples and len(test_samples) >= max_samples:
                break
            
            text = parsed_text.content.strip()
            if not text or len(text) < 10:
                continue
            
            # Calculate word count
            word_count = len(text.split())
            
            # Determine length category
            if word_count <= 30:
                length_category = "short"
            elif word_count <= 80:
                length_category = "medium"
            elif word_count <= 150:
                length_category = "long"
            else:
                length_category = "very_long"
            
            # Auto-categorize content if requested
            if auto_categorize:
                category = self._auto_categorize_text(text)
            else:
                category = "uploaded"
            
            # Calculate complexity score
            complexity_score = self._calculate_complexity_score(text)
            
            # Create test sample
            sample = TestSample(
                id=f"upload_{i+1:03d}",
                text=text,
                word_count=word_count,
                category=category,
                length_category=length_category,
                complexity_score=complexity_score
            )
            
            test_samples.append(sample)
        
        return test_samples
    
    def _auto_categorize_text(self, text: str) -> str:
        """Automatically categorize text based on content"""
        
        text_lower = text.lower()
        
        # Technical keywords
        technical_keywords = [
            'algorithm', 'function', 'variable', 'database', 'api', 'server',
            'code', 'programming', 'software', 'system', 'network', 'data',
            'implementation', 'framework', 'library', 'method', 'class'
        ]
        
        # News keywords
        news_keywords = [
            'reported', 'announced', 'according to', 'breaking', 'update',
            'government', 'official', 'statement', 'press', 'media', 'news',
            'today', 'yesterday', 'recently', 'sources say'
        ]
        
        # Literature keywords
        literature_keywords = [
            'character', 'story', 'novel', 'chapter', 'narrative', 'plot',
            'once upon', 'he said', 'she whispered', 'thought to himself',
            'in the distance', 'suddenly', 'meanwhile'
        ]
        
        # Conversation keywords
        conversation_keywords = [
            'hello', 'hi there', 'how are you', 'what do you think',
            'i think', 'you know', 'by the way', 'speaking of',
            'anyway', 'so basically', 'i mean', 'you see'
        ]
        
        # Count keyword matches
        categories = {
            'technical': sum(1 for kw in technical_keywords if kw in text_lower),
            'news': sum(1 for kw in news_keywords if kw in text_lower),
            'literature': sum(1 for kw in literature_keywords if kw in text_lower),
            'conversation': sum(1 for kw in conversation_keywords if kw in text_lower)
        }
        
        # Return category with highest score, default to 'uploaded'
        if max(categories.values()) > 0:
            return max(categories, key=categories.get)
        else:
            return 'uploaded'
    
    def _calculate_complexity_score(self, text: str) -> float:
        """Calculate text complexity score"""
        words = text.split()
        sentences = text.split('.')
        
        # Average word length
        avg_word_length = sum(len(word.strip('.,!?;:')) for word in words) / len(words)
        
        # Average sentence length
        avg_sentence_length = len(words) / max(len(sentences), 1)
        
        # Punctuation density
        punctuation_count = sum(1 for char in text if char in '.,!?;:()[]{}')
        punctuation_density = punctuation_count / len(text)
        
        # Complexity score (0-1 scale)
        complexity = (
            (avg_word_length - 3) / 10 * 0.4 +
            (avg_sentence_length - 10) / 20 * 0.4 +
            punctuation_density * 0.2
        )
        
        return max(0, min(1, complexity))
    
    def get_file_preview(self, parsed_texts: List[ParsedText], max_items: int = 10) -> Dict[str, Any]:
        """Get a preview of parsed file content"""
        
        preview = {
            'total_items': len(parsed_texts),
            'file_types': list(set(pt.metadata.get('type', 'unknown') for pt in parsed_texts)),
            'sample_texts': [],
            'word_count_stats': {
                'min': 0,
                'max': 0,
                'avg': 0
            }
        }
        
        if parsed_texts:
            # Sample texts
            for pt in parsed_texts[:max_items]:
                preview['sample_texts'].append({
                    'text': pt.content[:100] + '...' if len(pt.content) > 100 else pt.content,
                    'word_count': len(pt.content.split()),
                    'source': pt.section or f"Line {pt.line_number}" if pt.line_number else "Unknown"
                })
            
            # Word count statistics
            word_counts = [len(pt.content.split()) for pt in parsed_texts]
            preview['word_count_stats'] = {
                'min': min(word_counts),
                'max': max(word_counts),
                'avg': sum(word_counts) / len(word_counts)
            }
        
        return preview
