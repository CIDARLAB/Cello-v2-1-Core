# CELLO-V3-CORE

CELLO-V3-CORE is a streamlined algorithm for designing genetic circuits based on logic gate designs written in the Verilog format. It executes through the command-line interface by calling the 'celloAlgo.py' script. CELLO-3.0 is capable of efficiently handling single-cellular partitioning with multiple-output support, gerenating results saved in a local directory on your machine, with verbose logging.

## Cloning the repo

```
git clone https://github.com/CIDARLAB/Cello-v3-Core.git
cd Cello-v3-Core/
```

#
# Setup Instructions
### Install Packages:
YOSYS is the only required package to run Cello-v3-Core! Please check YOSYS installation guide for platforms other than MacOS.
```
brew install yosys
```

(Note: Using a venv is recommended)

## Usage:
CELLO-V3 takes the following parameters, and you can modify them in the __main__ function for celloAlgo.py, for example:

(rememebr to put the verilog files and all UCF files you want to work with in the 'input_folder')
```
vname = 'g92_boolean'
ucfname = 'SC1C1G1T1'
inpath = '/home/user/example/path/to/input_folder'
outpath = '/home/user/example/path/to/output_folder'
```
Then to run Cello:

```
python celloAlgo.py
```
That's it, and you can find the results and the optimized design in the *outpath* folder!

### Note: 
The size of the design that CELLO-3.0 can handle is limited by the number of genetic parts specified in the UCF files. To achieve intra-cellular partitioning for large circuit designs, consider first using [Oriole]() to parition the design into smaller circuits, and the feed them into CELLO-3.0. 

#
## Contributing

We welcome contributions from the community! If you'd like to contribute to CELLO-3.0, please follow the guidelines in the CONTRIBUTING.md file.

## Credits

CELLO-3.0 was developed by [Weiqi Ji](https://ginomcfino.github.io) and [other contributors]() at [CIDAR LAB](https://www.cidarlab.org) under [Douglas Densmore](https://www.cidarlab.org/doug-densmore). It was inspired by the original CELLO software package developed by [CIDAR LAB](https://www.cidarlab.org) and [other contributors]().

## License

CELLO-3.0 is released under the [license name] license. See the LICENSE file for more information.



