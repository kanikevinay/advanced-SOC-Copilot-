"""Custom text log parser for SOC Copilot.

Parses custom key-value text logs in format:
    TIMESTAMP EVENT_TYPE field1=value1 field2=value2 ...
    
Example:
    2026-03-24 10:00:10 UserLogin failed user=admin ip=45.33.32.1
    2026-03-24 10:05:00 DataTransfer size=3000MB src_ip=10.0.0.2 dst_ip=8.8.8.8
"""

from pathlib import Path
from typing import Any
import re
from datetime import datetime

from soc_copilot.core.base import BaseParser, ParsedRecord, ParseError


class TextLogParser(BaseParser):
    """Parser for custom text-based key-value log format.
    
    Features:
    - Extracts timestamp (first field)
    - Extracts event type (second field)
    - Parses key-value pairs (field=value)
    - Handles quoted values with spaces
    - Infers types for values (int, float, bool, str)
    """
    
    @property
    def supported_extensions(self) -> list[str]:
        """Support .log and .txt extensions."""
        return [".log", ".txt"]
    
    @property
    def format_name(self) -> str:
        """Format name."""
        return "Text"
    
    def parse(self, filepath: Path) -> list[ParsedRecord]:
        """Parse a text log file.
        
        Args:
            filepath: Path to the log file
            
        Returns:
            List of parsed records
            
        Raises:
            ParseError: If file cannot be parsed
        """
        records = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.rstrip('\n\r')
                    if not line.strip() or line.startswith('#'):
                        continue
                    
                    try:
                        record = self.parse_line(line)
                        if record:
                            record.source_file = str(filepath)
                            record.source_format = self.format_name
                            records.append(record)
                    except Exception as e:
                        # Log warning but continue processing
                        print(f"  Warning: Line {line_num}: {e}")
                        continue
        
        except Exception as e:
            raise ParseError(f"Failed to parse text log file {filepath}: {e}")
        
        return records
    
    def parse_line(self, line: str) -> ParsedRecord | None:
        """Parse a single line of text log.
        
        Format: TIMESTAMP EVENT_TYPE field1=value1 field2=value2 ...
        
        Args:
            line: Single line from log file
            
        Returns:
            ParsedRecord or None if line cannot be parsed
        """
        line = line.strip()
        
        if not line:
            return None
        
        # Split the line into components
        parts = line.split()
        
        if len(parts) < 2:
            raise ValueError(f"Invalid format, expected at least timestamp and event type: {line}")
        
        # First part: timestamp (can be date or datetime)
        timestamp_str = parts[0]
        
        # Second part: timestamp completion (time if not included in first part)
        event_type_idx = 1
        if self._looks_like_time(parts[1]):
            timestamp_str += " " + parts[1]
            event_type_idx = 2
        
        # Normalize timestamp
        try:
            timestamp = self._parse_timestamp(timestamp_str)
        except Exception as e:
            raise ValueError(f"Cannot parse timestamp '{timestamp_str}': {e}")
        
        if event_type_idx >= len(parts):
            raise ValueError(f"No event type found after timestamp: {line}")
        
        # Third part: event type
        event_type = parts[event_type_idx]
        
        # Rest: key-value pairs
        raw_data = {
            'event_type': event_type,
            'timestamp': timestamp,
        }
        
        # Parse key-value pairs
        remaining = " ".join(parts[event_type_idx + 1:])
        kv_pairs = self._parse_key_value_pairs(remaining)
        raw_data.update(kv_pairs)
        
        return ParsedRecord(
            timestamp=timestamp,
            raw=raw_data,
        )
    
    def _looks_like_time(self, s: str) -> bool:
        """Check if string looks like a time (HH:MM:SS or HH:MM)."""
        return bool(re.match(r'^\d{2}:\d{2}:\d{2}$', s)) or bool(re.match(r'^\d{2}:\d{2}$', s))
    
    def _parse_timestamp(self, timestamp_str: str) -> str:
        """Parse and normalize timestamp string.
        
        Supports formats:
        - 2026-03-24
        - 2026-03-24 10:00:10
        - 2026-03-24 10:00:10.123
        - 10:00:10 (uses today's date)
        
        Returns:
            ISO format timestamp string
        """
        timestamp_str = timestamp_str.strip()
        
        # Try various formats
        formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%H:%M:%S',
            '%H:%M',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        
        raise ValueError(f"Cannot parse timestamp: {timestamp_str}")
    
    def _parse_key_value_pairs(self, s: str) -> dict[str, Any]:
        """Parse key-value pairs from a string.
        
        Supports:
        - Simple: key=value key2=value2
        - Quoted: key="value with spaces"
        - Type inference: key=123 (int), key=45.5 (float), key=true (bool)
        
        Args:
            s: String containing key=value pairs
            
        Returns:
            Dictionary of key-value pairs
        """
        pairs = {}
        
        # Pattern for key=value (handles quoted values)
        # Matches: word="quoted value" or word=unquoted_value
        pattern = r'(\w+)=(?:"([^"]*)"|(\S+))'
        
        matches = re.finditer(pattern, s)
        for match in matches:
            key = match.group(1)
            value = match.group(2) or match.group(3)  # Group 2 for quoted, Group 3 for unquoted
            
            # Try to infer type
            pairs[key] = self._infer_type(value)
        
        return pairs
    
    def _infer_type(self, value: str) -> Any:
        """Infer and convert value to appropriate Python type.
        
        Args:
            value: String value
            
        Returns:
            Converted value (int, float, bool, or str)
        """
        value = value.strip()
        
        if not value:
            return None
        
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        # String (default)
        return value
