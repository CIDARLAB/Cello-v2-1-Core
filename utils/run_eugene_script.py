"""
Uses Py4J to invoke a Java program in an already running JVM to interface with the eugene.jar to run the eugene script.
The script runs Eugene's permute function, which generates all valid part orders based on the UCF rules.
These part orders are then used for SBOL and other file generation.
TODO: Ensure JVM properly started on Docker.
"""

# import subprocess
import log
import logging
import re


def call_mini_eugene(rules: list[str], orders_count: int = 5):
    """
    NOTE: Commands to be executed before the Python script...
    External command to compile miniEugenePermuter class:
        javac -cp .;py4j.jar;.;miniEugene-core-1.0.0-jar-with-dependencies.jar miniEugenePermuter.java
    External command to execute program to instantiate Py4J Java Gateway:
        java -cp .;py4j.jar;.;miniEugene-core-1.0.0-jar-with-dependencies.jar miniEugenePermuter
    NOTE: May need to add java to the path and restart the console...

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
    # java_rules = ListConverter().convert(rules, addition_app._gateway_client)  # convert to Java container explicitly
    # gateway.jvm.java.util.Collections.sort(java_rules)

    part_count = 0
    max = 0
    for rule in rules:
        if 'CONTAINS ' in rule:
            rules.append(f'{rule.split(" ")[1]} EXACTLY 1')
            part_count += 1
    for rule in rules:
        if ' EQUALS ' in rule:
            index = int(re.search('(?<=\\[)(.*)(?=\\])', rule)[0])
            if index > max:
                max = index
    if max > part_count:
        part_count = max + 2

    # DEBUGGING...
    # log.cf.info(f'Rules received by call_mini_eugene: {rules}')
    # log.cf.info(f'Part count received by call_mini_eugene: {part_count}')
    # rules = ['STARTSWITH Loc1', 'Loc2 NEXTTO Loc1', 'P3_PhlF BEFORE S4_SrpR', 'P3_PhlF BEFORE A1_AmtR',
    # 'S4_SrpR BEFORE A1_AmtR', 'P3_PhlF AFTER Loc2', 'S4_SrpR AFTER Loc2', 'A1_AmtR AFTER Loc2', 'P3_PhlF BEFORE Loc3',
    # 'S4_SrpR BEFORE Loc3', 'A1_AmtR BEFORE Loc3', 'ALL_FORWARD', 'CONTAINS S4_SrpR', 'CONTAINS A1_AmtR',
    # 'CONTAINS P3_PhlF', 'CONTAINS YFP_reporter_2', 'CONTAINS Loc1', 'CONTAINS Loc2', 'CONTAINS Loc3']
    # rules = ['STARTSWITH Loc1', 'Loc2 NEXTTO Loc1', 'P3_PhlF BEFORE S4_SrpR', 'ALL_FORWARD', 'CONTAINS S4_SrpR',
    # 'CONTAINS P3_PhlF', 'CONTAINS Loc1', 'CONTAINS Loc2', 'CONTAINS Jscar', '[3] EQUALS Jscar']

    # Call the miniPermute function in the Java program, which will in turn invoke miniEugene
    java_part_orders = miniEugeneInstance.miniPermute(rules, part_count, orders_count)  # FIXME: Add device rule loop
    if java_part_orders:
        # log.cf.info('Valid part orders found by miniEugene...')
        valid_orders = []  # Convert back to Python-friendly form
        for component in java_part_orders:
            if component[0] is not None:
                order = []
                for part in component:
                    order.append(part)
                valid_orders.append(order)
                # log.cf.info(f'   + {order}')
        return valid_orders
    else:
        log.cf.error("miniEugene did not return valid part orders...")
