"""
Uses Py4J to invoke a Java program in an already running JVM to interface with the eugene.jar to run the eugene script.
The script runs Eugene's permute function, which generates all valid part orders based on the UCF rules.
These part orders are then used for SBOL and other file generation.
TODO: Ensure JVM properly started on Docker.
"""

from py4j.java_gateway import JavaGateway

gateway = JavaGateway()                   # connect to the JVM
random = gateway.jvm.java.util.Random()   # create a java.util.Random instance
number1 = random.nextInt(10)              # call the Random.nextInt method
number2 = random.nextInt(10)
print(number1, number2)

addition_app = gateway.entry_point               # get the AdditionApplication instance
value = addition_app.addition(number1, number2)  # call the addition method
print(value)
