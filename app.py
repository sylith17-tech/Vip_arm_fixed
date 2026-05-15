# --- [KERNEL_INIT] ---
from gevent import monkey
monkey.patch_all()  # السطر الأهم: يجب أن يسبق كافة الاستيرادات لضمان عمل الـ WebSockets

import os
import yt_dlp
import logging
import uuid
import requests
import asyncio
from flask_socketio import SocketIO, emit, join_room
from flask import Flask, render_template, request, jsonify, send_file, after_this_request, Response, stream_with_context
from flask_cors import CORS
from PIL import Image
from PIL.ExifTags import TAGS
from gtts import gTTS

# --- [DYNAMIC_LIBRARY_LOADER] ---
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
    from moviepy.video import fx as vfx
except ImportError:
    try:
        import moviepy.editor as mp
        VideoFileClip = mp.VideoFileClip
        AudioFileClip = mp.AudioFileClip
        vfx = mp.vfx
    except Exception:
        try:
            from moviepy.video.io.VideoFileClip import VideoFileClip
            from moviepy.audio.io.AudioFileClip import AudioFileClip
            import moviepy.video.fx as vfx
        except Exception as e:
            print(f"CRITICAL: MoviePy Load Failed: {e}")

# --- [CENTRAL_INTELLIGENCE_CORE] - NODE: Kernel-0x0 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [NODE_ID: Kernel-0x0] - %(message)s'
)
logger = logging.getLogger(__name__)
import sqlite3

def init_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, user TEXT, msg TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

init_db()


app = Flask(__name__, template_folder='.', static_folder='.')
app.config['SECRET_KEY'] = 'VIP_ARM_SECURE_KEY_0x0'
CORS(app)

# إعداد SocketIO المطور لضمان وصول الرسائل للطرفين في بيئة Render
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='gevent', 
    ping_timeout=60,      # زيادة المهلة لضمان استقرار النفق
    ping_interval=25,
    manage_session=False,
    logger=True,           # تفعيل السجلات لتتبع تدفق الرسائل
    engineio_logger=True
)

# إعداد المسارات الأساسية للنظام
BASE_DIR = os.getcwd()
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
STUDIO_FOLDER = os.path.join(BASE_DIR, 'studio_exports')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

for folder in [DOWNLOAD_FOLDER, STUDIO_FOLDER, UPLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

# --- [UTILITY_FUNCTIONS] ---
def format_size(bytes_num):
    if not bytes_num:
        return "--"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_num < 1024:
            return f"{bytes_num:.1f} {unit}"
    if bytes_num > 0: bytes_num /= 1024
    return "0 B"

def get_ydl_opts(custom_out=None):
    return {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': custom_out or os.path.join(DOWNLOAD_FOLDER, 'VIP_ARM_%(id)s.%(ext)s'),
        'nocheckcertificate': True,
        'quiet': True,
        'merge_output_format': 'mp4'
    }

# --- [ADVANCED_VIDEO_ENGINE] ---
def create_shorts(input_path):
    output_path = input_path.replace(".mp4", "_SHORTS.mp4")
    try:
        with VideoFileClip(input_path) as video:
            duration = min(video.duration, 60)
            clip = video.subclip(0, duration)
            w, h = clip.size
            target_ratio = 9/16
            target_w = h * target_ratio
            final_clip = vfx.crop(clip, x_center=w/2, width=target_w)
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        return output_path
    except Exception as e:
        logger.error(f"Shorts Creation Failed: {e}")
        return input_path

def dub_video(input_path, lang='ar'):
    output_path = input_path.replace(".mp4", "_DUBBED.mp4")
    temp_audio = os.path.join(UPLOAD_FOLDER, f"temp_{uuid.uuid4()}.mp3")
    try:
        with VideoFileClip(input_path) as video:
            tts = gTTS(text="تمت المعالجة بواسطة محرك VIP_ARM", lang=lang)
            tts.save(temp_audio)
            audio_clip = AudioFileClip(temp_audio)
            final_video = video.set_audio(audio_clip)
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        return output_path
    except Exception as e:
        logger.error(f"Dubbing Failed: {e}")
        return input_path
    finally:
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

# --- [SOCKET_IO_COMMUNICATION - FIXED FOR MULTIPLAYER] ---
@socketio.on('join')
def on_join(data):
    try:
        conn = sqlite3.connect("chat.db")
        c = conn.cursor()
        c.execute("SELECT user, msg FROM messages WHERE room = ? ORDER BY timestamp DESC LIMIT 50", (data.get("room"),))
        history = c.fetchall()[::-1]
        conn.close()
        for user, msg in history:
            emit("message", {"user": user, "msg": msg}, room=request.sid)
    except Exception as e:
        print(f"History Error: {e}")
    room = data.get('room', 'global')
    user = data.get('user', 'Unknown')
    join_room(room)
    logger.info(f"SIGNAL: Node {user} synchronized with Tunnel {room}")
    emit('status', {'msg': f'Node {user} is online'}, room=room)

@socketio.on('message')
def handle_message(data):
    try:
        conn = sqlite3.connect("chat.db")
        c = conn.cursor()
        c.execute("INSERT INTO messages (room, user, msg) VALUES (?, ?, ?)", (data.get("room"), data.get("user"), data.get("msg")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
    # تم دمج إصلاح البث لضمان وصول الرسالة لجميع الأطراف في الغرفة
    room = data.get('room', 'global')
    logger.info(f"ROUTING: Encrypted signal received in Tunnel {room}")
    emit('message', data, room=room, broadcast=True, include_self=False)

# --- [ROUTES] ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/studio')
def studio_page():
    return render_template('studio.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

@app.route('/api/proxy_download')
def proxy_download():
    target_url = request.args.get('url')
    filename = request.args.get('filename', 'VIP_ARM_Capture.mp4')
    if not target_url:
        return "Target URL is missing", 400
    try:
        req = requests.get(target_url, stream=True, timeout=60, verify=False)
        return Response(
            stream_with_context(req.iter_content(chunk_size=8192)),
            headers={
                "Content-Type": req.headers.get("Content-Type", "video/mp4"),
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        return f"Kernel Error: {str(e)}", 500

@app.route('/api/scan', methods=['POST'])
def web_scanner():
    data = request.json
    target_url = data.get('url')
    if not target_url:
        return jsonify({"error": "Missing Target URL"}), 400
    try:
        if not target_url.startswith('http'):
            target_url = 'https://' + target_url
        response = requests.get(target_url, timeout=10, verify=True)
        headers = response.headers
        security_headers = ["Content-Security-Policy", "Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
        results = {h: {"status": "✅ Found" if h in headers else "❌ Missing", "value": headers.get(h, "N/A")} for h in security_headers}
        return jsonify({"target": target_url, "status_code": response.status_code, "server": headers.get("Server", "Hidden"), "security_report": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('image') or request.files.get('file')
    if not file:
        return jsonify({"error": "No Payload"}), 400
    filename = f"VIP_{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return jsonify({"status": "success", "url": f"/uploads/{filename}", "filename": filename})

@app.route('/api/download', methods=['POST'])
@app.route('/api/process', methods=['POST'])
def unified_handler():
    data = request.json
    url = data.get('url')
    mode = data.get('mode')
    if not url:
        return jsonify({"status": "failed", "message": "No URL provided"}), 400
    try:
        if not mode:
            ydl_opts_info = {'quiet': True, 'nocheckcertificate': True}
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = []
                for f in info.get('formats', []):
                    if f.get('url') and f.get('vcodec') != 'none':
                        formats.append({
                            "ext": f.get('ext'),
                            "resolution": f.get('resolution') or f.get('format_note'),
                            "filesize": format_size(f.get('filesize') or f.get('filesize_approx')),
                            "url": f.get('url'),
                            "proxy_url": f"/api/proxy_download?url={requests.utils.quote(f.get('url'))}&filename={requests.utils.quote(info.get('title', 'video'))}.{f.get('ext')}"
                        })
                return jsonify({"status": "success", "title": info.get('title'), "thumbnail": info.get('thumbnail'), "formats": formats[::-1]})
        else:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(url, download=True)
                raw_path = ydl.prepare_filename(info)
                if not os.path.exists(raw_path):
                    raw_path = os.path.splitext(raw_path)[0] + ".mp4"

            final_path = create_shorts(raw_path) if mode == 'shorts' else dub_video(raw_path) if mode == 'dub' else raw_path

            @after_this_request
            def cleanup(response):
                try:
                    for f in {raw_path, final_path}:
                        if f and os.path.exists(f):
                            os.remove(f)
                except: pass
                return response
            return send_file(final_path, as_attachment=True)
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route('/api/exif', methods=['POST'])
def forensic_core():
    file = request.files.get('image')
    if not file:
        return jsonify({"error": "No Image"}), 400
    try:
        img = Image.open(file)
        raw_exif = img._getexif()
        if not raw_exif:
            return jsonify({"status": "clear", "message": "Zero Metadata"})
        report = {TAGS.get(tid, tid): str(val) for tid, val in raw_exif.items() if not isinstance(val, bytes)}
        return jsonify({"status": "extracted", "forensic_data": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/<page>')
def serve_pages(page):
    if page.startswith('uploads/'):
        return send_file(page)
    if os.path.exists(page) and not page.endswith('.html'):
        return send_file(page)
    target = page if page.endswith('.html') else f"{page}.html"
    if os.path.exists(target):
        return render_template(target)
    return render_template('index.html'), 404

# --- [START_SERVER] ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
else:
    # لضمان توافق خادم Gunicorn في بيئة Render السحابية
    application = app
