#!/usr/bin/env python3

# Import everything necessary for the calculations in this file
import sys  # This is needed for command-line user inputs
import numpy as np
import pandas as pd

# Check first that the user is properly calling the python script
if len(sys.argv) < 3:
    print("Usage: python Lab02Ex1b.py <file_name> <polynomial_order>")
    sys.exit(1)

# Note that sys.argv[0] is always the script name itself, so the user inputs we
# need will be found in sys.argv[1] and sys.argv[2].
file_name  = sys.argv[1]
poly_order = sys.argv[2]

# Now we're going to perform a few checks on the file in particular. This file
# needs to exist and allow us to open it (correct permissions).
try:
    # Try to read the data
    csv_data = pd.read_csv(file_name).to_numpy()

except FileNotFoundError:
    # If we can't find the file, print an error message.
    print("Error: File not found.")
except pd.errors.EmptyDataError:
    # If there's no data in the file, print an error message.
    print("Error: The CSV file is empty.")
except pd.errors.ParserError:
    # If the file is not in CSV format or corrupted, print an error message.
    print("Error: The CSV file is corrupted or not a valid CSV format.")

# Also perform a few checks on the polynomial order. This has to be greater
# than zero in order for the code to work.
# TODO: the above comment



# Define a function to calculate the .. for ..
def fit_polynomial(x, y, poly_order):
    A = np.column_stack([x**i for i in range(poly_order + 1)])
    
    AT_A_inv = np.linalg.inv(np.dot(A.T, A))
    AT_y = np.dot(A.T, y)
    beta = np.dot(AT_A_inv, AT_y)

    return beta

# Start the calculations with a for loop that cycles through each property in 
# the file (density, viscosity, enthalpy) and grabs the columns corresponding
# to
pressure_data = csv_data[:, 0]
for index, property in enumerate(["Density", "Viscosity", "Enthalpy"]):
    # Convert the pandas output to a numpy array
    property_data = csv_data[:, index + 1]
    beta = fit_polynomial(pressure_data, property_data, int(poly_order))

    print(property)
    print(*(f"{a:.3e}" for a in beta), sep="\n")
    print("\n")








