import subprocess
import atexit
import os

from config import BASE_DIR


def start_gateway():
    """
    Compilation:
      javac -cp .:jars/py4j.jar:.:jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src src/miniEugenePermuter.java
      javac -cp .;jars/py4j.jar;.;jars/miniEugene-core-1.0.0-jar-with-dependencies.jar;./src src/miniEugenePermuter.java
    Execution:
      java -cp .:jars/py4j.jar:./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src miniEugenePermuter // mac
      java -cp .;jars/py4j.jar;./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar;./src miniEugenePermuter // win

    :return: Popen subprocess
    """

    working_directory = os.path.join(BASE_DIR, 'core_algorithm', 'utils', 'py4j_gateway')

    if os.name == 'posix':
        cmd = [
            'java',
            '-cp',
            '.:jars/py4j.jar:./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src',
            'miniEugenePermuter'
        ]
        # Redirect stdout and stderr to os.devnull to run in background
        with open(os.devnull, 'w') as fnull:
            process = subprocess.Popen(cmd, cwd=working_directory, stdout=fnull, stderr=fnull)
    elif os.name == 'nt':
        cmd = [
            'java',
            '-cp',
            ';jars/py4j.jar;./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar;./src',
            'miniEugenePermuter'
        ]
        # Redirect stdout and stderr to os.devnull to run in background
        with open(os.devnull, 'w') as fnull:
            process = subprocess.Popen(cmd, cwd=working_directory, stdout=fnull, stderr=fnull, shell=True)

    atexit.register(lambda: process.terminate())
    return process


def terminate_gateway(process) -> None:
    if process.poll() is None:
        process.terminate()
        process.wait()

    return None
