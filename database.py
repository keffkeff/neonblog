import sqlite3
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from models import Post

DATABASE_PATH = Path("blog.db")


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            color TEXT NOT NULL,
            size TEXT NOT NULL,
            excerpt TEXT DEFAULT '',
            content TEXT NOT NULL,
            markdown_content TEXT DEFAULT '',
            media_files TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_time TEXT DEFAULT '1 min read'
        )
    ''')
    
    # Add markdown_content column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN markdown_content TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add updated_at column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    
    # Add sample posts if table is empty
    cursor.execute('SELECT COUNT(*) FROM posts')
    if cursor.fetchone()[0] == 0:
        _insert_sample_posts(cursor)
        conn.commit()
    
    conn.close()


def _insert_sample_posts(cursor):
    """Insert sample posts for demo"""
    sample_posts = [
        (
            "The Future of Web Development: HTMX and Hypermedia",
            "TECHNOLOGY",
            "neon-pink",
            "bento-large",
            "Exploring how HTMX is changing the way we think about building interactive web applications...",
            """<p>In recent years, the web development landscape has been dominated by JavaScript frameworks like React, Vue, and Angular. But a quiet revolution is happening, led by tools like HTMX that embrace the original hypermedia model of the web.</p>
            <p>HTMX allows you to access modern browser features directly from HTML, rather than using JavaScript. This means you can create dynamic, interactive web applications with significantly less code and complexity.</p>
            <h2>Why HTMX?</h2>
            <p>The main advantage of HTMX is simplicity. Instead of managing complex client-side state, you let the server handle the logic and return HTML fragments that HTMX swaps into your page.</p>
            <p>This approach has several benefits:</p>
            <ul>
                <li>Smaller bundle sizes</li>
                <li>Better SEO out of the box</li>
                <li>Simpler mental model</li>
                <li>Works with any backend language</li>
            </ul>""",
            """# The Future of Web Development: HTMX and Hypermedia

In recent years, the web development landscape has been dominated by JavaScript frameworks like React, Vue, and Angular. But a quiet revolution is happening, led by tools like HTMX that embrace the original hypermedia model of the web.

HTMX allows you to access modern browser features directly from HTML, rather than using JavaScript. This means you can create dynamic, interactive web applications with significantly less code and complexity.

## Why HTMX?

The main advantage of HTMX is simplicity. Instead of managing complex client-side state, you let the server handle the logic and return HTML fragments that HTMX swaps into your page.

This approach has several benefits:

- Smaller bundle sizes
- Better SEO out of the box
- Simpler mental model
- Works with any backend language""",
            "",
            "5 min read"
        ),
        (
            "Neon Aesthetics in Modern UI",
            "DESIGN",
            "neon-cyan",
            "bento-medium",
            "Why glowing colors are making a comeback...",
            """<p>Neon colors have made a dramatic comeback in web design, bringing energy and personality to digital interfaces.</p>
            <p>The cyberpunk aesthetic, popularized by movies and games, has influenced modern UI design trends.</p>
            <h2>Key Principles</h2>
            <ul>
                <li>Use dark backgrounds to make colors pop</li>
                <li>Add subtle glow effects with box-shadow</li>
                <li>Limit your neon palette to maintain hierarchy</li>
            </ul>""",
            """# Neon Aesthetics in Modern UI

Neon colors have made a dramatic comeback in web design, bringing energy and personality to digital interfaces.

The cyberpunk aesthetic, popularized by movies and games, has influenced modern UI design trends.

## Key Principles

- Use dark backgrounds to make colors pop
- Add subtle glow effects with box-shadow
- Limit your neon palette to maintain hierarchy""",
            "",
            "3 min read"
        ),
        (
            "Quick CSS Tricks",
            "TIPS",
            "neon-purple",
            "bento-small",
            "",
            """<p>Here are some useful CSS tricks:</p>
            <h3>Center anything with Flexbox</h3>
            <pre><code>display: flex;
align-items: center;
justify-content: center;</code></pre>""",
            """# Quick CSS Tricks

Here are some useful CSS tricks:

### Center anything with Flexbox

```css
display: flex;
align-items: center;
justify-content: center;
```""",
            "",
            "2 min read"
        ),
    ]
    
    for post in sample_posts:
        cursor.execute('''
            INSERT INTO posts (title, category, color, size, excerpt, content, markdown_content, media_files, read_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', post)


def _row_to_post(row) -> Post:
    """Convert database row to Post object"""
    # Handle the case where markdown_content might not exist in old rows
    markdown_content = ""
    try:
        markdown_content = row['markdown_content'] or ""
    except (IndexError, KeyError):
        pass
    
    return Post(
        id=row['id'],
        title=row['title'],
        category=row['category'],
        color=row['color'],
        size=row['size'],
        excerpt=row['excerpt'] or '',
        content=row['content'],
        markdown_content=markdown_content,
        media_files=row['media_files'] or '',
        created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
        read_time=row['read_time']
    )


def get_all_posts() -> List[Post]:
    """Get all posts sorted by date (newest first)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_post(row) for row in rows]


def get_post_by_id(post_id: int) -> Optional[Post]:
    """Get a specific post by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return _row_to_post(row)
    return None


def get_latest_post() -> Optional[Post]:
    """Get the most recent post"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts ORDER BY created_at DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return _row_to_post(row)
    return None


def create_post(
    title: str,
    category: str,
    color: str,
    size: str,
    excerpt: str,
    content: str,
    media_files: List[str],
    markdown_content: str = ""
) -> Post:
    """Create a new post"""
    # Calculate read time based on content
    word_count = len(content.split())
    read_time = f"{max(1, word_count // 200)} min read"
    
    # Convert media list to comma-separated string
    media_str = ','.join(media_files)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO posts (title, category, color, size, excerpt, content, markdown_content, media_files, read_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, category.upper(), color, size, excerpt, content, markdown_content, media_str, read_time))
    
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return get_post_by_id(post_id)


def update_post(
    post_id: int,
    title: str,
    category: str,
    color: str,
    size: str,
    excerpt: str,
    content: str,
    media_files: List[str],
    markdown_content: str = ""
) -> Optional[Post]:
    """Update an existing post"""
    # Calculate read time
    word_count = len(content.split())
    read_time = f"{max(1, word_count // 200)} min read"
    
    # Convert media list to comma-separated string
    media_str = ','.join(media_files)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE posts 
        SET title = ?, 
            category = ?, 
            color = ?, 
            size = ?, 
            excerpt = ?, 
            content = ?,
            markdown_content = ?,
            media_files = ?, 
            read_time = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (title, category.upper(), color, size, excerpt, content, markdown_content, media_str, read_time, post_id))
    
    conn.commit()
    conn.close()
    
    return get_post_by_id(post_id)


def delete_post(post_id: int) -> bool:
    """Delete a post by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted