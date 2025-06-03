from flask import Flask, render_template_string, abort, request
import os
import json

# 将 static_folder 设置为当前目录，static_url_path 设置为空字符串，
# 这样 /<folder>/<filename> 会映射到当前目录下的同名文件。
app = Flask(__name__, static_folder='.', static_url_path='')

# 启动时预加载所有文件夹的元数据，加速首页加载
FOLDERS_META = []
for name in os.listdir('.'):
    if os.path.isdir(name) and os.path.isfile(os.path.join(name, '__info.json')):
        folder_path = os.path.join('.', name)
        json_path = os.path.join(folder_path, '__info.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except Exception:
            raw_data = []
        # 列表视图: 取最近1条动态的首张图作为预览
        list_preview = None
        if raw_data:
            pictures = raw_data[0].get('item', {}).get('pictures', [])
            if pictures:
                clean_url = pictures[0].split('?', 1)[0]
                filename = os.path.basename(clean_url)
                local_file = os.path.join(folder_path, filename)
                if os.path.isfile(local_file):
                    list_preview = f"/{name}/{filename}"
                else:
                    list_preview = clean_url
        # 网格视图: 取最近1条动态的首张图作为预览
        grid_preview = list_preview
        FOLDERS_META.append({'name': name, 'list_preview': list_preview, 'grid_preview': grid_preview})

# 模板：显示所有包含 __info.json 的文件夹列表，带列表/网格切换、预览图片、搜索栏
template_index = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feed Folders</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f8fa; margin: 0; padding: 0; }
        .container { width: 80%; max-width: 900px; margin: 20px auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .search-input { padding: 8px 12px; width: 200px; border: 1px solid #ccc; border-radius: 4px; }
        .search-btn, .toggle-btn { padding: 8px 12px; border: none; background: #1da1f2; color: #fff; border-radius: 4px; cursor: pointer; margin-left: 10px; }
        /* 列表视图 */
        .folder-list { list-style: none; padding: 0; }
        .folder-item { background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; margin-bottom: 15px; padding: 10px; display: flex; align-items: center; cursor: pointer; }
        .folder-item .info { flex: 1; font-size: 16px; color: #1da1f2; }
        .folder-item .info:hover { text-decoration: underline; }
        .preview-list img { width: 60px; height: 60px; object-fit: cover; border-radius: 4px; margin-left: 15px; }
        /* 网格视图 */
        .folder-list.grid-view { display: flex; flex-wrap: wrap; gap: 15px; }
        .folder-list.grid-view .folder-item { width: calc(25% - 15px); flex-direction: column; align-items: center; padding: 0; margin-bottom: 15px; }
        .folder-list.grid-view .folder-item .info { width: 100%; text-align: center; padding: 10px 0; border-bottom: 1px solid #e1e8ed; }
        .folder-list.grid-view .folder-item .grid-preview { position: relative; width: 100%; padding-bottom: 75%; overflow: hidden; }
        .folder-list.grid-view .folder-item .grid-preview img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <form method="get" action="/search" id="searchForm">
                <input type="text" name="q" id="search" class="search-input" placeholder="搜索文件夹...">
                <button type="submit" class="search-btn">搜索</button>
                <button type="button" id="toggleView" class="toggle-btn">切换视图</button>
            </form>
        </div>
        <ul id="folderList" class="folder-list">
            {% for folder in folders %}
            <li class="folder-item" onclick="window.location='/feed/{{ folder.name }}'">
                <div class="info">{{ folder.name }}</div>
                <div class="preview-list">
                    {% if folder.list_preview %}<img src="{{ folder.list_preview }}" alt="preview">{% endif %}
                </div>
                <div class="grid-preview" style="display:none; width:100%;">
                    {% if folder.grid_preview %}<img src="{{ folder.grid_preview }}" alt="grid preview">{% endif %}
                </div>
            </li>
            {% endfor %}
        </ul>
    </div>
    <script>
        const toggleBtn = document.getElementById('toggleView');
        const folderList = document.getElementById('folderList');
        // 切换列表/网格
        toggleBtn.addEventListener('click', () => {
            const items = document.querySelectorAll('.folder-item');
            folderList.classList.toggle('grid-view');
            if (folderList.classList.contains('grid-view')) {
                items.forEach(item => {
                    if (item.querySelector('.preview-list')) item.querySelector('.preview-list').style.display = 'none';
                    if (item.querySelector('.grid-preview')) item.querySelector('.grid-preview').style.display = 'block';
                });
            } else {
                items.forEach(item => {
                    if (item.querySelector('.preview-list')) item.querySelector('.preview-list').style.display = 'flex';
                    if (item.querySelector('.grid-preview')) item.querySelector('.grid-preview').style.display = 'none';
                });
            }
        });
    </script>
</body>
</html>
'''

# 模板：显示单个文件夹下的动态流，支持点击图片放大预览
template_feed = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feed - {{ folder }}</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f8fa; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .back-link { margin-bottom: 20px; display: inline-block; text-decoration: none; color: #1da1f2; cursor: pointer; }
        .post { background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; margin-bottom: 20px; padding: 15px; }
        .post-title { font-size: 16px; font-weight: bold; margin-bottom: 8px; }
        .post-time { color: #657786; font-size: 12px; margin-bottom: 10px; }
        .post-desc { font-size: 14px; margin-bottom: 10px; }
        .post-images { display: flex; flex-wrap: wrap; gap: 5px; }
        .post-images img { width: calc(50% - 5px); border-radius: 8px; cursor: pointer; }
        /* Lightbox 样式 */
        #lightboxOverlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); justify-content: center; align-items: center; z-index: 1000; }
        #lightboxOverlay img { max-width: 90%; max-height: 90%; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="back-link" onclick="window.location='/'">&larr; Back to folders</div>
        <h2>Feed - {{ folder }}</h2>
        {% for post in posts %}
        <div class="post">
            {% if post.title %}
            <div class="post-title">{{ post.title }}</div>
            {% endif %}
            <div class="post-time">{{ post.time }}</div>
            <div class="post-desc">{{ post.description }}</div>
            <div class="post-images">
                {% for img in post.images %}
                <img src="{{ img }}" alt="Post image" onclick="openLightbox('{{ img }}')">
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
    <div id="lightboxOverlay" onclick="closeLightbox()">
        <img id="lightboxImg" src="" alt="">
    </div>
    <script>
        function openLightbox(src) {
            const overlay = document.getElementById('lightboxOverlay');
            const img = document.getElementById('lightboxImg');
            img.src = src;
            overlay.style.display = 'flex';
        }
        function closeLightbox() {
            document.getElementById('lightboxOverlay').style.display = 'none';
        }
    </script>
</body>
</html>
'''

# 模板：搜索结果页面保持不变
template_search = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Results for "{{ query }}"</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f8fa; margin: 0; padding: 0; }
        .container { max-width: 800px; margin: 20px auto; padding: 20px; }
        .back-link { margin-bottom: 20px; display: inline-block; text-decoration: none; color: #1da1f2; cursor: pointer; }
        .result { background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; margin-bottom: 20px; padding: 15px; }
        .result-header { font-size: 14px; color: #657786; margin-bottom: 10px; }
        .result-title { font-size: 16px; font-weight: bold; margin-bottom: 8px; }
        .result-desc { font-size: 14px; margin-bottom: 10px; }
        .result-images { display: flex; flex-wrap: wrap; gap: 5px; }
        .result-images img { width: calc(50% - 5px); border-radius: 8px; cursor: pointer; }
        #lightboxOverlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); justify-content: center; align-items: center; z-index: 1000; }
        #lightboxOverlay img { max-width: 90%; max-height: 90%; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="back-link" onclick="window.location='/'">&larr; Back to folders</div>
        <h2>Search Results for "{{ query }}"</h2>
        {% if results %}
            {% for res in results %}
            <div class="result">
                <div class="result-header">Folder: <a href="/feed/{{ res.folder }}">{{ res.folder }}</a> | {{ res.time }}</div>
                {% if res.title %}
                <div class="result-title">{{ res.title }}</div>
                {% endif %}
                <div class="result-desc">{{ res.description }}</div>
                <div class="result-images">
                    {% for img in res.images %}
                    <img src="{{ img }}" alt="Result image" onclick="openLightbox('{{ img }}')">
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <p>No results found.</p>
        {% endif %}
    </div>
    <div id="lightboxOverlay" onclick="closeLightbox()">
        <img id="lightboxImg" src="" alt="">
    </div>
    <script>
        function openLightbox(src) {
            const overlay = document.getElementById('lightboxOverlay');
            const img = document.getElementById('lightboxImg');
            img.src = src;
            overlay.style.display = 'flex';
        }
        function closeLightbox() {
            document.getElementById('lightboxOverlay').style.display = 'none';
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(template_index, folders=FOLDERS_META)

@app.route('/feed/<folder>')
def feed(folder):
    folder_path = os.path.join('.', folder)
    json_path = os.path.join(folder_path, '__info.json')
    if not os.path.isdir(folder_path) or not os.path.isfile(json_path):
        return abort(404)

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    posts = []
    for entry in raw_data:
        title = entry.get('item', {}).get('title') or ''
        description = entry.get('item', {}).get('description', '')
        time = entry.get('time', '')
        pictures = entry.get('item', {}).get('pictures', [])
        image_srcs = []
        for url in pictures:
            clean_url = url.split('?', 1)[0]
            filename = os.path.basename(clean_url)
            local_file = os.path.join(folder_path, filename)
            if os.path.isfile(local_file):
                local_url = f"/{folder}/{filename}"
                image_srcs.append(local_url)
            else:
                image_srcs.append(clean_url)
        posts.append({
            'title': title,
            'description': description,
            'time': time,
            'images': image_srcs,
            'folder': folder
        })
    return render_template_string(template_feed, folder=folder, posts=posts)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    results = []
    if query:
        for name in os.listdir('.'):
            if os.path.isdir(name) and os.path.isfile(os.path.join(name, '__info.json')):
                folder_path = os.path.join('.', name)
                json_path = os.path.join(folder_path, '__info.json')
                with open(json_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                for entry in raw_data:
                    title = entry.get('item', {}).get('title') or ''
                    description = entry.get('item', {}).get('description', '')
                    combined = (title + ' ' + description).lower()
                    if query in combined:
                        time = entry.get('time', '')
                        pictures = entry.get('item', {}).get('pictures', [])
                        image_srcs = []
                        for url in pictures:
                            clean_url = url.split('?', 1)[0]
                            filename = os.path.basename(clean_url)
                            local_file = os.path.join(folder_path, filename)
                            if os.path.isfile(local_file):
                                local_url = f"/{name}/{filename}"
                                image_srcs.append(local_url)
                            else:
                                image_srcs.append(clean_url)
                        results.append({
                            'folder': name,
                            'title': title,
                            'description': description,
                            'time': time,
                            'images': image_srcs
                        })
    return render_template_string(template_search, query=query, results=results)

if __name__ == '__main__':
    app.run(debug=True)
