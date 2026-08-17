import sys
import os
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize
from ui import MainWindow
from licensing.license_client import license_client
from licensing.auth_dialog import AuthDialog

def main():
    try:
        # Set Windows AppUserModelID so taskbar displays custom icon properly
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TalhaShaikh.DolaAIWatermarkRemover.2.0")
        except Exception:
            pass

        # Create the Qt Application
        app = QApplication(sys.argv)
        
        # Configure app metadata
        app.setApplicationName("Dola AI Watermark Remover by Talha Shaikh")
        app.setApplicationDisplayName("Dola AI Watermark Remover — Talha Shaikh")
        app.setOrganizationName("Talha Shaikh")
        app.setOrganizationDomain("talhashaikh.com")
        
        # Set High-Resolution Crisp Application & Window Icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
        if os.path.exists(icon_path):
            app_icon = QIcon()
            for sz in [16, 24, 32, 48, 64, 96, 128, 256]:
                app_icon.addFile(icon_path, QSize(sz, sz))
            if os.path.exists(png_path):
                app_icon.addFile(png_path, QSize(256, 256))
            app.setWindowIcon(app_icon)
        
        # Online License Verification on startup
        valid, msg, user_data = license_client.verify_current_session()
        
        if not valid:
            auth_dlg = AuthDialog(initial_message=msg if user_data else "")
            res = auth_dlg.exec()
            if res != QDialog.DialogCode.Accepted or not license_client.session_token:
                # User closed the auth dialog without activating
                sys.exit(0)
        
        # Create and display the main window in full screen (maximized) by default
        window = MainWindow()
        window.showMaximized()
        
        # Start the Qt event loop
        sys.exit(app.exec())
    except Exception as e:
        with open("crash_log.txt", "w") as f:
            f.write(f"Crash occurred: {str(e)}\n")
            traceback.print_exc(file=f)
        print(f"Exception during startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
