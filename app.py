import sys
import os
import threading
import logging
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import requests
import urllib3
import webview

# 配置日志
logging.basicConfig(filename='error.log', level=logging.ERROR, encoding='utf-8')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app = Flask(__name__, static_folder=resource_path('static'))
CORS(app)

APIS = [
    "http://cj.ffzyapi.com/api.php/provide/vod/from/ffm3u8/at/json",
    "https://cj.lziapi.com/api.php/provide/vod/from/lzm3u8/at/json"
]

def fetch_data(params):
    headers = {"User-Agent": "Mozilla/5.0"}
    for api_url in APIS:
        try:
            resp = requests.get(api_url, params=params, headers=headers, timeout=5, verify=False)
            if resp.status_code == 200: return resp.json()
        except: continue
    return None

# === 核心新增：图片代理接口 ===
# 前端通过 /api/proxy_img?url=... 来请求图片
@app.route('/api/proxy_img')
def proxy_img():
    img_url = request.args.get('url')
    if not img_url: return "", 404
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/" # 伪造来源，防止防盗链
        }
        # stream=True 允许流式传输，速度更快
        resp = requests.get(img_url, headers=headers, verify=False, timeout=5, stream=True)
        
        # 将获取到的图片数据直接透传给前端
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        return Response(resp.iter_content(chunk_size=1024),
                        status=resp.status_code,
                        headers=headers)
    except Exception as e:
        print(f"图片加载失败: {e}")
        return "", 404
# ===========================

@app.route('/')
def index():
    return send_from_directory(resource_path('.'), 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/api/categories')
def get_categories():
    data = fetch_data({'ac': 'list'})
    return jsonify({'code': 200, 'data': data.get('class', [])}) if data else jsonify({'code': 500, 'data': []})

@app.route('/api/videos')
def get_videos():
    params = {'ac': 'detail', 'pg': request.args.get('page', 1), 'wd': request.args.get('wd', ''), 't': request.args.get('t', '')}
    data = fetch_data(params)
    if data:
        clean_list = []
        for item in data.get('list', []):
            clean_list.append({
                'id': item.get('vod_id'), 'title': item.get('vod_name'), 'pic': item.get('vod_pic'),
                'category': item.get('type_name'), 'year': item.get('vod_year', ''), 
                'area': item.get('vod_area', ''), 'remarks': item.get('vod_remarks', ''), 'desc': item.get('vod_blurb')
            })
        return jsonify({'code': 200, 'data': clean_list})
    return jsonify({'code': 500})

@app.route('/api/video_detail')
def get_video_detail():
    data = fetch_data({'ac': 'detail', 'ids': request.args.get('id')})
    if data and data.get('list'):
        item = data['list'][0]
        episode_list = []
        if item.get('vod_play_url'):
            for seg in item.get('vod_play_url').split('#'):
                if '$' in seg: name, url = seg.split('$')
                else: name, url = '正片', seg
                episode_list.append({'name': name, 'url': url})
        return jsonify({'code': 200, 'data': {'id': item.get('vod_id'), 'title': item.get('vod_name'), 'episodes': episode_list}})
    return jsonify({'code': 500})

def start_server():
    app.run(host='127.0.0.1', port=5678, threaded=True)

if __name__ == '__main__':
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    webview.create_window('面包电影院', 'http://127.0.0.1:5678', width=1280, height=800, min_size=(1024, 768), background_color='#000000')
    webview.start()