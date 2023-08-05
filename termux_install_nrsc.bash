#!~/../usr/bin/bash
#
# This script downloads, builds and installs nrsc5 in Termux (with rtl sdr USB support
# 2. upgrade Termux Packages
pkg upgrade

# 3. Install first set of dependencies (based on @ferrellsl's original post) **AND libao **:
pkg install git cmake curl build-essential autoconf libtool binutils libao termux-api libusb fftw

# 4. Clone the librtlsdr git repo (from the pastebin script):
git clone https://github.com/librtlsdr/librtlsdr.git

# 5. Change to librtlsdr source directory:
cd librtlsdr

# 6. Remove the pthread_cancel from rtl_adsb.c (we're not using ads-b with nrsc5 anyway):
sed -i 's/pthread_cancel/\/\/pthread_cancel/g' src/rtl_adsb.c

# 7. Build and install librtlsdr
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$PREFIX ..
make
make install
cd ../..

# 8. Clone the nrsc5 repo from git:
git clone https://github.com/theori-io/nrsc5.git

# 9. Change to nrsc5 directory:
cd nrsc5

# 10. Comment-out pthread_cancel call in main.c:
sed -i 's/pthread_cancel/\/\/pthread_cancel/g' src/main.c

# 11. Build nrsc5:
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$PREFIX ..
make
make install
cd ../..
