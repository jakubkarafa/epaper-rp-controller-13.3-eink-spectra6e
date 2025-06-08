# =============================================================================
#  File        :   server.py
#  Author      :   Jakub Karafa (UI/backend)
#                 + Waveshare Electronics (hardware driver)
#  Function    :   E-paper web controller with hardware interface
#  Info        :   Web UI for 13.3" e-Paper HAT+ (E)
# -----------------------------------------------------------------------------
#  This version:   custom
#  Date        :   2025-06-08
#  Based on    :   Waveshare sample code
#                  (see: https://www.waveshare.com/wiki/13.3inch_e-Paper_HAT%2B_(E))
# =============================================================================
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
# =============================================================================
import os
import sys
import uuid
import time
import socket
import logging
import traceback
from functools import wraps
from flask import (Flask, request, render_template, send_file, redirect, url_for,
                   flash, session, abort, jsonify)
from PIL import Image
from functools import wraps
from config import SECRET_KEY, API_KEY, ADMIN_PASSWORD, USER_PASSWORD

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PALETTE_FOLDER = os.path.join(BASE_DIR, "palettes")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PALETTE_FOLDER, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

try:
    from config import SECRET_KEY, API_KEY, ADMIN_PASSWORD
except ImportError:
    SECRET_KEY = os.environ.get("EPAPER_SECRET_KEY", os.urandom(32))
    API_KEY = os.environ.get("EPAPER_API_KEY", "changeme123")
    ADMIN_PASSWORD = os.environ.get("EPAPER_ADMIN_PASS", "admin123")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

LOG_FILE = os.path.join(LOG_DIR, "epaper.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]")

libdir = os.path.join(BASE_DIR, 'lib')
if os.path.exists(libdir): sys.path.append(libdir)
try:
    import epd13in3E
except Exception as e:
    epd13in3E = None
    logging.error("E-paper driver not loaded: " + str(e))

def user_logged_in():
    return session.get("user_logged_in", False)

def require_site_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Always allow access to the login/logout pages and static files
        allowed = (
            request.endpoint in ['site_login', 'site_logout', 'static'] or
            request.path.startswith('/static/') or
            (request.endpoint or '').startswith('static')
        )
        if not user_logged_in() and not allowed:
            return redirect(url_for("site_login", next=request.url))
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename, exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in exts

def get_user_prefix():
    if 'uid' not in session:
        session['uid'] = uuid.uuid4().hex
    return session['uid']

def session_file(suffix):
    return os.path.join(UPLOAD_FOLDER, f"{get_user_prefix()}{suffix}")

def cleanup_uploads(keep_last_n=20):
    files = [os.path.join(UPLOAD_FOLDER, f)
             for f in os.listdir(UPLOAD_FOLDER)
             if f.endswith(('.bin', '.png'))]
    files = sorted(files, key=os.path.getctime, reverse=True)
    for f in files[keep_last_n:]:
        try:
            os.remove(f)
        except Exception as e:
            logging.error(f"Failed to remove {f}: {e}")

def list_palettes():
    return sorted([f for f in os.listdir(PALETTE_FOLDER) if f.endswith('.act')])

def safe_palette_filename(fname):
    fname = os.path.basename(fname)
    if not fname.endswith('.act'):
        raise ValueError("Palette file must end with .act")
    path = os.path.join(PALETTE_FOLDER, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Palette {fname} not found.")
    return path

def load_act_palette(path):
    try:
        with open(path, "rb") as f:
            act = f.read()
        palette_data = act[:768]
        palette_data = palette_data + bytes([0] * (768 - len(palette_data)))
        return list(palette_data), None
    except Exception as e:
        return None, f"Failed to load palette: {e}"

def pack_indices_for_epaper(indices):
    if len(indices) % 2 == 1:
        indices += bytes([0])
    packed = bytearray()
    for i in range(0, len(indices), 2):
        hi = indices[i] & 0x0F
        lo = indices[i+1] & 0x0F
        packed.append((hi << 4) | lo)
    return packed

def safe_open_image(file_storage):
    try:
        img = Image.open(file_storage)
        img.verify()
        file_storage.seek(0)
        return Image.open(file_storage)
    except Exception:
        raise ValueError("Uploaded file is not a valid image.")

def convert_image_with_palette(img_file, palette_bytes, buf_path, preview_path):
    img = safe_open_image(img_file)
    img = img.convert("RGB").resize((1200, 1600))
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_bytes)
    quant_img = img.quantize(palette=pal_img, dither=Image.FLOYDSTEINBERG)
    quant_img.save(preview_path, format="PNG")
    indices = quant_img.tobytes()
    buf = pack_indices_for_epaper(indices)
    with open(buf_path, "wb") as f:
        f.write(buf)
    return preview_path

def display_on_epaper(buffer_bin):
    if not epd13in3E:
        return False, "E-paper driver not loaded."
    if not os.path.exists(buffer_bin):
        return False, "Buffer not found"
    try:
        with open(buffer_bin, "rb") as f:
            data = f.read()
        epd = epd13in3E.EPD()
        epd.Init()
        epd.Clear(0x1)
        epd.display(data)
        epd.sleep()
        return True, "OK"
    except Exception as e:
        logging.error(str(e))
        return False, f"Failed: {e}"

from functools import wraps
def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged"):
            flash("Admin login required.", "danger")
            return redirect(url_for("admin_login", next=request.url))
        return fn(*args, **kwargs)
    return wrapped

@app.before_request
def global_protect():
    # Don't block static files or login page itself
    if request.endpoint in ['site_login', 'site_logout', 'static']:
        return
    if not user_logged_in():
        return redirect(url_for("site_login", next=request.url))

@app.route("/login", methods=["GET", "POST"])
def site_login():
    next_url = request.args.get("next") or url_for("index")
    if user_logged_in():
        return redirect(next_url)
    error = None
    if request.method == "POST":
        if request.form.get("password") == USER_PASSWORD:
            session["user_logged_in"] = True
            flash("Logged in!", "success")
            return redirect(next_url)
        else:
            error = "Incorrect password."
    return render_template("site_login.html", error=error, next=next_url)

@app.route("/logout")
def site_logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("site_login"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    next_url = request.args.get("next") or url_for("index")
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == ADMIN_PASSWORD:
            session["admin_logged"] = True
            flash("Admin login successful!", "success")
            return redirect(next_url)
        else:
            flash("Wrong password.", "danger")
    return render_template("admin_login.html", next=next_url)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))

@app.route("/", methods=["GET"])
def index():
    tab = request.args.get("tab", "convert")
    palettes = list_palettes()
    selected_palette = palettes[0] if palettes else ""
    preview_url = None
    buf_download = None

    preview_png = session_file(".png")
    buffer_bin = session_file(".bin")
    if os.path.exists(preview_png):
        preview_url = url_for('preview_png', filename=os.path.basename(preview_png), t=int(time.time()))
    if os.path.exists(buffer_bin):
        buf_download = url_for("download_buf", filename=os.path.basename(buffer_bin))

    cleanup_uploads()

    return render_template("epaper.html",
        palettes=palettes,
        selected_palette=selected_palette,
        preview_url=preview_url,
        buf_download=buf_download,
        tab=tab,
        is_admin=session.get("admin_logged", False)
    )

@app.route("/convert", methods=["POST"])
def convert_post():
    try:
        img_file = request.files.get("img")
        palette_name = request.form.get("palette")
        if not img_file or not allowed_file(img_file.filename, {"png", "jpg", "jpeg", "bmp"}):
            flash("No valid image selected.", "danger")
            return redirect(url_for("index", tab="convert"))
        if not palette_name or palette_name not in list_palettes():
            flash("Invalid or missing palette selected.", "danger")
            return redirect(url_for("index", tab="convert"))
        palette_path = safe_palette_filename(palette_name)
        palette_bytes, palette_err = load_act_palette(palette_path)
        if palette_err:
            flash(palette_err, "danger")
            return redirect(url_for("index", tab="convert"))

        preview_png = session_file(".png")
        buffer_bin = session_file(".bin")
        convert_image_with_palette(img_file, palette_bytes, buffer_bin, preview_png)
        flash("✅ Image converted! Preview below. Click send to display.", "success")
    except Exception as e:
        flash(f"Failed to process image: {e}", "danger")
        logging.error(str(e))
    return redirect(url_for("index", tab="convert"))

@app.route("/display", methods=["POST"])
def display_post():
    try:
        buffer_bin = session_file(".bin")
        if not os.path.exists(buffer_bin):
            flash("No converted buffer available. Convert image first.", "danger")
            return redirect(url_for("index", tab="convert"))
        ok, msg = display_on_epaper(buffer_bin)
        if ok:
            flash("✅ Image sent to e-paper!", "success")
        else:
            flash(f"⚠️ Failed to send: {msg}", "danger")
    except Exception as e:
        flash(f"Internal error: {e}", "danger")
        logging.error(str(e))
    return redirect(url_for("index", tab="convert"))

@app.route("/raw_upload", methods=["POST"])
@admin_required
def raw_upload():
    try:
        rawfile = request.files.get("bin")
        fname = rawfile.filename if rawfile else ""
        if not rawfile or not allowed_file(fname, {"bin"}):
            flash("Only .bin files are accepted for raw upload. Choose another file.", "danger")
            return redirect(url_for("index", tab="raw"))
        buffer_bin = session_file(".bin")
        rawfile.save(buffer_bin)
        ok, msg = display_on_epaper(buffer_bin)
        if ok:
            flash("✅ Raw buffer displayed on e-paper!", "success")
        else:
            flash(f"⚠️ Failed to display raw: {msg}", "danger")
    except Exception as e:
        flash(f"Internal error: {e}", "danger")
        logging.error(str(e))
    return redirect(url_for("index", tab="raw"))

@app.route("/palette/upload", methods=["POST"])
@admin_required
def upload_palette():
    pal = request.files.get("palette")
    if not pal or not allowed_file(pal.filename, {"act"}):
        flash("Upload a .act palette file.", "danger")
        return redirect(url_for("index", tab="convert"))
    dst = os.path.join(PALETTE_FOLDER, os.path.basename(pal.filename))
    pal.save(dst)
    flash(f"Palette {pal.filename} uploaded.", "success")
    return redirect(url_for("index", tab="convert"))

@app.route("/palette/delete/<palette>")
@admin_required
def delete_palette(palette):
    try:
        fullpath = safe_palette_filename(palette)
        os.remove(fullpath)
        flash(f"Deleted palette: {palette}", "success")
    except Exception as e:
        flash(f"Failed to delete: {e}", "danger")
    return redirect(url_for("index", tab="convert"))

@app.route("/preview/<filename>")
def preview_png(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return "Preview not found", 404

@app.route("/download/<filename>")
@admin_required
def download_buf(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path) and filename.endswith('.bin'):
        return send_file(path, as_attachment=True)
    return "File not found", 404

@app.route("/upload_image", methods=["POST"])
def upload_image():
    try:
        img_file = request.files.get("file")
        palette_name = request.form.get("palette")
        if not img_file or not allowed_file(img_file.filename, {"png", "jpg", "jpeg", "bmp"}):
            return jsonify({"error": "No valid image."}), 400
        if not palette_name or palette_name not in list_palettes():
            return jsonify({"error": "Invalid palette."}), 400
        palette_path = safe_palette_filename(palette_name)
        palette_bytes, palette_err = load_act_palette(palette_path)
        if palette_err:
            return jsonify({"error": palette_err}), 400

        preview_png = session_file(".png")
        buffer_bin = session_file(".bin")
        convert_image_with_palette(img_file, palette_bytes, buffer_bin, preview_png)
        return jsonify({"success": True})
    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/api/display", methods=["POST"])
def api_display():
    api_token = request.headers.get("X-API-Key")
    if api_token != API_KEY:
        return {"ok": False, "error": "Unauthorized"}, 401

    img_file = request.files.get("img")
    palette_name = request.form.get("palette", None)
    palettes = list_palettes()
    palette_file = palette_name if palette_name in palettes else (palettes[0] if palettes else None)
    if not img_file or not palette_file:
        return {"ok": False, "error": "Missing image or palette."}, 400
    palette_bytes, palette_err = load_act_palette(os.path.join(PALETTE_FOLDER, palette_file))
    if palette_err:
        return {"ok": False, "error": palette_err}, 400
    try:
        preview_png = session_file(".png")
        buffer_bin = session_file(".bin")
        convert_image_with_palette(img_file, palette_bytes, buffer_bin, preview_png)
        ok, msg = display_on_epaper(buffer_bin)
        if ok:
            return {"ok": True, "msg": "Image displayed!"}
        else:
            return {"ok": False, "error": msg}, 500
    except Exception as e:
        logging.error(str(e))
        return {"ok": False, "error": str(e)}, 500

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", msg="Not found."), 404

@app.errorhandler(413)
def too_large(e):
    return render_template("error.html", msg="File too large. Max 5MB."), 413

@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", msg="Internal server error."), 500

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = 'localhost'
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 80  # or 5000 if not using sudo/port 80
    ip = get_ip()
    hostname = socket.gethostname()
    print(f"\nServer running at: http://{ip}:{port}")
    print(f"Or, if you set your Pi's hostname to 'eink': http://eink.local\n")
    app.run(host=host, port=port, debug=True)
