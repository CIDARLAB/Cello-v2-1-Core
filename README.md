# CELLO-3.0

CELLO-3.0 is a software package for designing genetic circuits based on logic gate designs written in the Verilog format. It includes a core cell-logic synthesis process, plus a web-interface for modifying UCF files. CELLO-3.0 is capable of efficiently handling single-cellular partitioning, gerenating results saved in a local directory on your machine, with optional verbose commandline-outputs.

## Cloning the repo

```
git clone https://github.com/your-username/cello-3.0.git
cd CELLO-3.0/
```
Here, you can find two modules which are independent of each other:
- CELLO-V3 (run the Cello genetic circuit design algorithm)
- UCFormatter (modify [UCF]() files containin genetic part specifications)

#
## CELLO-V3
### Setup Instructions:
First, install necessary packages (venv is recommended)
```
brew install yosys
```
That's all you need!

### Usage:
Navigate into the CELLO-V3 folder,
```
cd CELLO-V3/
```
CELLO-V3 takes the following parameters, for example:
```
vname = 'g92_boolean'
ucfname = 'SC1C1G1T1'
inpath = '/home/user/example/path/to/input_folder'
outpath = '/home/user/example/path/to/input_folder'
```
Then to run Cello:

```
python celloAlgo.py
```
Finally, you can find the results and the optimized design in the *outpath* folder!

### Note: 
The size of the design that CELLO-3.0 can handle is limited by the number of genetic parts specified in the UCF files. To achieve intra-cellular partitioning for large circuit designs, consider first using [Oriole]() to parition the design into smaller circuits, and the feed them into CELLO-3.0. 


#
## UCFormatter
### Setup Instructions:
```
cd UCFormatter/
```
You'll need to install [Redis](https://redis.io/docs/getting-started/installation/) on your computer

Ex. On MacOS:
```
brew install redis
```
(for other platforms, please check Redis installation guide)

Then, install a few python pacakges
```
pip install -r req.txt
```

### Running UCFormatter tool:
```
python UCFormatter.py
```
Finally, navigate to [localhost:8050](http://127.0.0.1:8050) to see use UCFormatter running!

### Troubleshoot:

If You get the error that port 8050 is already running it means that UCFormatter was not shut down correctly from the last session. You can try to shut it down this way:

```
redis-cli shutdown
```
(Ignore if it takes forever, use 'ctrl+c')

```
lsof -i :8050
```

This will show you as list of PIDs running on port 8050

```
kill PID
```
(use the PIDs that listed from the last step, repeat if needed)

Now, you are able to restart Cello again!

If that doesn't work, just restart your computer, all your cache will be reset this way.


## Intended Usage

CELLO-3.0 can be used in a variety of ways, depending on your needs:

- As a standalone tool: Use the interactive shell interface to design optimized genetic circuits.
- As a Python package: Import the core CELLO code as a Python library and use it as a component in your own software.

CELLO-3.0 also includes a proprietary UCF formatter tool that can modify or create UCF files through an intuitive graphial user interface.

## Features

* Core cell-logic synthesis process from logic circuits.
* Optional verbose command-line outputs
* Visualizes circuit mapping and circuit-flow scores
* Transform design to SBOL format for universtal transport


## Future Work

CELLO-3.0 is an ongoing project, and future work may include:

* Optimizing Yosys commands for logic synthesis
* Develop more compatibility with any genetic circuit designs
* Integrating with other genetic engineering tools and databases

## Contributing

We welcome contributions from the community! If you'd like to contribute to CELLO-3.0, please follow the guidelines in the CONTRIBUTING.md file.

## Credits

CELLO-3.0 was developed by [Weiqi Ji](https://ginomcfino.github.io) and [other contributors]() at [CIDAR LAB](https://www.cidarlab.org) under [Douglas Densmore](https://www.cidarlab.org/doug-densmore). It was inspired by the original CELLO software package developed by [CIDAR LAB](https://www.cidarlab.org) and [other contributors]().

## License

CELLO-3.0 is released under the [license name] license. See the LICENSE file for more information.



