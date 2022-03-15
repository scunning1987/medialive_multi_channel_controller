#!/bin/bash
sudo bash -c 'echo -e "[nimble]\nname= Nimble Streamer repository\nbaseurl=http://nimblestreamer.com/centos/7/\$basearch\nenabled=1\ngpgcheck=1\ngpgkey=http://nimblestreamer.com/gpg.key\n" > /etc/yum.repos.d/nimble.repo'
sudo yum -y makecache
sudo yum -y install nimble
sudo yum -y install wget
sudo wget https://raw.githubusercontent.com/scunning1987/aws_projects/main/377/ec2_stream_builder.py
sudo python ec2_stream_builder.py 40 20000
sudo sed -i 's/port\ =\ 8081/port\ =\ 80/g' /etc/nimble/nimble.conf
sudo echo "management_listen_interfaces = *" >> /etc/nimble/nimble.conf
sudo service nimble start