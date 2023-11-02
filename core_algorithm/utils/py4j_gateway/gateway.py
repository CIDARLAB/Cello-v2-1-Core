import subprocess
import atexit
from config import BASE_DIR
import os

def start_gateway():
    cmd = [
        'java', 
        '-cp', 
        '.:jars/py4j.jar:./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src',
        'miniEugenePermuter'
    ]
    working_directory = os.path.join(BASE_DIR, 'core_algorithm', 'utils', 'py4j_gateway')
    
    # Redirect stdout and stderr to os.devnull to run in background
    with open(os.devnull, 'w') as fnull:
        process = subprocess.Popen(cmd, cwd=working_directory, stdout=fnull, stderr=fnull)

    atexit.register(lambda: process.terminate())
    return process
