# botorch [Alpha]

botorch is a library for Bayesian Optimization in pytorch.
This is an alpha version under active development - expect things to break!


## Installation

**Requirements**:
- Python >= 3.6
- PyTorch >= 1.0.1
- gpytorch >= 0.2.1
- cython
- scipy

#### Install using conda

1. Create the base environment using `conda env create -f botorch_base.yml`

2. Activate the environment using `conda activate botorch_base`

3. Install via pip: `pip install git+ssh://git@github.com/facebookexternal/botorch.git`

*Notes:*
- To use **CUDA on MacOS**, pytorch needs to be built from source instead
(see the quick start instructions on https://pytorch.org/)
- In 3. you **must** use ssh since the repo is private - for that to work, make
sure your ssh public key is registered with GitHub, and is usable by ssh.
