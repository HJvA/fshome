#!/bin/sh -x
# bash script to setup fshome project submodules
set -x
trap read debug

rm -d -r HAP-python
#rm -d -r .git/modules/HAP-python
git submodule init
git submodule update --depth=1
git submodule absorbgitdirs
git -C ./HAP-python config core.sparsecheckout true

echo !tests/* >> .git/modules/HAP-python/info/sparse-checkout
echo !docs/* >> .git/modules/HAP-python/info/sparse-checkout
echo !accessories/* >> .git/modules/HAP-python/info/sparse-checkout
#echo "pyhap/">> ./HAP-python/.git/info/sparse-checkout
echo "/*">> .git/modules/HAP-python/info/sparse-checkout

git submodule update --force --checkout HAP-python 
git submodule update --force --checkout bottle

return

cd ~/fshome


# get HAP-python as submodule
git clone --depth=1 --no-checkout https://github.com/ikalchev/HAP-python ./pyhap
git submodule add https://github.com/ikalchev/HAP-python ./pyhap
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