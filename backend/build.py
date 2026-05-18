import os
import sys
import subprocess
import shutil

def build_app():
    print("Starting PyInstaller build...")
    
    # Check if pyinstaller is installed
    try:
        import PyInstaller.__main__
    except ImportError:
        print("Error: PyInstaller is not installed. Please run `pip install pyinstaller pywebview`.")
        sys.exit(1)

    # Define paths
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.abspath(os.path.join(backend_dir, '../frontend'))
    whisper_dir = os.path.join(backend_dir, 'whisper.cpp', 'build', 'bin')
    
    # Files to include
    add_data_args = [
        f'--add-data={frontend_dir}:frontend',
    ]

    # Include whisper-cli if exists
    whisper_cli = os.path.join(whisper_dir, 'whisper-cli')
    if os.path.exists(whisper_cli):
        add_data_args.append(f'--add-data={whisper_cli}:whisper.cpp/build/bin')
    else:
        print(f"Warning: whisper-cli not found at {whisper_cli}. It won't be bundled.")

    # Try to find ffmpeg in system if not explicitly bundled
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        # Note: Depending on licensing, you might want to bundle a static ffmpeg.
        # For this script, we just assume the user has it in PATH or we bundle the local one if present.
        # To bundle, we would uncomment:
        # add_data_args.append(f'--add-data={ffmpeg_path}:.')
        pass

    # PyInstaller command arguments
    pyinstaller_args = [
        'app.py',
        '--name=AudioNotes',
        '--windowed',        # No console window (macOS .app format)
        '--noconfirm',       # Overwrite existing build
        '--clean',           # Clean cache
    ] + add_data_args

    # Check for icon
    icon_path = os.path.join(backend_dir, 'app_icon.icns')
    if os.path.exists(icon_path):
        pyinstaller_args.append(f'--icon={icon_path}')

    print("Running PyInstaller with args:", " ".join(pyinstaller_args))
    PyInstaller.__main__.run(pyinstaller_args)
    
    print("\nBuild complete! The application is located in the 'dist/AudioNotes.app' directory.")

if __name__ == '__main__':
    build_app()
