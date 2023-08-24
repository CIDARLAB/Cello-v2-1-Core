"""
Uses Py4J to invoke a Java program in an already running JVM to interface with the eugene.jar to run the eugene script.
The script runs Eugene's permute function, which generates all valid part orders based on the UCF rules.
These part orders are then used for SBOL and other file generation.
TODO: Ensure JVM properly started on Docker.
"""

import py4j

from py4j.java_gateway import JavaGateway

gateway = JavaGateway()
