#!/bin/bash

modname=$1
if [ -z "$modname" ]; then
  read -p " module to refresh?: " modname
fi
echo updating "$modname"
read -p "continue?" yesno

if [ -n $yesno ]; then
  if [ ! -d "obsolete" ]; then
    mkdir obsolete
  fi
  cp -r $modname obsolete
  rm -rf $modname
  git submodule deinit -f -- $modname
  rm -rf .git/modules/$modname
  git rm -f $modname
fi
if [ "$modname" = "HAP-python" ]; then
  modurl=https://github.com/ikalchev/HAP-python
  incl1=!tests/*
  incl2=!docs/*
  incl3=!accessories/*
  incl4="/*"
fi
if [ "$modname" = "bottle" ]; then
  modurl=https://github.com/bottlepy/bottle
  incl1=bottle.py
fi
if [ "$modname" = "bluepy" ]; then
  modurl=https://github.com/IanHarvey/bluepy
  incl1=!docs/*
  incl2=!bluez-*/*
  incl4="/*"
  sudo apt install libglib2.0-dev
fi

git clone --depth=1 --no-checkout $modurl ./$modname
git submodule add $modurl
git -C ./$modname config core.sparsecheckout true
if [ -n $incl1 ]; then
echo $incl1 >> ./$modname/.git/info/sparse-checkout
fi
if [ -n $incl2 ]; then
echo $incl2 >> ./$modname/.git/info/sparse-checkout
fi
if [ -n $incl3 ]; then
echo $incl3 >> ./$modname/.git/info/sparse-checkout
fi
if [[ -n $incl4 ]]; then
echo "$incl4">> ./$modname/.git/info/sparse-checkout
fi
git submodule update --force --checkout $modname

read -p "pip3 install $modname?" yesno
if [[ -n $yesno && $yesno=yes ]]; then
cd $modname
pip3 install .
fi

