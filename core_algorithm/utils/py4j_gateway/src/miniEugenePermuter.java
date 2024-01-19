import py4j.GatewayServer;

import java.net.URI;
import java.util.Arrays;
import java.util.List;
import java.text.SimpleDateFormat;  
import java.util.Date;
import javax.management.*;
import java.lang.management.ManagementFactory;

import org.cidarlab.minieugene.MiniEugene;
import org.cidarlab.minieugene.dom.Component;
import org.cidarlab.minieugene.exception.MiniEugeneException;
import org.cidarlab.minieugene.util.SolutionExporter;


public class miniEugenePermuter {

  public String[][] miniPermute(List<String> input, int part_count, int orders_count) {
	  	SimpleDateFormat formatter = new SimpleDateFormat("dd/MM/yyyy HH:mm:ss");  
		Date date = new Date();  
		System.out.println(formatter.format(date));  
	    System.out.println("Java miniPermute function called by the Python script.");
		
		// Instantiate miniEugene
		MiniEugene me = new MiniEugene();
		
		// Reformat input for use by miniEugene solve() function
        String[] array = new String[input.size()];
        System.arraycopy(input.toArray(), 0, array, 0, input.size());
		String[] rules = array;
		
		// Run solve(rules, x, y) (Find y part orders with x parts in each)
		try {
			me.solve(rules, part_count, orders_count);
		} catch(Exception e) {
			e.printStackTrace();
		}

		// Save to file
		// SolutionExporter se = new SolutionExporter(
				// me.getSolutions(), me.getInteractions());
		// try {
			// String folder = "./examples/solutions.eug";
			// se.toEugene(folder);
			// System.out.println("Saved part orders to " + folder + ".");
		// } catch (MiniEugeneException e) {
			// e.printStackTrace();
		// }

		// Reformat for return to Python
		int len = me.getSolutions().size();
        String[][] solutions = new String[len][part_count];
		if(null != me.getSolutions()) {
		    int i = 0;
			for(Component[] solution : me.getSolutions()) {
			    int j = 0;
			    for(Component object : solution) {
			        solutions[i][j] = object.getName();
			        j++;
			    }
			    i++;
			}
		}

	    System.out.println("Returning " + solutions.length + " valid part orders to the Python script...");

        System.out.println(Thread.currentThread().getThreadGroup().getName() + " threads: " + Thread.activeCount());
        System.out.println("Total threads (all groups): " + ManagementFactory.getThreadMXBean().getThreadCount());

	    Runtime rt = Runtime.getRuntime();
        long total_mem = rt.totalMemory();
        long free_mem = rt.freeMemory();
        long used_mem = total_mem - free_mem;
        System.out.println("Memory usage: " + used_mem/1000000.0 + " MB");

		System.out.println("\nWaiting for additional calls from the Python script...\n");

        return solutions;
  }


  public static void main(String[] args) {
	System.out.println("\nStarting Java program to instantiate the Py4J Gateway...");
	
    miniEugenePermuter app = new miniEugenePermuter();  // app is now the gateway.entry_point
    GatewayServer server = new GatewayServer(app);
    server.start();
	System.out.println("Py4J Java Gateway instantiated.");
	System.out.println("\nWaiting for calls from the Python script...\n");
  }

}
