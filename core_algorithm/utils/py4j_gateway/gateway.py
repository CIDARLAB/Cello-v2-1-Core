import subprocess
import atexit
import os

from config import BASE_DIR


def start_gateway():
    # External command to compile miniEugenePermuter class:
    #     javac -cp '.:py4j.jar:.:miniEugene-core-1.0.0-jar-with-dependencies.jar' miniEugenePermuter.java   // mac / lin
    #     javac -cp .;py4j.jar;.;miniEugene-core-1.0.0-jar-with-dependencies.jar miniEugenePermuter.java     // win
    # External command to execute program to instantiate Py4J Java Gateway:
    #     java -cp '.:py4j.jar:.:miniEugene-core-1.0.0-jar-with-dependencies.jar./src' miniEugenePermuter    // mac / lin
    #     java -cp .;py4j.jar;.;miniEugene-core-1.0.0-jar-with-dependencies.jar./src miniEugenePermuter      // win

    if os.name == 'nt':
        cmd = [
            'java',
            '-cp',
            '.;jars/py4j.jar;./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src',
            'miniEugenePermuter'
        ]
    else:
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
