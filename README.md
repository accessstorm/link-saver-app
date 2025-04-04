# 🖥️ Tkinter Desktop App

A lightweight Python desktop application built using **Tkinter**. This project includes a custom window icon and has been bundled into a standalone .exe file for easy distribution on Windows.

---

## ✨ Features
- ✅ Simple and clean GUI using tkinter
- 🖼️ Custom window icon (`.ico`)
- 💡 One-click executable (`.exe`) for Windows
- 🚫 No terminal window on launch

---

## 🚀 How to Run

### 🐍 Run from Python (Source Code)
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
python your_script.py
```

### 💾 Run the Executable (.exe)
1. Navigate to the `dist/` folder (after building).
2. Double-click `your_script.exe` to launch the app.

## 🛠️ Build Instructions (PyInstaller)
To build the app into a standalone `.exe`, use PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=your_icon.ico your_script.py
```

✅ Tip: Ensure `your_icon.ico` is in the same directory as your script.
If needed, include the icon manually:

```bash
pyinstaller --onefile --windowed --icon=your_icon.ico --add-data "your_icon.ico;." your_script.py
```

## 📁 File Structure
```
├── your_script.py
├── your_icon.ico
├── README.md
├── dist/
│   └── your_script.exe
```

## 🧠 Requirements
* Python 3.x
* Tkinter (usually included with Python)
* PyInstaller

```bash
pip install pyinstaller
```

## 📌 License
This project is open-source. Feel free to use and modify it.

Made with ❤️ using Python + Tkinter
