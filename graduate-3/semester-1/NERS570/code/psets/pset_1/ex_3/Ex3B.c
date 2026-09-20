#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

// To calculate a binary number, we need to go through the following steps:
//      (1) Divide the decimal number by 2 and write down the remainder
//      (2) Take the new quotient and divide by 2; write down the remainder
//      (3) Continue dividing until the quotient becomes 0
//      (4) Read the remainders in REVERSE ORDER -- this is the binary value
//
// The following function implements this.
void to_binary(int quotient, char *binary, int size) {
    // We're going to fill the array starting at the back, so we can satisfy (4)
    // easily.
    binary[size - 1] = '\0';
    int index = size - 1;

    // If the starting number is 0, then just fill things out without needing
    // to even go into the while loop.
    if (quotient == 0) {
        binary[--index] = '0';
    } else {
        // While our quotient is > 0, we should continue to calculate remainders
        while (quotient > 0) {
            // Find the remainder when the quotient is divided by 2
            int remainder = quotient % 2;

            // Place the remainder at the end of the binary character array
            // Note that the "+ '0'" just converts the integer value to a
            // character literal.
            binary[--index] = remainder + '0';

            // Move onto the next quotient
            quotient /= 2;
        }
    }
}

// This function will calculate and return the Z number for a given two-dimensional
// coordinate. It proceeds through the following three steps:
//      (1) Converts x and y into binary numbers
//      (2) Interleaves the bits of the binary numbers
//      (3) Converts the interleaved number back to decimal and returns it
int z_order2d(int x, int y) {
    // Note that the most amount of characters and unsigned integer can be when
    // represented in binary is 32 characters. This defines an array of characters 
    // with a total capacity of 32 bytes.
    char binary_x[33];
    char binary_y[33];
    
    // Fill the entire array(s) with values first, then we'll write over when
    // we call the to_binary function
    for (int i = 0; i < 32; i++) {
        binary_x[i] = '0';
        binary_y[i] = '0';
    }

    // Convert x and y to binary values
    to_binary(x, binary_x, 33);
    to_binary(y, binary_y, 33);

    // Assign something to contain the new interleaved binary number and make sure
    // to assign the last character as '\0'
    char int_binary[65];
    int_binary[64] = '\0';
    
    // Assign a write index that we will cycle through to interleave the bits
    int write_index = 0;

    // Next, cycle through and interleave the bits of the binary numbers
    for (int i = 0; i < 32; i++) {
        int_binary[write_index++] = binary_x[i];
        int_binary[write_index++] = binary_y[i];
    }

    // Convert the interleaved number back to decimal and return
    int z_number = strtol(int_binary, NULL, 2);

    return z_number;
}

// This function will cycle through the array and assign it integer values from
// 1 to N^2 in Z-order
void fill_matrix(int *matrix, int N) {
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            matrix[i*N+j] = z_order2d(i, j) + 1;
        }
    }
}
