"""
Uses Py4J to invoke a Java program in an already running JVM to interface with the eugene.jar to run the eugene script.
The script runs Eugene's permute function, which generates all valid part orders based on the UCF rules.
These part orders are then used for SBOL and other file generation.
TODO: Ensure JVM properly started on Docker.
"""

# import subprocess
import log
import logging


def call_mini_eugene(rules: list[str], part_count: int, orders_count: int = 5):
    """
    NOTE: Commands to be executed before the Python script...
    External command to compile miniEugenePermuter class:
        javac -cp .;py4j.jar;.;miniEugene-core-1.0.0-jar-with-dependencies.jar miniEugenePermuter.java
    External command to execute program to instantiate Py4J Java Gateway:
        java -cp .;py4j.jar;.;miniEugene-core-1.0.0-jar-with-dependencies.jar miniEugenePermuter

    :param rules:
    :param part_count:
    :param orders_count:
    """

    from py4j.java_gateway import JavaGateway, GatewayParameters
    logging.getLogger("py4j").setLevel(logging.INFO)  # Suppress (useless) console output
    # from py4j.java_collections import ListConverter

    # TODO: Call JVM/Java program from this script...
    # application = "C:\\Program Files\\Java\\jdk-20\\bin\\javac.exe"
    # # application = "C:\\Users\\Chris\\OneDrive\\VS-Code\\CELLO\\Cell-v3-Fork\\Cello-v3-Core\\utils"
    # subprocess.run([application, "-cp .\\py4j.jar;.\\miniEugene-core-1.0.0-jar-with-dependencies.jar "
    #                              "AdditionApplication.java"])
    # application = "C:\\Program Files\\Java\\jdk-20\\bin\\java.exe"
    # subprocess.run([application, "-cp .\\py4j.jar;.\\miniEugene-core-1.0.0-jar-with-dependencies.jar "
    #                              "AdditionApplication"])
    # subprocess.run("java -cp .;py4j.jar;.;miniEugene-core-1.0.0-jar-with-dependencies.jar AdditionApplication")
    # gateway = JavaGateway(gateway_parameters=GatewayParameters(auto_convert=True)).launch_gateway(
    #                       jarpath="./py4j.jar", classpath="./miniEugene-core-1.0.0-jar-with-dependencies.jar")

    # Connect to JVM and setup to convert to Java-friendly containers
    gateway = JavaGateway(gateway_parameters=GatewayParameters(auto_convert=True))
    miniEugeneInstance = gateway.entry_point

    rules = ['CONTAINS Gate3_a', 'CONTAINS Gate1_a', 'CONTAINS Gate5_a', 'CONTAINS Gate5_b',
             'CONTAINS nanoluc_reporter_a', 'ALL_FORWARD', 'STARTSWITH L1', 'ENDSWITH L2', 'Gate5_a AFTER Gate3_a',
             'Gate5_a AFTER Gate1_a', 'Gate3_a AFTER Gate1_a']
    # java_rules = ListConverter().convert(rules, addition_app._gateway_client)  # convert to Java container explicitly
    # gateway.jvm.java.util.Collections.sort(java_rules)

    # Call the miniPermute function in the Java program, which will in turn invoke miniEugene
    java_part_orders = miniEugeneInstance.miniPermute(rules, part_count, orders_count)
    if java_part_orders:
        log.cf.info(f'\nDPL FILES:'
                    f'\n - Valid part orders found by miniEugene...')
        valid_orders = []  # Convert back to Python-friendly form
        for component in java_part_orders:
            order = []
            for part in component:
                order.append(part)
            valid_orders.append(order)
            log.cf.info(f'   + {order}')
    else:
        log.cf.error("miniEugene did not return valid part orders...")
