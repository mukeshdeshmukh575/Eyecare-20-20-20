# Eyecare Tray Application 👁️

A premium, modern Windows system tray application designed to enforce the **20-20-20 eye care rule**: *every 20 minutes, look at something 20 feet away for 20 seconds.*

This application operates quietly in the background, minimizing eye strain by overlaying a calming, glassmorphic eye-rest dashboard when your timer is up. It comes complete with customization settings, daily break completion metrics, calming exercises, and native Windows integration.

---

## Key Features

- **System Tray Operation**: Stays out of your way in the Windows Taskbar status area. Double-click the tray icon to open the settings/stats window.
- **Glassmorphic Break Overlay**: When the 20-minute mark is reached, a beautiful, semi-transparent fullscreen backdrop appears with a customized circular countdown timer and eye-relaxation tips.
- **Dynamic Tray Icon**: Changes color dynamically based on state:
  - **Teal / Green**: Active monitoring.
  - **Slate Gray**: Reminders are paused.
  - **Blue**: Break in progress.
- **Audio Prompts**: Low-latency, non-intrusive sound signals using native Windows audio system chimes at the start and completion of a break.
- **Snooze & Skip Options**: Respects your productivity with a 5-minute snooze or immediate break skip for critical tasks.
- **Autostart with Windows**: Optional setting to automatically register the program in the Windows registry to start up when you turn on your PC.
- **Breaks Statistics**: Tracks your daily progress (e.g. how many breaks you have completed today and total time rested).

---

## Installation & Setup

1. **Verify Python is installed** (Python 3.10+ recommended):
   ```bash
   python --version
   ```

2. **Install Required Libraries**:
   ```bash
   pip install PyQt6 Pillow
   ```

3. **Run the Application**:
   ```bash
   pythonw main.py
   ```
   *Note: Using `pythonw` runs the script silently in the background without launching a command prompt window.*

---

## Compiling to a Standalone Executable (.exe)

To run the application natively without needing to open a Python environment, you can compile it into a single, optimized executable using **PyInstaller**.

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Compile the application:
   ```bash
   pyinstaller --noconsole --onefile --icon=NONE --name=Eyecare main.py
   ```
   - `--noconsole`: Hides the command line window.
   - `--onefile`: Bundles everything into a single `.exe` file.
   - `--name=Eyecare`: Sets the output binary name.

3. The compiled `.exe` file will be generated in the `dist` folder. You can copy it anywhere (e.g., your Desktop or Startup folder) and double-click it to run.

---

## Custom Styles & Design System

The application is styled with a sleek dark aesthetic (based on the popular **Catppuccin Mocha** palette):
- **Primary Background**: Dark slate `#0f172a` (Slate 900)
- **Secondary Cards**: Deep slate `#1e293b` (Slate 800)
- **Active Accents**: Teal `#2dd4bf` (Teal 400)
- **Secondary Accents**: Blue `#3b82f6` (Blue 500)
- **Muted Elements**: Gray `#64748b` (Slate 500)
- **Typography**: Clean system-ui `Segoe UI` fonts with custom font weights and line heights.
