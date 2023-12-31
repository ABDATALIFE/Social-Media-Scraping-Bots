import subprocess

try:
    subprocess.run(
        ['.venv/Scripts/python.exe', 'smbots.py', 'fb', '--visible']
    )
except KeyboardInterrupt:
    pass
