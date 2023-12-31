import subprocess

try:
    subprocess.run(
        ['.venv/Scripts/python.exe', 'smbots.py', 'email', '--visible']
    )
except KeyboardInterrupt:
    pass
