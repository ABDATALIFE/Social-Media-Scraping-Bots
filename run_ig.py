import subprocess

try:
    subprocess.run(
        ['.venv/Scripts/python.exe', 'smbots.py', 'ig', '--visible']
    )
except KeyboardInterrupt:
    pass
