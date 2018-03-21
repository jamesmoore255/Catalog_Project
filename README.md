A simple project for creating catalogs and items within catalogs, with the ability to sign in, and alter the catalogs in which you own.

To use the same virtual machine to run this SQL database, you will first need to download VirtualBox, this will run the virtual machine. You do not need the extension pack, SDK or to launch the virtualbox, vagrant will do that. This is the link to download virtual box:

https://www.virtualbox.org/wiki/Download_Old_Builds_5_1

Download vagrant, install the version for your operating system. This is the link:

https://www.vagrantup.com/downloads.html

Fork and clone this github repository:

https://github.com/udacity/fullstack-nanodegree-vm

Navigate into the cloned directory, you will find another directory called vagrant, cd into this directory. From the terminal inside the vagrant subdirectory, run the command "vagrant up". This will download and install the Linux operating system. Once "vagrant up" is finished, you can run vagrant ssh to log into your new Linux VM.

Once you are logged in, change into the shared vagrant sub-directory using "cd /vagrant". This will be the subdirectory directly inside the "fullstack-nanodegree-vm" called vagrant. Anything you save in this subdirectory can be accessed using the Linux VM.

Then you will need to fork and download this directory into the vagrant folder. Once the directory is inside this folder you can run the vagrant machine, navigate to the directory and run:

"python project.py"

In your browser go to "localhost:8000/" and you will be able to use this catalog!

Author
James Moore

Unlicensed