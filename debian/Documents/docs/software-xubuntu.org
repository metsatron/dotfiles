#!/usr/bin/bash
# metsatron standard app install

# start
sudo apt update
sudo apt upgrade
sudo add-apt-repository multiverse
sudo apt update

sudo apt install curl cpufrequtils stow p7zip-rar pngquant neofetch unrar emacs htop php
sudo cpufreq-set -r -g performance

# Install or uninstall the latest Linux kernels from the Ubuntu Kernel PPA
sudo apt update
wget https://raw.githubusercontent.com/pimlie/ubuntu-mainline-kernel.sh/master/ubuntu-mainline-kernel.sh
sudo install ubuntu-mainline-kernel.sh /usr/local/bin/
ubuntu-mainline-kernel.sh -c
sudo ubuntu-mainline-kernel.sh -i

# Install Ubuntu Mainline Kernel Installer
sudo add-apt-repository ppa:cappelikan/ppa
sudo apt update
sudo apt install mainline

# Disc Image Tools
sudo apt install bchunk ccd2iso mdf2iso nrg2iso mame-tools ciso gparted gpart boabab acetoneiso

# Install dependencies
sudo dpkg --add-architecture i386
wget -nc https://dl.winehq.org/wine-builds/winehq.key
sudo apt-key add winehq.key
sudo apt-add-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ focal main'
sudo apt update
sudo apt install --install-recommends winehq-stable wine winetricks

# Install Software
sudo apt install filezilla deluge steam kdeconnect inkscape shotwell meld gthumb libreoffice-l10n-en-gb hunspell-en-gb hunspell-en-au

# Install Media Software
sudo apt install obs-studio vlc kdenlive qmmp sox audacity mkvtoolnix mkvtoolnix-gui 

# HandBreak
sudo add-apt-repository ppa:stebbins/handbrake-releases
sudo apt install --install-recommends handbrake-gtk

# install SMplayer & SMtube
sudo add-apt-repository ppa:rvm/smplayer
sudo apt-get update
sudo apt-get install smtube mplayer smplayer

# Kdenlive
sudo add-apt-repository ppa:kdenlive/kdenlive-stable
sudo apt install kdenlive

# Midi
sudo apt install yoshimi qmidiroute jack-keyboard seq24 fluidsynth qsynth fluid-soundfont-gm jackd2 pulseaudio-module-jack

# Install Nextcloud development
sudo add-apt-repository ppa:nextcloud-devs/client
sudo apt install nextcloud-desktop

# Avidemux
sudo add-apt-repository ppa:ubuntuhandbook1/avidemux
sudo apt update
sudo apt install libavidemux2.7-6 libavidemux2.7-qt5-6 avidemux2.7-qt5 avidemux2.7-plugins-qt5 avidemux2.7-jobs-qt5

# Install virtualbox
# sudo apt install virtualbox virtualbox-ext-pack virtualbox-guest-additions-iso virtualbox-dkms

# Install QEMU virt-manager
sudo apt install virt-manager

# Install Lutris
sudo add-apt-repository ppa:lutris-team/lutris
sudo apt update
sudo apt install lutris

# GZdoom
sudo apt-get install g++ make cmake libsdl2-dev git zlib1g-dev \
     libbz2-dev libjpeg-dev libfluidsynth-dev libgme-dev libopenal-dev \
     libmpg123-dev libsndfile1-dev libgtk-3-dev timidity nasm \
     libgl1-mesa-dev tar libsdl1.2-dev libglew-dev

# snap
sudo snap install waterfox-classic --edge --devmode
sudo snap install telegram-desktop
sudo snap install discord
sudo snap install skype --classic
sudo snap install zoom-client
sudo snap install slack --classic
sudo snap install freeplane-mindmapping
sudo snap install foobar2000
sudo snap install --edge mpc-hc
sudo snap install losslesscut
sudo snap install signal-desktop
sudo snap install gzdoom

# Flatpak
sudo apt install flatpak
sudo apt install gnome-software-plugin-flatpak
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
# flatpak install flathub org.gmusicbrowser.gmusicbrowser
flatpak install flathub com.github.geigi.cozy

# ungoogled-chromium
echo 'deb http://download.opensuse.org/repositories/home:/ungoogled_chromium/Ubuntu_Focal/ /' | sudo tee /etc/apt/sources.list.d/home:ungoogled_chromium.list
curl -fsSL https://download.opensuse.org/repositories/home:ungoogled_chromium/Ubuntu_Focal/Release.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/home:ungoogled_chromium.gpg > /dev/null
sudo apt update
sudo apt install ungoogled-chromium

# Global Menu
sudo apt install xfce4-appmenu-plugin vala-panel-appmenu

# TeamViewer
wget https://download.teamviewer.com/download/linux/teamviewer_amd64.deb
sudo apt install ./teamviewer_amd64.deb

# RPCS3 Emulator
sudo apt-get install build-essential
sudo apt-get install qtcreator
sudo apt-get install qt5-default
cd ~/Apps
chmod a+x ./rpcs3-*_linux64.AppImage && ./rpcs3-*_linux64.AppImage

# Dolphin Emulator
sudo apt-add-repository ppa:dolphin-emu/ppa
sudo apt update
sudo apt install dolphin-emu

# FSlint
mkdir -p ~/Downloads/fslint
cd ~/Downloads/fslint
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/pygtk/python-gtk2_2.24.0-6_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/pygtk/python-glade2_2.24.0-6_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/f/fslint/fslint_2.46-1_all.deb
sudo apt-get install ./*.deb

# Caliabre
sudo -v && wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sudo sh /dev/stdin

