import os
import sqlite3
from functools import wraps
from flask import Flask, jsonify, request, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data.db')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'womenhistory-secret-key')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': '需要登录'}), 401
        return f(*args, **kwargs)
    return decorated


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB_PATH):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                tag TEXT,
                img TEXT,
                description TEXT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                info TEXT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE museum (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                img TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()


def row_to_dict(row):
    return {key: row[key] for key in row.keys()} if row else None


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(os.path.join(BASE_DIR, path)):
        return app.send_static_file(path)
    return app.send_static_file('index.html')


@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if username == ADMIN_USER and password == ADMIN_PASS:
        session['logged_in'] = True
        return jsonify({'message': '登录成功'})
    return jsonify({'error': '用户名或密码错误'}), 403


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    session.clear()
    return jsonify({'message': '已退出登录'})


@app.route('/api/auth/status', methods=['GET'])
def api_auth_status():
    return jsonify({'logged_in': bool(session.get('logged_in'))})


@app.route('/api/people', methods=['GET'])
def api_people():
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute('SELECT * FROM people ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([row_to_dict(row) for row in rows])


@app.route('/api/people/<int:item_id>', methods=['GET'])
def api_people_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT * FROM people WHERE id=?', (item_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': '未找到指定人物'}), 404
    return jsonify(row_to_dict(row))


@app.route('/api/articles', methods=['GET'])
def api_articles():
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute('SELECT * FROM articles ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([row_to_dict(row) for row in rows])


@app.route('/api/articles/<int:item_id>', methods=['GET'])
def api_article_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT * FROM articles WHERE id=?', (item_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': '未找到指定文章'}), 404
    return jsonify(row_to_dict(row))


@app.route('/api/museum', methods=['GET'])
def api_museum():
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute('SELECT * FROM museum ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([row_to_dict(row) for row in rows])


@app.route('/api/admin/people', methods=['GET', 'POST'])
@login_required
def admin_people():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'GET':
        rows = cursor.execute('SELECT * FROM people ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([row_to_dict(row) for row in rows])

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    tag = data.get('tag', '').strip()
    img = data.get('img', '').strip()
    description = data.get('description', '').strip()
    content = data.get('content', '').strip()
    if not name:
        conn.close()
        return jsonify({'error': '人物姓名不能为空'}), 400
    cursor.execute(
        'INSERT INTO people (name, tag, img, description, content) VALUES (?, ?, ?, ?, ?)',
        (name, tag, img, description, content)
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = cursor.execute('SELECT * FROM people WHERE id=?', (new_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@app.route('/api/admin/people/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def admin_people_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT * FROM people WHERE id=?', (item_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': '未找到指定人物'}), 404

    if request.method == 'GET':
        conn.close()
        return jsonify(row_to_dict(row))

    if request.method == 'DELETE':
        cursor.execute('DELETE FROM people WHERE id=?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': '删除成功'})

    data = request.get_json() or {}
    name = data.get('name', row['name']).strip()
    tag = data.get('tag', row['tag'] or '').strip()
    img = data.get('img', row['img'] or '').strip()
    description = data.get('description', row['description'] or '').strip()
    content = data.get('content', row['content'] or '').strip()
    if not name:
        conn.close()
        return jsonify({'error': '人物姓名不能为空'}), 400
    cursor.execute(
        'UPDATE people SET name=?, tag=?, img=?, description=?, content=? WHERE id=?',
        (name, tag, img, description, content, item_id)
    )
    conn.commit()
    updated = cursor.execute('SELECT * FROM people WHERE id=?', (item_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(updated))


@app.route('/api/admin/articles', methods=['GET', 'POST'])
@login_required
def admin_articles():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'GET':
        rows = cursor.execute('SELECT * FROM articles ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([row_to_dict(row) for row in rows])

    data = request.get_json() or {}
    title = data.get('title', '').strip()
    info = data.get('info', '').strip()
    content = data.get('content', '').strip()
    if not title:
        conn.close()
        return jsonify({'error': '文章标题不能为空'}), 400
    cursor.execute(
        'INSERT INTO articles (title, info, content) VALUES (?, ?, ?)',
        (title, info, content)
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = cursor.execute('SELECT * FROM articles WHERE id=?', (new_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@app.route('/api/admin/articles/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def admin_article_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT * FROM articles WHERE id=?', (item_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': '未找到指定文章'}), 404

    if request.method == 'GET':
        conn.close()
        return jsonify(row_to_dict(row))

    if request.method == 'DELETE':
        cursor.execute('DELETE FROM articles WHERE id=?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': '删除成功'})

    data = request.get_json() or {}
    title = data.get('title', row['title']).strip()
    info = data.get('info', row['info'] or '').strip()
    content = data.get('content', row['content'] or '').strip()
    if not title:
        conn.close()
        return jsonify({'error': '文章标题不能为空'}), 400
    cursor.execute(
        'UPDATE articles SET title=?, info=?, content=? WHERE id=?',
        (title, info, content, item_id)
    )
    conn.commit()
    updated = cursor.execute('SELECT * FROM articles WHERE id=?', (item_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(updated))


@app.route('/api/admin/museum', methods=['GET', 'POST'])
@login_required
def admin_museum():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'GET':
        rows = cursor.execute('SELECT * FROM museum ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([row_to_dict(row) for row in rows])

    data = request.get_json() or {}
    title = data.get('title', '').strip()
    img = data.get('img', '').strip()
    if not title:
        conn.close()
        return jsonify({'error': '展品名称不能为空'}), 400
    cursor.execute(
        'INSERT INTO museum (title, img) VALUES (?, ?)',
        (title, img)
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = cursor.execute('SELECT * FROM museum WHERE id=?', (new_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@app.route('/api/admin/museum/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def admin_museum_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT * FROM museum WHERE id=?', (item_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': '未找到指定展品'}), 404

    if request.method == 'GET':
        conn.close()
        return jsonify(row_to_dict(row))

    if request.method == 'DELETE':
        cursor.execute('DELETE FROM museum WHERE id=?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': '删除成功'})

    data = request.get_json() or {}
    title = data.get('title', row['title']).strip()
    img = data.get('img', row['img'] or '').strip()
    if not title:
        conn.close()
        return jsonify({'error': '展品名称不能为空'}), 400
    cursor.execute(
        'UPDATE museum SET title=?, img=? WHERE id=?',
        (title, img, item_id)
    )
    conn.commit()
    updated = cursor.execute('SELECT * FROM museum WHERE id=?', (item_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(updated))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
