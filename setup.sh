#!/bin/sh -x
# bash script to setup fshome project initially

cd ~/fshome

# create a local fshome repositry
git init
touch .gitignore
git add .gitignore
git commit -m "initial commit setting up submodules"

# get bottle as submodule
git clone --depth=1 --no-checkout https://github.com/bottlepy/bottle ./bottle
git submodule add https://github.com/bottlepy/bottle
git -C ./bottle config core.sparsecheckout true
echo bottle.py >> ./bottle/.git/info/sparse-checkout
git submodule update --force --checkout bottle

# get HAP-python as submodule
git clone --depth=1 --no-checkout https://github.com/ikalchev/HAP-python ./HAP-python
git submodule add https://github.com/ikalchev/HAP-python
git -C ./HAP-python config core.sparsecheckout true
echo !tests/* >> ./HAP-python/.git/info/sparse-checkout
echo !docs/* >> ./HAP-python/.git/info/sparse-checkout
echo !accessories/* >> ./HAP-python/.git/info/sparse-checkout
#echo "pyhap/">> ./HAP-python/.git/info/sparse-checkout
echo "/*">> ./HAP-python/.git/info/sparse-checkout

git submodule update --force --checkout HAP-python

# maybe still required for zeroconf package:
#sudo apt-get install libavahi-compat-libdnssd-dev avahi-utils
#cd HAP-python
#python3 -m pip install -r -v requirements.txt
#python3 setup.py