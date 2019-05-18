#!/bin/sh -x
# bash script to setup fshome project initially

cd ~/fshome


# get HAP-python as submodule
git clone --depth=1 --no-checkout https://github.com/ikalchev/HAP-python ./pyhap
git submodule add https://github.com/ikalchev/HAP-python ../pyhap
git -C ./pyhap config core.sparsecheckout true
#echo !tests/* >> ./pyhap/.git/info/sparse-checkout
#echo !docs/* >> ./pyhap/.git/info/sparse-checkout
#echo !accessories/* >> ./pyhap/.git/info/sparse-checkout
#echo "pyhap/">> ./HAP-python/.git/info/sparse-checkout
echo !pyhap/*>> ./pyhap/.git/info/sparse-checkout

git submodule update --force --checkout pyhap

# maybe still required for zeroconf package:
#sudo apt-get install libavahi-compat-libdnssd-dev avahi-utils
#cd HAP-python
#python3 -m pip install -r -v requirements.txt
#python3 setup.py