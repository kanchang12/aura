from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, BlogPost
from datetime import datetime
from slugify import slugify
import bleach

blog_bp = Blueprint('blog', __name__)

def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@blog_bp.route('/posts', methods=['GET'])
def get_posts():
    """Get published blog posts (public endpoint for SEO)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        posts = BlogPost.query.filter_by(published=True)\
            .order_by(BlogPost.published_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'posts': [post.to_dict() for post in posts.items],
            'total': posts.total,
            'pages': posts.pages,
            'current_page': page
        }), 200

    except Exception as e:
        print(f"Error fetching posts: {e}")
        return jsonify({'error': 'Failed to fetch posts'}), 500

@blog_bp.route('/posts/<slug>', methods=['GET'])
def get_post(slug):
    """Get a single blog post by slug (public endpoint)"""
    try:
        post = BlogPost.query.filter_by(slug=slug, published=True).first()

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        return jsonify(post.to_dict()), 200

    except Exception as e:
        print(f"Error fetching post: {e}")
        return jsonify({'error': 'Failed to fetch post'}), 500

@blog_bp.route('/admin/posts', methods=['GET'])
@admin_required
def get_all_posts():
    """Get all blog posts including drafts (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        posts = BlogPost.query.order_by(BlogPost.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'posts': [post.to_dict() for post in posts.items],
            'total': posts.total,
            'pages': posts.pages,
            'current_page': page
        }), 200

    except Exception as e:
        print(f"Error fetching posts: {e}")
        return jsonify({'error': 'Failed to fetch posts'}), 500

@blog_bp.route('/admin/posts', methods=['POST'])
@admin_required
def create_post():
    """Create a new blog post (admin only)"""
    try:
        data = request.get_json()

        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        excerpt = data.get('excerpt', '').strip()

        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400

        # Generate slug
        slug = slugify(title)

        # Check if slug already exists
        existing = BlogPost.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{datetime.utcnow().timestamp()}"

        # Sanitize HTML content
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4',
                       'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre']
        allowed_attrs = {'a': ['href', 'title'], 'img': ['src', 'alt']}
        clean_content = bleach.clean(content, tags=allowed_tags, attributes=allowed_attrs)

        # Create post
        post = BlogPost(
            title=title,
            slug=slug,
            content=clean_content,
            excerpt=excerpt or clean_content[:160],
            meta_description=data.get('meta_description', '')[:160],
            meta_keywords=data.get('meta_keywords', ''),
            author_id=current_user.id,
            published=data.get('published', False)
        )

        if post.published:
            post.published_at = datetime.utcnow()

        db.session.add(post)
        db.session.commit()

        return jsonify({
            'message': 'Post created successfully',
            'post': post.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating post: {e}")
        return jsonify({'error': 'Failed to create post'}), 500

@blog_bp.route('/admin/posts/<int:post_id>', methods=['PUT'])
@admin_required
def update_post(post_id):
    """Update a blog post (admin only)"""
    try:
        post = BlogPost.query.get(post_id)

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        data = request.get_json()

        if 'title' in data:
            post.title = data['title'].strip()
            post.slug = slugify(post.title)

        if 'content' in data:
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4',
                           'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre']
            allowed_attrs = {'a': ['href', 'title'], 'img': ['src', 'alt']}
            post.content = bleach.clean(data['content'], tags=allowed_tags, attributes=allowed_attrs)

        if 'excerpt' in data:
            post.excerpt = data['excerpt'].strip()

        if 'meta_description' in data:
            post.meta_description = data['meta_description'][:160]

        if 'meta_keywords' in data:
            post.meta_keywords = data['meta_keywords']

        if 'published' in data:
            was_published = post.published
            post.published = data['published']

            if post.published and not was_published:
                post.published_at = datetime.utcnow()

        post.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Post updated successfully',
            'post': post.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating post: {e}")
        return jsonify({'error': 'Failed to update post'}), 500

@blog_bp.route('/admin/posts/<int:post_id>', methods=['DELETE'])
@admin_required
def delete_post(post_id):
    """Delete a blog post (admin only)"""
    try:
        post = BlogPost.query.get(post_id)

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        db.session.delete(post)
        db.session.commit()

        return jsonify({'message': 'Post deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting post: {e}")
        return jsonify({'error': 'Failed to delete post'}), 500
