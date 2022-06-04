#!/bin/bash
#sudo apt install fbi
#sudo apt install sshfs
#sshfs pi@192.168.1.20:/mnt/extntfs /mnt/raspi3mnt
pkill -f /usr/bin/fbi
shopt globstar
cd /mnt/rasp3mnt/fotoos
files=(**/*.jpg **/*.bmp **/*.png **/*.heic)
sudo fbi -noverbose -a -t 4 -u "${files[@]}"
