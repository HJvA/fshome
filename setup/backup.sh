#!/bin/bash
#
# to copy fshome sqlite database to google drive
#
# rclone must have been installed and
# gdrive must be setup with a google account
# wget https://github.com/rclone/rclone/releases/download/v1.51.0/rclone-v1.51.0-linux-arm.deb
# sudo apt install ./rclone*.deb
# rclone config
#
# first use rsync to quickly copy to temp while locking the database
#
rclone lsl gdrive:rpibu
rclone copy --include \*.json \. gdrive:rpibu -Pu --max-depth 1
rclone copy /etc/samba/smb.conf gdrive:rpibu -Pu
rclone copy /etc/fstab gdrive:rpibu -Pu
rclone copy /etc/ztab gdrive:rpibu -Pu
rclone copy /etc/rc.local gdrive:rpibu -Pu
rclone copy ~/.config/rclone/rclone.conf gdrive:rpibu -Pu
rclone copy /etc/wpa_supplicant/wpa_supplicant.conf gdrive:rpibu -Pu
rclone copy /var/log/messages gdrive:rpibu -Pu
read -p "enter to continue"
rsync /mnt/extssd/storage/fs20store.sqlite /mnt/extntfs/storage -P
rclone copy /mnt/extntfs/storage/fs20store.sqlite gdrive:rpibu -P
