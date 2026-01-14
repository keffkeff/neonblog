from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import aiofiles
from pathlib import Path
import uuid
import markdown2

from database import init_db, get_all_posts, get_post_by_id, get_latest_post, create_post, update_post

app = FastAPI(title="Neon Blog")

# Markdown processor with extras
MARKDOWN_EXTRAS = [
    "fenced-code-blocks",
    "tables",
    "strike",
    "task_list",
    "code-friendly",
    "cuddled-lists",
    "header-ids",
]

def render_markdown(text: str) -> str:
    """Convert markdown to HTML"""
    if not text:
        return ""
    return markdown2.markdown(text, extras=MARKDOWN_EXTRAS)


# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


# Create upload directories
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "images").mkdir(exist_ok=True)
(UPLOAD_DIR / "videos").mkdir(exist_ok=True)

STATIC_DIR = Path(__file__).parent

# Mount uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Serve static files
@app.get("/styles.css", response_class=FileResponse)
async def serve_css():
    return FileResponse(STATIC_DIR / "styles.css")


@app.get("/favicon.ico", response_class=FileResponse)
async def serve_favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    raise HTTPException(status_code=404, detail="Favicon not found")


# ============================================
# BASE HTML TEMPLATE HELPER
# ============================================
def base_html(title: str, content: str, include_htmx: bool = True) -> str:
    """Generate base HTML wrapper"""
    htmx_script = '<script src="https://unpkg.com/htmx.org@1.9.10"></script>' if include_htmx else ''
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <link rel="stylesheet" href="/styles.css">
    {htmx_script}
</head>
<body>
    {content}
</body>
</html>'''


# ============================================
# MARKDOWN EDITOR ROUTES
# ============================================

@app.get("/editor", response_class=HTMLResponse)
async def editor_page(post_id: Optional[int] = None):
    """Markdown editor page - create new or edit existing"""
    
    # If editing existing post, load its content
    initial_content = ""
    initial_title = ""
    initial_category = ""
    initial_color = "neon-cyan"
    initial_size = "bento-medium"
    initial_excerpt = ""
    form_action = "/posts/create-markdown"
    form_method = "hx-post"
    submit_text = "Publish Post"
    page_title = "Create New Post"
    
    if post_id:
        post = get_post_by_id(post_id)
        if post:
            initial_content = post.content
            initial_title = post.title
            initial_category = post.category.lower()
            initial_color = post.color
            initial_size = post.size
            initial_excerpt = post.excerpt
            form_action = f"/posts/{post_id}/update-markdown"
            form_method = "hx-put"
            submit_text = "Update Post"
            page_title = f"Edit: {post.title}"
    
    # Category options
    categories = ["technology", "design", "tutorial", "opinion", "news", "tips", "tools", "showcase"]
    category_options = "\n".join([
        f'<option value="{cat}" {"selected" if cat == initial_category else ""}>{cat.title()}</option>'
        for cat in categories
    ])
    
    # Color options
    colors = [
        ("neon-pink", "Pink"),
        ("neon-cyan", "Cyan"),
        ("neon-purple", "Purple"),
        ("neon-green", "Green"),
        ("neon-orange", "Orange"),
        ("neon-yellow", "Yellow"),
    ]
    color_options = "\n".join([
        f'<option value="{val}" {"selected" if val == initial_color else ""}>{name}</option>'
        for val, name in colors
    ])
    
    # Size options
    sizes = [
        ("bento-small", "Small"),
        ("bento-medium", "Medium"),
        ("bento-large", "Large"),
        ("bento-tall", "Tall"),
        ("bento-wide", "Wide"),
    ]
    size_options = "\n".join([
        f'<option value="{val}" {"selected" if val == initial_size else ""}>{name}</option>'
        for val, name in sizes
    ])
    
    content = f'''
    <header class="latest-header">
        <a href="/">
            <span class="latest-tag">HOME</span>
            <h1>Back to Blog</h1>
        </a>
    </header>

    <main class="editor-container">
        <div class="editor-header">
            <h1 class="editor-title">
                <span class="neon-text">✎</span> {page_title}
            </h1>
            <p class="editor-subtitle">Write in Markdown, see live preview</p>
        </div>

        <form class="editor-form"
              {form_method}="{form_action}"
              hx-target="body"
              hx-swap="innerHTML"
              hx-encoding="multipart/form-data">
            
            <!-- Post Settings Bar -->
            <div class="editor-settings">
                <div class="setting-group">
                    <label for="title">Title</label>
                    <input type="text" id="title" name="title" 
                           value="{initial_title}"
                           placeholder="Post title..." required>
                </div>
                
                <div class="setting-group">
                    <label for="category">Category</label>
                    <select id="category" name="category" required>
                        <option value="">Select...</option>
                        {category_options}
                    </select>
                </div>
                
                <div class="setting-group">
                    <label for="color">Style</label>
                    <select id="color" name="color" required>
                        {color_options}
                    </select>
                </div>
                
                <div class="setting-group">
                    <label for="size">Size</label>
                    <select id="size" name="size" required>
                        {size_options}
                    </select>
                </div>
            </div>

            <!-- Excerpt -->
            <div class="editor-excerpt">
                <label for="excerpt">Excerpt (optional)</label>
                <input type="text" id="excerpt" name="excerpt" 
                       value="{initial_excerpt}"
                       placeholder="Brief description for post cards...">
            </div>

            <!-- Split Editor -->
            <div class="editor-split">
                <!-- Left: Markdown Input -->
                <div class="editor-pane editor-input">
                    <div class="pane-header">
                        <span class="pane-title">📝 Markdown</span>
                        <span class="pane-hint">Supports GitHub-flavored markdown</span>
                    </div>
                    <textarea 
                        id="markdown-input"
                        name="content"
                        placeholder="# Start writing..."
                    hx-post="/preview"
                    hx-trigger="keyup changed delay:400ms"
                    hx-target="#preview-content"
                    hx-swap="innerHTML"
                    required
                >{initial_content}</textarea>
            </div>

            <!-- Right: Live Preview -->
            <div class="editor-pane editor-preview">
                <div class="pane-header">
                    <span class="pane-title">👁️ Preview</span>
                    <span class="pane-hint" id="preview-status">Live preview</span>
                </div>
                <div class="preview-content markdown-body" id="preview-content">
                    <p class="preview-placeholder">Start typing to see preview...</p>
                </div>
            </div>
        </div>

        <!-- Media Upload -->
        <div class="editor-media">
            <label for="media">📎 Attach Media (optional)</label>
            <input type="file" id="media" name="media" 
                   multiple accept="image/*,video/*" class="file-input">
        </div>

        <!-- Actions -->
        <div class="editor-actions">
            <a href="/" class="btn btn-secondary">Cancel</a>
            <button type="submit" class="btn btn-primary">
                <span class="btn-text">{submit_text}</span>
                <span class="btn-icon">→</span>
            </button>
        </div>
    </form>
</main>
'''

    return HTMLResponse(content=base_html(page_title + " - Neon Blog", content))

@app.post("/preview", response_class=HTMLResponse)
async def preview_markdown(content: str = Form("")):
    """Render markdown to HTML for live preview"""
    if not content.strip():
        return HTMLResponse(
            content='<p class="preview-placeholder">Start typing to see preview...</p>'
        )

    html_content = render_markdown(content)
    return HTMLResponse(content=html_content)

@app.post("/posts/create-markdown", response_class=HTMLResponse)
async def create_markdown_post(
title: str = Form(...),
category: str = Form(...),
color: str = Form(...),
size: str = Form(...),
excerpt: str = Form(""),
content: str = Form(...),
media: List[UploadFile] = File(default=[])
):
    """Create a new post from markdown content"""
    # Handle file uploads
    media_files = []
    for file in media:
        if file.filename:
            file_ext = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            
            if file.content_type and file.content_type.startswith('image/'):
                file_path = UPLOAD_DIR / "images" / unique_filename
            elif file.content_type and file.content_type.startswith('video/'):
                file_path = UPLOAD_DIR / "videos" / unique_filename
            else:
                continue
            
            async with aiofiles.open(file_path, 'wb') as f:
                file_content = await file.read()
                await f.write(file_content)
            
            media_files.append(str(file_path))

    # Convert markdown to HTML for storage
    html_content = render_markdown(content)

    # Create post in database
    new_post = create_post(
        title=title,
        category=category,
        color=color,
        size=size,
        excerpt=excerpt,
        content=html_content,
        media_files=media_files,
        markdown_content=content  # Store original markdown
    )

    # Redirect to homepage (full page reload via htmx)
    return HTMLResponse(
        content="",
        status_code=200,
        headers={"HX-Redirect": "/"}
    )

@app.put("/posts/{post_id}/update-markdown", response_class=HTMLResponse)
async def update_markdown_post(
post_id: int,
title: str = Form(...),
category: str = Form(...),
color: str = Form(...),
size: str = Form(...),
excerpt: str = Form(""),
content: str = Form(...),
media: List[UploadFile] = File(default=[])
):
    """Update an existing post with markdown content"""

    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Handle new file uploads
    media_files = post.get_media_list()  # Keep existing media
    for file in media:
        if file.filename:
            file_ext = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            
            if file.content_type and file.content_type.startswith('image/'):
                file_path = UPLOAD_DIR / "images" / unique_filename
            elif file.content_type and file.content_type.startswith('video/'):
                file_path = UPLOAD_DIR / "videos" / unique_filename
            else:
                continue
            
            async with aiofiles.open(file_path, 'wb') as f:
                file_content = await file.read()
                await f.write(file_content)
            
            media_files.append(str(file_path))

    # Convert markdown to HTML
    html_content = render_markdown(content)

    # Update post
    update_post(
        post_id=post_id,
        title=title,
        category=category,
        color=color,
        size=size,
        excerpt=excerpt,
        content=html_content,
        media_files=media_files,
        markdown_content=content
    )

    return HTMLResponse(
        content="",
        status_code=200,
        headers={"HX-Redirect": f"/posts/{post_id}"}
    )

@app.get("/", response_class=HTMLResponse)
async def homepage():
    posts = get_all_posts()
    latest = get_latest_post()

    # Build post cards HTML
    cards_html = ""
    for post in posts:
        excerpt_html = f'<p class="post-excerpt">{post.excerpt}</p>' if post.excerpt else ''
        cards_html += f'''
        <article class="bento-item {post.size} {post.color}">
            <a href="/posts/{post.id}" class="post-link">
                <div class="post-category">{post.category}</div>
                <h2>{post.title}</h2>
                {excerpt_html}
                <div class="post-meta">
                    <span>{post.formatted_date()}</span>
                    <span>•</span>
                    <span>{post.read_time}</span>
                </div>
            </a>
        </article>
        '''

    latest_title = latest.title if latest else "Welcome to Neon Blog"
    latest_id = latest.id if latest else 1

    content = f'''
    <header class="latest-header">
        <a href="/posts/{latest_id}">
            <span class="latest-tag">LATEST</span>
            <h1>{latest_title}</h1>
        </a>
    </header>

    <main class="container">
        <section class="bento-grid" id="posts-grid">
            {cards_html}
        </section>

        <!-- Quick Actions -->
        <section class="quick-actions">
            <a href="/editor" class="action-card neon-cyan">
                <span class="action-icon">✎</span>
                <span class="action-text">
                    <strong>Markdown Editor</strong>
                    <small>Create post with live preview</small>
                </span>
            </a>
        </section>

        <section class="add-post-section">
            <h2 class="section-title">
                <span class="neon-text">+</span> Quick Create (HTML)
            </h2>
            
            <form class="post-form"
                  hx-post="/posts/create"
                  hx-target="#posts-grid"
                  hx-swap="afterbegin"
                  hx-encoding="multipart/form-data"
                  hx-on::after-request="this.reset()">
                
                <div class="form-group">
                    <label for="post-title">Title</label>
                    <input type="text" id="post-title" name="title" 
                           placeholder="Enter your post title..." required>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="post-category">Category</label>
                        <select id="post-category" name="category" required>
                            <option value="">Select category...</option>
                            <option value="technology">Technology</option>
                            <option value="design">Design</option>
                            <option value="tutorial">Tutorial</option>
                            <option value="opinion">Opinion</option>
                            <option value="news">News</option>
                            <option value="tips">Tips</option>
                            <option value="tools">Tools</option>
                            <option value="showcase">Showcase</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="post-color">Neon Style</label>
                        <select id="post-color" name="color" required>
                            <option value="neon-pink">Pink</option>
                            <option value="neon-cyan">Cyan</option>
                            <option value="neon-purple">Purple</option>
                            <option value="neon-green">Green</option>
                            <option value="neon-orange">Orange</option>
                            <option value="neon-yellow">Yellow</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="post-size">Card Size</label>
                        <select id="post-size" name="size" required>
                            <option value="bento-small">Small</option>
                            <option value="bento-medium">Medium</option>
                            <option value="bento-large">Large</option>
                            <option value="bento-tall">Tall</option>
                            <option value="bento-wide">Wide</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label for="post-excerpt">Excerpt</label>
                    <textarea id="post-excerpt" name="excerpt" rows="2"
                              placeholder="Brief description of your post..."></textarea>
                </div>

                <div class="form-group">
                    <label for="post-content">Content (HTML)</label>
                    <textarea id="post-content" name="content" rows="8"
                              placeholder="Write your post content here... (HTML supported)"
                              required></textarea>
                </div>

                <div class="form-group">
                    <label for="post-media">Media (Images/Videos)</label>
                    <input type="file" id="post-media" name="media" 
                           multiple accept="image/*,video/*" class="file-input">
                </div>

                <div class="form-actions">
                    <button type="reset" class="btn btn-secondary">Clear</button>
                    <button type="submit" class="btn btn-primary">
                        <span class="btn-text">Publish Post</span>
                        <span class="btn-icon">→</span>
                    </button>
                </div>
            </form>
        </section>
    </main>
    '''

    return HTMLResponse(content=base_html("Neon Blog", content))

@app.get("/posts/{post_id}", response_class=HTMLResponse)
async def get_post_page(post_id: int):
    post = get_post_by_id(post_id)

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Build media HTML
    media_html = ""
    media_list = post.get_media_list()
    if media_list:
        media_html = '<div class="post-media">'
        for media_file in media_list:
            if media_file.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                media_html += f'<img src="/{media_file}" alt="Post media">'
            elif media_file.endswith(('.mp4', '.webm', '.ogg')):
                media_html += f'<video src="/{media_file}" controls></video>'
        media_html += '</div>'

    content = f'''
    <header class="latest-header">
        <a href="/">
            <span class="latest-tag">HOME</span>
            <h1>Back to all posts</h1>
        </a>
    </header>

    <main class="post-page">
        <div class="post-nav">
            <a href="/" class="back-link">← Back to all posts</a>
            <a href="/editor?post_id={post.id}" class="edit-link">✎ Edit Post</a>
        </div>
        
        <article class="post-full">
            <span class="post-category">{post.category}</span>
            <h1>{post.title}</h1>
            <div class="post-meta">
                <span>Published {post.formatted_date_long()}</span>
                <span>•</span>
                <span>{post.read_time}</span>
            </div>
            
            <div class="post-body markdown-body">
                {post.content}
                {media_html}
            </div>
        </article>
    </main>
    '''

    return HTMLResponse(content=base_html(f"{post.title} - Neon Blog", content))

@app.post("/posts/create", response_class=HTMLResponse)
async def create_new_post(
title: str = Form(...),
category: str = Form(...),
color: str = Form(...),
size: str = Form(...),
excerpt: str = Form(""),
content: str = Form(...),
media: List[UploadFile] = File(default=[])
):
    # Handle file uploads
    media_files = []
    for file in media:
        if file.filename:
            file_ext = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"

            if file.content_type and file.content_type.startswith('image/'):
                file_path = UPLOAD_DIR / "images" / unique_filename
            elif file.content_type and file.content_type.startswith('video/'):
                file_path = UPLOAD_DIR / "videos" / unique_filename
            else:
                continue
            
            async with aiofiles.open(file_path, 'wb') as f:
                file_content = await file.read()
                await f.write(file_content)
            
            media_files.append(str(file_path))

    # Create post in database
    new_post = create_post(
        title=title,
        category=category,
        color=color,
        size=size,
        excerpt=excerpt,
        content=content,
        media_files=media_files
    )

    excerpt_html = f'<p class="post-excerpt">{new_post.excerpt}</p>' if new_post.excerpt else ''

    return HTMLResponse(content=f'''
    <article class="bento-item {new_post.size} {new_post.color}">
        <a href="/posts/{new_post.id}" class="post-link">
            <div class="post-category">{new_post.category}</div>
            <h2>{new_post.title}</h2>
            {excerpt_html}
            <div class="post-meta">
                <span>{new_post.formatted_date()}</span>
                <span>•</span>
                <span>Just now</span>
            </div>
        </a>
    </article>
    ''')

@app.get("/health")
async def health_check():
    posts = get_all_posts()
    return {"status": "healthy", "posts_count": len(posts)}

    if name == "main":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)