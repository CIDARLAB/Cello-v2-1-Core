"""
Uses Py4J to invoke a Java program in an already running JVM to interface with the eugene.jar to run the eugene script.
The script runs Eugene's permute function, which generates all valid part orders based on the UCF rules.
These part orders are then used for SBOL and other file generation.

This utilizes the miniEugene-core program.  Please see github or the included md file for copyright information.
https://github.com/CIDARLAB/miniEugene-core

"""

import logging
import re
import itertools

from core_algorithm.utils import log


def call_mini_eugene(rules: list[str], orders_count: int = 100):
    """
    NOTE: Commands to be executed before the Python script...
    Compilation:
      javac -cp .:jars/py4j.jar:.:jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src src/miniEugenePermuter.java
      javac -cp .;jars/py4j.jar;.;jars/miniEugene-core-1.0.0-jar-with-dependencies.jar;./src src/miniEugenePermuter.java
    Execution:
      java -cp .:jars/py4j.jar:./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src miniEugenePermuter // mac
      java -cp .;jars/py4j.jar;./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar;./src miniEugenePermuter // win
    NOTE: May need to add java to the path and restart the console...

    :param rules:
    :param part_count:
    :param orders_count: -1 to find ALL valid permutations (may be prohibitively long)
    """

    from py4j.java_gateway import JavaGateway, GatewayParameters
    # Suppress (useless) console output
    logging.getLogger("py4j").setLevel(logging.INFO)
    # from py4j.java_collections import ListConverter

    # Connect to JVM and setup to convert to Java-friendly containers
    gateway = JavaGateway(gateway_parameters=GatewayParameters(auto_convert=True))
    miniEugeneInstance = gateway.entry_point
    # java_rules = ListConverter().convert(rules, addition_app._gateway_client)  # convert to Java container explicitly
    # gateway.jvm.java.util.Collections.sort(java_rules)

    # rules = ['STARTSWITH L1', 'L2 BEFORE L3', 'CONTAINS L1', 'CONTAINS L2', 'CONTAINS L3', 'ALL_FORWARD',
    #          'P1_PhlF_a AFTER L2', 'P1_PhlF_a BEFORE L3', 'P1_PhlF_b AFTER L3', 'Q1_QacR_a AFTER L2',
    #          'Q1_QacR_a BEFORE L3', 'F2_AmeRs_a AFTER L2', 'F2_AmeRs_a BEFORE L3', 'CONTAINS F2_AmeRs_a',
    #          'CONTAINS Q1_QacR_a', 'CONTAINS P1_PhlF_a', 'CONTAINS P1_PhlF_b', 'CONTAINS YFP_reporter_2_a',
    #          'L1 EXACTLY 1', 'L2 EXACTLY 1', 'L3 EXACTLY 1',
    #          'F2_AmeRs_a EXACTLY 1', 'Q1_QacR_a EXACTLY 1', 'P1_PhlF_a EXACTLY 1', 'P1_PhlF_b EXACTLY 1',
    #          'YFP_reporter_2_a EXACTLY 1', 'L1 EXACTLY 1', 'L2 EXACTLY 1', 'L3 EXACTLY 1']

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

    rules.reverse()

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
    # print('Rules: ', rules)
    # print('\nPart_count: ', part_count)
    # print('\nOrders_count: ', orders_count)
    java_part_orders = miniEugeneInstance.miniPermute(rules, part_count, orders_count)  # FIXME: Add device rule loop
    # java_part_orders_2 = miniEugeneInstance.miniPermute(rules, part_count, orders_count)
    rules.reverse()
    # java_part_orders_rev = miniEugeneInstance.miniPermute(rules, part_count, orders_count)

    def convert_to_list_of_lists(part_orders):
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
            # print("valid_orders: ")
            # for order in valid_orders:
            #     print(order)
            return valid_orders
        else:
            log.cf.error("miniEugene did not return valid part orders...")

    valid_orders = convert_to_list_of_lists(java_part_orders)
    # valid_orders_2 = convert_to_list_of_lists(java_part_orders_2)
    # valid_orders_rev = convert_to_list_of_lists(java_part_orders_rev)
    # if valid_orders == valid_orders_2:
    #     print('\n\nCONSISTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n')
    # else:
    #     print('\n\nNOT CONSISTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n')
    # if valid_orders == valid_orders_rev:
    #     print('\n\nORDER DOES NOT MATTER!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n')
    # else:
    #     print('\n\nORDER DOES MATTER!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n')
    if len(valid_orders) > 5:
        selected_orders = []
        for cnt in range(5):
            selected_orders.append(valid_orders[cnt*len(valid_orders)//5])
        return selected_orders
    else:
        return valid_orders
