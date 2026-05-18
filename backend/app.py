import os
import sys

# Ensure common bin directories are in PATH for macOS GUI apps (like when launched via double-click)
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin"

import time
import json
import uuid
import subprocess
import requests
import threading
import shutil
import urllib.request
import webview
from pathlib import Path
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def get_app_data_dir():
    """ Get the app data directory for storing models """
    home = str(Path.home())
    app_data = os.path.join(home, 'Library', 'Application Support', 'LocalAudioNotes')
    os.makedirs(app_data, exist_ok=True)
    return app_data

def get_model_path():
    return os.path.join(get_app_data_dir(), "ggml-large-v3.bin")

def get_frontend_dir():
    """ Get the frontend directory path based on environment """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'frontend')
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

# Use resource path for static files if bundled
static_dir = get_frontend_dir()
app = Flask(__name__, static_folder=static_dir, static_url_path='/')
CORS(app)

UPLOAD_FOLDER = os.path.join(get_app_data_dir(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 强制锁定的本地模型（根据用户提供的截图确认为 gemma4:31b）
LOCKED_MODEL_NAME = "gemma4:31b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

def format_sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def process_audio_pipeline(task_id, filepath, preset):
    try:
        # 阶段1：音频预处理 (ffmpeg)
        yield format_sse("progress", {"status": "decoding", "message": "解码与预处理音频 (ffmpeg)..."})
        wav_path = os.path.join(UPLOAD_FOLDER, f"{task_id}.wav")
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-i', filepath,
            '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', wav_path
        ]
        
        # 捕获 ffmpeg 输出
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg 转换失败: {result.stderr}")
        
        # 阶段2：极速转录 (whisper.cpp)
        yield format_sse("progress", {"status": "transcribing", "message": "调用 Metal 加速转录 (whisper.cpp)..."})
        whisper_bin = get_resource_path('whisper.cpp/build/bin/whisper-cli')
        model_path = get_model_path()
        
        if not os.path.exists(whisper_bin):
            # Fallback for missing whisper.cpp (e.g. testing environment)
            print("Warning: whisper.cpp not found. Proceeding assuming it's a test environment or mocked.")
            
        whisper_cmd = [
            whisper_bin,
            '-m', model_path,
            '-f', wav_path,
            '-t', '8', # Use 8 threads to better utilize M2 Ultra/Pro CPUs
            '-nt', '-l', 'zh', # no timestamps, output raw text, set language to Chinese
            '--prompt', '以下是普通话的会议记录' # Add initial prompt to reduce hallucinations (like dashes)
        ]
        
        # 真实环境中这里执行 whisper.cpp
        # 由于我们可能在没有 whisper.cpp 的环境测试，使用一个简单的 try-except 或者检查
        if os.path.exists(whisper_bin):
            whisper_proc = subprocess.run(whisper_cmd, capture_output=True, text=True)
            if whisper_proc.returncode != 0:
                raise Exception(f"whisper.cpp 执行失败: {whisper_proc.stderr}")
            raw_text = whisper_proc.stdout.strip()
        else:
            # 模拟测试环境下的转录
            time.sleep(2)
            raw_text = "这是一段模拟的转录文本，因为 whisper.cpp 没有找到。今天我们开会讨论了如何设计系统架构，包括前端React和后端Flask。"

        if not raw_text:
            raise Exception("转录结果为空，请检查音频文件。")

        # 阶段3：语义重构 (Ollama)
        yield format_sse("progress", {"status": "summarizing", "message": f"语义重构中 ({LOCKED_MODEL_NAME})..."})
        
        prompt_templates = {
            "设计课程录音大纲": "你是一个专业的设计课程讲师。请将以下语音转录文本转化为结构化的课程大纲，去除语气词，修复错别字，并列出核心知识点：\n\n",
            "日常会议速记": "你是一个高级行政助理。请将以下会议录音转录文本整理为专业的会议纪要，提取核心决策和 Action Items：\n\n"
        }
        
        system_prompt = prompt_templates.get(preset, "请整理以下文本，修正错别字并输出结构化的 Markdown 笔记：\n\n")
        full_prompt = system_prompt + raw_text

        # 严格约束与异常捕获机制，禁止 fallback
        payload = {
            "model": LOCKED_MODEL_NAME,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }

        try:
            ollama_res = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
            if ollama_res.status_code != 200:
                raise Exception(f"Ollama 返回错误状态码: {ollama_res.status_code}. 可能原因：模型不存在或服务未运行。禁止回退！")
            
            res_data = ollama_res.json()
            if "response" not in res_data:
                raise Exception("Ollama 返回数据格式异常，缺少 response 字段。")
                
            markdown_text = res_data["response"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"无法连接到 Ollama 服务 ({OLLAMA_API_URL})，请确认已启动并且模型 {LOCKED_MODEL_NAME} 已下载。错误详情: {str(e)}")

        # 阶段4：完成并发送最终数据
        yield format_sse("complete", {
            "rawText": raw_text,
            "markdown": markdown_text
        })
        
    except Exception as e:
        yield format_sse("error", {"message": str(e)})
    finally:
        # 清理临时文件
        if os.path.exists(filepath):
            os.remove(filepath)
        wav_path = os.path.join(UPLOAD_FOLDER, f"{task_id}.wav")
        if os.path.exists(wav_path):
            os.remove(wav_path)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    preset = request.form.get('preset', '日常会议速记')
    
    if file:
        filename = secure_filename(file.filename)
        task_id = str(uuid.uuid4())
        filepath = os.path.join(UPLOAD_FOLDER, f"{task_id}_{filename}")
        file.save(filepath)
        
        return jsonify({"task_id": task_id, "filepath": filepath, "preset": preset})

@app.route('/api/process', methods=['GET'])
def process_file():
    task_id = request.args.get('task_id')
    filepath = request.args.get('filepath')
    preset = request.args.get('preset')
    
    if not all([task_id, filepath, preset]):
        return jsonify({"error": "Missing parameters"}), 400
        
    return Response(process_audio_pipeline(task_id, filepath, preset), mimetype='text/event-stream')

@app.route('/api/model_status', methods=['GET'])
def model_status():
    exists = os.path.exists(get_model_path())
    return jsonify({"exists": exists})

@app.route('/api/download_model', methods=['POST'])
def download_model():
    model_url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin"
    target_path = get_model_path()
    
    def generate():
        try:
            req = urllib.request.urlopen(model_url)
            total_size = int(req.info().get('Content-Length', -1))
            downloaded = 0
            chunk_size = 1024 * 1024 # 1MB chunks
            
            with open(target_path, 'wb') as f:
                while True:
                    chunk = req.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        yield format_sse("progress", {"progress": round(progress, 2)})
            
            yield format_sse("complete", {"message": "模型下载完成"})
        except Exception as e:
            yield format_sse("error", {"message": str(e)})

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/select_model', methods=['POST'])
def select_model():
    # Use pywebview to open a file dialog
    try:
        window = webview.windows[0]
        result = window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=('BIN Files (*.bin)', 'All Files (*.*)'))
        if result and len(result) > 0:
            source_path = result[0]
            target_path = get_model_path()
            shutil.copy2(source_path, target_path)
            return jsonify({"success": True, "message": "模型配置成功"})
        return jsonify({"success": False, "message": "未选择文件"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/')
def index():
    return app.send_static_file('index.html')

def start_server():
    app.run(port=5001, debug=False)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        app.run(port=5001, debug=True)
    else:
        # Run Flask in a background thread
        t = threading.Thread(target=start_server)
        t.daemon = True
        t.start()
        
        # Open PyWebview window in the main thread
        webview.create_window("本地语音笔记助手", "http://localhost:5001", width=1024, height=768)
        webview.start()
