# epaper-rp-controller-13.3-eink-spectra6e

**A beautiful web UI for the Waveshare 13.3inch E Ink Spectra 6 (E6) Full Color E-Paper Display, 1600×1200 pixels (RPi Zero or any Pi).**
Easily upload, convert, preview, and display images — with full admin and API control.

---

## 🚀 Features

* **🔒 Secure:** Login required for all access (single password, quick setup)
* **🖼️ Effortless image upload:** Drag & drop or file picker (PNG, JPG, BMP)
* **🎨 Palette support:** Custom `.act` color palettes — select, upload, delete (admin)
* **⚡ Instant preview:** See converted output before displaying
* **👑 Admin tools:** Palette management, raw buffer upload, separate admin login
* **🤖 API endpoint:** For automation and remote display
* **📱 Mobile-friendly:** Responsive Bootstrap 5 UI
* **⚠️ Custom errors and clear messages**

---

## 💾 Quick Install

1. **Download or clone the app folder** (e.g. `epaper_app/`) to your Raspberry Pi (or any Linux with Python 3.8+)

2. **Install dependencies** (recommended: virtual environment):

   ```bash
   cd epaper-rp-controller-13.3-eink-spectra6e
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set your passwords and keys** in `config.py`:

   ```python
   SECRET_KEY = "change_this"
   API_KEY = "your_api_key_here"
   ADMIN_PASSWORD = "your_admin_password_here"
   USER_PASSWORD = "your_user_password_here"
   ```

   *(Change all values!)*

4. **Palettes already included:**
   - Official `.act` color palettes for this display, downloaded from the [Waveshare wiki](https://www.waveshare.com/wiki/13.3inch_e-Paper_HAT%2B_(E)), are already in the `palettes/` folder.
   - You can add more or manage palettes any time via the Admin tab (after admin login).

5. **Run the server:**

   **A. To use standard web port 80 (so you can use [http://eink.local](http://eink.local)):**

   ```bash
   sudo python server.py
   ```

   *Port 80 requires sudo (root) on Linux. This lets you visit the app at [http://eink.local](http://eink.local) or [http://your-pi-ip](http://your-pi-ip).*

   - **Using `http://eink.local`:**  
   To access your Pi at `http://eink.local`, your Raspberry Pi's hostname **must be set to `eink`**.  
   You can set or change your Pi's hostname with `sudo raspi-config` → `System Options` → `Hostname`.  
   After changing, reboot your Pi.

   > 💡 `eink.local` works if your network supports mDNS/Bonjour (default on Windows, Mac, and most Linux).

   **B. If you prefer not to use sudo:**
   Edit the last line of `server.py` to use a port above 1024 (e.g., 5000):

   ```python
   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=5000, debug=True)
   ```

   Then start normally:

   ```bash
   python server.py
   ```

   And access it at [http://your-pi-ip:5000](http://your-pi-ip:5000)

6. **Open your browser:**

   - **See your Pi's IP on startup:**  
   The app prints your Raspberry Pi’s IP address and chosen port when starting, so you always know what address to open in your browser.
   * Visit [http://your-pi-ip:port](http://your-pi-ip:port)
   * Log in with your user password

---

## 🖥️ Usage

**Normal users:**

* Log in with your site password
* Upload or drag & drop an image
* Pick a palette and preview the e-paper result
* Click "Send to e-paper" to display

**Admins:**

* After user login, click "Admin login" to enter admin mode
* Upload/delete palette files (.act)
* Access raw buffer upload for advanced use

**API:**

* POST images to `/api/display` with your API key (see API Info tab for examples)

**Log out:**

* Use the "Log out" link at any time (top right)

---

## ⚙️ Tips & FAQ

* **Change or reset passwords:** Edit `config.py` and restart the server
* **Multiple users:** All share one password unless you add usernames (easy to extend)
* **Start at boot:** Use `tmux`, `screen`, or a simple `systemd` unit
* **Security:** Change ALL default credentials and API keys!

---

## 🆘 Troubleshooting

* **Virtualenv errors:** Always use a virtualenv for `pip install`, never `sudo pip install ...`
* **"No palettes found":** Upload a palette in Admin tab
* **Display/hardware issues:** Ensure the Waveshare drivers are installed, and wiring is correct

---

## 🤝 Contributing

Contributions are welcome!  
If you have ideas, bug fixes, improvements, or want to help with new features, feel free to open an issue or submit a pull request.

Whether it’s a typo fix, UI tweak, or something bigger—your help is appreciated!

---

## 🏷️ Credits & Attribution

* **Web UI & backend:** Jakub Karafa ([karafa.eu](https://karafa.eu))
* **E-paper driver:** Based on Waveshare’s official [Python code for 13.3" e-Paper HAT+ (E)](https://www.waveshare.com/wiki/13.3inch_e-Paper_HAT%2B_%28E%29)
* **Copyright:**

  * UI/backend © Jakub Karafa
  * Driver code © Waveshare Electronics (MIT license)
* **Tech stack:** Flask, Bootstrap 5, Pillow, Dropzone.js

---

## 📝 License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

For updates, see [karafa.eu](https://karafa.eu) or reach out to the author.
