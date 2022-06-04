#!/bin/sh -x
# bash script to setup fshome project initially

cd ~/fshome

# create a local fshome repositry
git init
touch .gitignore
git add .gitignore
git commit -m "initial commit setting up submodules"

git clone --depth=1 https://github.com/FuzzyMistborn/python-eufy-security ./submod/eufy
git submodule add https://github.com/FuzzyMistborn/python-eufy-security
git submodule update --force --checkout submod/eufy

# get bottle as submodule
git clone --depth=1 --no-checkout https://github.com/bottlepy/bottle ./bottle
git submodule add https://github.com/bottlepy/bottle
git -C ./bottle config core.sparsecheckout true
echo bottle.py >> ./bottle/.git/info/sparse-checkout
git submodule update --force --checkout bottle

# get HAP-python as submodule
git clone --depth=1 --no-checkout https://github.com/ikalchev/HAP-python ./submod/HAP-python
git submodule add https://github.com/ikalchev/HAP-python
git -C ./submod/HAP-python config core.sparsecheckout true
echo !tests/* >> ./submod/HAP-python/.git/info/sparse-checkout
echo !docs/* >> ./submod/HAP-python/.git/info/sparse-checkout
echo !accessories/* >> ./submod/HAP-python/.git/info/sparse-checkout
#echo "pyhap/">> ./HAP-python/.git/info/sparse-checkout
echo "/*">> ./submod/HAP-python/.git/info/sparse-checkout
git submodule update --force --checkout submod/HAP-python

# get bluepy as submodule
git clone --depth=1 --no-checkout https://github.com/IanHarvey/bluepy ./bluepy
git submodule add https://github.com/IanHarvey/bluepy
git -C ./bluepy config core.sparsecheckout true
echo !docs/* >> ./bluepy/.git/info/sparse-checkout
echo !bluez-5.47/* >> ./bluepy/.git/info/sparse-checkout
echo "/*">> ./bluepy/.git/info/sparse-checkout
git submodule update --force --checkout bluepy
cd bluepy
sudo apt install libglib2.0-dev
pip3 install .

#symlink to pyhap as HAP-python modules refer to pyhap directly
ln -s ./HAP-python/pyhap ./pyhap
ln -s ./submod/eufy/eufy_security ./eufy

# maybe still required for zeroconf package:
#sudo apt-get install libavahi-compat-libdnssd-dev avahi-utils
#cd HAP-python
#python3 -m pip install -r -v requirements.txt
#python3 setup.py