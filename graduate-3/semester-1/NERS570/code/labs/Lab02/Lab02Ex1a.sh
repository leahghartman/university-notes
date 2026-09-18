#!/bin/bash

if [ -z "$1" ]; then
    echo "Number of intervals is not defined!"
    echo "Script requires one argument!"
    exit 1
else
    if [[ $1 =~ ^-?[0-9]+$ ]]; then
        if [ $1 -le 0 ]; then
            echo "N=$1 is less than 1!"
            echo "N must be greater than 0!"
            exit 3
        fi
    else
        echo "Value of N is not an integer!"
        echo "N=$1"
        exit 2
    fi
fi

N=$1

# Create an outer loop that loops over the temperature values we'd like to 
# perform the calculations at.
for temperature in "300K" "600K" "800K"; do
    # Assign variables for the directory and csv file names
    dir_name=$temperature
    csv_name=$dir_name/"water_prop_$N.csv"

    # Create a directory (ONLY if it doesn't exist) for the current temperature
    mkdir -p $dir_name

    # Remove the old CSV file (if one exists) and create a new one
    rm -f $csv_name && touch $csv_name

    # Create a header for the top of the CSV file
    echo "pressure [MPa], density [g/ml], viscosity [muPa*s], enthalpy [kJ/kg]" >> $csv_name

    # For N equi-spaced intervals, evaluate the pressure at Pi 
    for i in $(seq 0 $(($N-1))); do
        Pi=$(awk -v N="$N" -v i="$i" 'BEGIN { printf "%.3f", (100/N)*(i+0.5)}')

        # Put the calculated pressure in the first column of the file
        echo -n "$Pi," >> $csv_name

        # Run the thermo_water script for each property for this specific pressure
        for property in "density" "viscosity" "enthalpy"; do
            result=$(./thermo_water $temperature $Pi $property)

            # Append the calculated value to the last line of the CSV file.
            # Don't append a comma at the end of the line if we're at the last
            # property.
            if [[ "$property" == "enthalpy" ]]; then
                echo -n "$result" >> $csv_name
            else 
                echo -n "$result," >> $csv_name
            fi
        done

        # After this loop is done, we've completed writing a single line in the
        # data file, so make sure to move to the next line.
        echo "" >> $csv_name
    done
done
