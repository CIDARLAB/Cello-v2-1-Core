# Cello-v3-Core

This software package is a streamlined algorithm for designing genetic circuits based on logic gate designs written in the Verilog format. It executes through the command-line interface by calling the 'celloAlgo.py' script. CELLO-3.0 is capable of efficiently handling single-cellular (with multi-cellular support coming soon) partitioning with multiple-output support, gerenating results saved in a local directory on your machine, with verbose logging, ang with GUI interface coming soon.

## Cloning the repo

```
git clone https://github.com/CIDARLAB/Cello-v3-Core.git
cd Cello-v3-Core/
```

# Setup Instructions
### Install Packages:
YOSYS is the only required package to run Cello-v3-Core! Please check [YOSYS installation guide](https://yosyshq.net/yosys/documentation.html) for platforms other than MacOS.

To install Yosys, the easiest way is through [Homebrew](https://brew.sh).
```
pip install graphviz
brew install yosys
```
you may need to install Graphviz. Please check [YOSYS installation guide](https://yosyshq.net/yosys/documentation.html) for platforms other than MacOS.

(Note: Python venv is not needed for Cello-v3-Core, but is recommended)

## Usage:
CELLO-V3 takes the following parameters, and you can modify them in the __main__ function for celloAlgo.py, for example:

```
inpath = '/home/user/example/path/to/input_folder'
outpath = '/home/user/example/path/to/output_folder'
```

By default, the ```inpath``` is the [sample_inputs](/sample_inputs/) folder, and the ```outpath``` is the [def_out](/def_out/) folder, so users can use Cello without having to specify the paths.


**To run Cello, type in terminal:**

```
python celloAlgo.py
```

Simply follow the prompts when it asks for which Verilog and UCF you would like to use.

That's it, and you will see the results and the optimized design in the *outpath* folder!

Alternatively, you could make a script to call the ```CELLO3``` process and use this codebase as an API.

### Note: 
The size of the design that CELLO-3.0 can handle is limited by the number of genetic parts specified in the UCF files. To achieve intra-cellular partitioning for large circuit designs, consider first using [Oriole](https://github.com/CIDARLAB/genetic-circuit-partitioning-new.git) to parition the design into smaller circuits, and the feed them into CELLO-3.0. 

#
## Sample Inputs
Can be found in the [sample_inputs](sample_inputs/) folder. This includes the UCF files for Cello, as well as a few dozen Verilog files to test Cello with. You may use your own Verilog files or modified UCF files to run Cello and choose a different a different folder to store them by speifying "inpath". But make sure that all the input files are valid, and they are organized in the right folder.

#
## Example Output
Here is an example of what the result from Cello looks like in the terminal. It uses the and.v circuit paried with Bth1C1G1T1 UCF. After running this experiment, you will see other files generated in the output folder as well. The important takeways are the *circuit score* and the *design*, which will be returned in the terminal. Because additional convenience features are on the backlog, it is important to check the terminal for the *circuit score* and the *design* Cello made.

**Note**: this represents a work-in-progress, two things still need to be done to produce correct circuit scores:

1. Fill out the IO values of each gate and output, and use the "min on" and "max off" values for the output instead of max / min from the outputs.
2. modify the recursive ```get_score``` function in gate_assignment.py to compount gate scores for each gate in gate group in each recursive step, rather than taking the best gate at each step.

After these changes are complete, the correct (ie. most optimized) designs will be produced by this software. The following is a work-in-progress which shows partially correct results.

![example output](assets/ExampleOutput_And+Eco_(WIP).png)

Please check the [assets](assets/) folder for further supplementary information.

#
## Contributing

We welcome contributions from the community! If you'd like to contribute to CELLO-3.0, please follow the guidelines in the CONTRIBUTING.md file.

## Credits

CELLO-3.0 was developed by [Weiqi Ji](https://ginomcfino.github.io) at [CIDAR LAB](https://www.cidarlab.org) under [Douglas Densmore](https://www.cidarlab.org/doug-densmore). It was inspired by the original [Cello](https://github.com/CIDARLAB/cello) and [CELLO-V2](https://github.com/CIDARLAB/Cello-v2.git) software package developed by [CIDAR LAB](https://www.cidarlab.org) under [Douglas Densmore](https://www.cidarlab.org/doug-densmore) and [other contributors](https://github.com/CIDARLAB).

## License

CELLO-3.0 is released under the [Apache 2.0](License.txt) license. See the LICENSE file for more information.



