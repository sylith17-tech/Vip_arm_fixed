import os
import yt_dlp
import logging
import uuid
import requests
from flask import Flask, render_template, request, jsonify, send_file, after_this_request, Response, stream_with_context
from flask_cors import CORS
from PIL import Image
from PIL.ExifTags import TAGS
# التوافق مع MoviePy 2.x
from moviepy import VideoFileClip
from moviepy.video import fx as vfx
from gtts import gTTS

# [CENTRAL_INTELLIGENCE_CORE] - NODE: Kernel-0x0
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [NODE_ID: Kernel-0x0] - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)

# إعداد المجلدات
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
STUDIO_FOLDER = os.path.join(os.getcwd(), 'studio_exports')
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

for folder in [DOWNLOAD_FOLDER, STUDIO_FOLDER, UPLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- وظائف مساعدة ---
def format_size(bytes):
    if not bytes: return "--"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024: return f"{bytes:.1f} {unit}"
        bytes /= 1024

def get_ydl_opts(custom_out=None):
    return {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': custom_out or os.path.join(DOWNLOAD_FOLDER, 'VIP_ARM_%(id)s.%(ext)s'),
        'nocheckcertificate': True,
        'quiet': True
    }

# --- ميزات المعالجة المتقدمة (AI & Video Core) ---
def create_shorts(input_path):
    output_path = input_path.replace(".mp4", "_SHORTS.mp4")
    with VideoFileClip(input_path) as video:
        duration = min(video.duration, 60)
        clip = video.subclip(0, duration)
        w, h = clip.size
        target_ratio = 9/16
        target_w = h * target_ratio
        final_clip = clip.fx(vfx.crop, x_center=w/2, width=target_w)
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    return output_path

def dub_video(input_path, lang='ar'):
    output_path = input_path.replace(".mp4", "_DUBBED.mp4")
    temp_audio = f"temp_{uuid.uuid4()}.mp3"
    with VideoFileClip(input_path) as video:
        tts = gTTS(text="تمت المعالجة بواسطة محرك VIP_ARM", lang=lang)
        tts.save(temp_audio)
        audio_clip = VideoFileClip(temp_audio).audio
        final_video = video.with_audio(audio_clip)
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    if os.path.exists(temp_audio): os.remove(temp_audio)
    return output_path

# --- [NEW] ميزة التحميل عبر البروكسي (حل مشكلة الفتح في تبويب جديد) ---
@app.route('/api/proxy_download')
def proxy_download():
    target_url = request.args.get('url')
    filename = request.args.get('filename', 'VIP_ARM_Capture.mp4')
    
    if not target_url:
        return "Target URL is missing", 400

    try:
        # نقوم بسحب البيانات كـ Stream لتوفير موارد السيرفر
        req = requests.get(target_url, stream=True, timeout=60, verify=False)
        
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                yield chunk

        return Response(
            stream_with_context(generate()),
            headers={
                "Content-Type": req.headers.get("Content-Type", "video/mp4"),
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Proxy Error: {str(e)}")
        return f"Kernel Error: {str(e)}", 500

# --- ميزة الفحص الأمني المطورة (Scanner Core) ---
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

        security_headers = [
            "Content-Security-Policy", "Strict-Transport-Security",
            "X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"
        ]

        results = {h: {"status": "✅ Found" if h in headers else "❌ Missing", "value": headers.get(h, "N/A")} for h in security_headers}

        return jsonify({
            "target": target_url,
            "status_code": response.status_code,
            "server": headers.get("Server", "Hidden"),
            "security_report": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- إدارة المسارات والرفع ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/studio')
def studio_page():
    return render_template('studio.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('image') or request.files.get('file')
    if not file: return jsonify({"error": "No Payload"}), 400

    filename = f"VIP_{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return jsonify({"status": "success", "url": f"/uploads/{filename}", "filename": filename})

@app.route('/<page>')
def serve_pages(page):
    if os.path.exists(page) and not page.endswith('.html'):
        return send_file(page)
    target = page if page.endswith('.html') else f"{page}.html"
    if os.path.exists(target): return render_template(target)
    return render_template('index.html'), 404

# --- API Endpoints ---
@app.route('/api/download', methods=['POST'])
@app.route('/api/process', methods=['POST'])
def unified_handler():
    data = request.json
    url = data.get('url')
    mode = data.get('mode')
    
    if not url: return jsonify({"status": "failed", "message": "No URL provided"}), 400

    try:
        if not mode:
            # وضع التحليل السريع (Extraction)
            with yt_dlp.YoutubeDL({'quiet': True, 'nocheckcertificate': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                # استخراج التنسيقات المباشرة
                formats = []
                for f in info.get('formats', []):
                    if f.get('url'):
                        formats.append({
                            "ext": f.get('ext'),
                            "resolution": f.get('resolution') or f.get('format_note'),
                            "filesize": format_size(f.get('filesize') or f.get('filesize_approx')),
                            # نرسل الرابط كـ Proxy لضمان التحميل القسري
                            "url": f.get('url'),
                            "proxy_url": f"/api/proxy_download?url={requests.utils.quote(f.get('url'))}&filename={requests.utils.quote(info.get('title', 'video'))}.{f.get('ext')}"
                        })
                
                return jsonify({
                    "status": "success", 
                    "title": info.get('title'), 
                    "thumbnail": info.get('thumbnail'), 
                    "uploader": info.get('uploader'),
                    "duration_string": info.get('duration_string'),
                    "formats": formats[::-1][:15] # إرسال آخر 15 تنسيق (الأعلى جودة غالباً)
                })
        else:
            # وضع المعالجة (Shorts / Dubbing)
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(url, download=True)
                raw_path = ydl.prepare_filename(info)

            final_path = create_shorts(raw_path) if mode == 'shorts' else dub_video(raw_path) if mode == 'dub' else raw_path

            @after_this_request
            def cleanup(response):
                try:
                    for f in {raw_path, final_path}:
                        if f and os.path.exists(f): os.remove(f)
                except: pass
                return response
            
            return send_file(final_path, as_attachment=True)
            
    except Exception as e:
        logger.error(f"Unified Handler Error: {str(e)}")
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route('/api/exif', methods=['POST'])
def forensic_core():
    file = request.files.get('image')
    if not file: return jsonify({"error": "No Image"}), 400
    try:
        img = Image.open(file)
        raw_exif = img._getexif()
        if not raw_exif: return jsonify({"status": "clear", "message": "Zero Metadata"})
        report = {TAGS.get(tid, tid): str(val) for tid, val in raw_exif.items() if not isinstance(val, bytes)}
        return jsonify({"status": "extracted", "forensic_data": report})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # تفعيل الـ Threaded للتعامل مع طلبات الـ Stream بفعالية
    app.run(host='0.0.0.0', port=port, threaded=True)
