#!/bin/bash

# (a) Use a command to download the tar.gz file
wget http://www-personal.umich.edu/~bkochuna/NERS570/Lab2/Ex2.tar.gz

# (b) Use a command to unzip the file and enter the directory
tar -xf Ex2.tar.gz; cd Ex2

# (c) Use the find command to find the locations of two files and (d) find the
# differences between the content of the two files
diff $(find . -maxdepth 2 -name "nuclear_secrets*.txt") > launch_code.txt

# (e)(i) Search all given files
grep -rwl                       \
    --exclude="launch_code.txt" \
    "Jackpot" .                 \
    | sort -t'/' -k3,3          \
    > jackpot_locations.txt

# (e)(ii) Only search .doc/.xml files, so created .txt files are already excluded naturally
grep -rwl \
    --include="*.doc"  \
    --include="*.xml"  \
    "Jackpot" .        \
    | sort -t'/' -k3,3 \
    >> jackpot_locations.txt

# (e)(iii) Search .txt files only; have to explicitly exclude created txt files
grep -irwlE                           \
    --exclude="jackpot_locations.txt" \
    --exclude="launch_code.txt"       \
    --include="*.txt"                 \
    "jack\s*pot" .                    \
    | sort -t'/' -k3,3                \
    >> jackpot_locations.txt
