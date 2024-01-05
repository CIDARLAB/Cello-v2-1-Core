from app.cli import start_cli
from core_algorithm.utils.py4j_gateway.gateway import start_gateway
from py4j.java_gateway import JavaGateway

if __name__ == '__main__':
    try:
        gateway = JavaGateway(eager_load=True)
        print("\nJava Py4J gateway already started")
    except Exception:
        print("\nAttempting to start Java Py4J gateway...")
        try:
            start_gateway()
            print("Started Java Py4J gateway")
        except Exception:
            print("Failed to start Java Py4J gateway!")
    start_cli()
