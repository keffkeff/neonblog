from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class Post:
    id: int
    title: str
    category: str
    color: str
    size: str
    excerpt: str
    content: str  # HTML content (rendered)
    media_files: str  # Stored as comma-separated string
    created_at: datetime
    read_time: str
    markdown_content: str = ""  # Original markdown (for editing)
    
    def get_media_list(self) -> List[str]:
        """Convert comma-separated media string to list"""
        if not self.media_files:
            return []
        return [f.strip() for f in self.media_files.split(',') if f.strip()]
    
    def formatted_date(self) -> str:
        return self.created_at.strftime("%b %d, %Y")
    
    def formatted_date_long(self) -> str:
        return self.created_at.strftime("%B %d, %Y")
    
    def has_markdown(self) -> bool:
        """Check if post has markdown source"""
        return bool(self.markdown_content and self.markdown_content.strip())


class PostCreate(BaseModel):
    title: str
    category: str
    color: str
    size: str
    excerpt: Optional[str] = ""
    content: str
    markdown_content: Optional[str] = ""