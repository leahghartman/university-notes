#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

// This function will calculate and return the Z number for a given two-dimensional
// coordinate. It proceeds through the following three steps:
//      (1) Converts x and y into binary numbers
//      (2) Interleaves the bits of the binary numbers
//      (3) Converts the interleaved number back to decimal and returns it
int z_order2d(int x, int y) {
    // Now, we don't even have to do anything with the binary representation
    // itself, we just need to use the integer values
    
    int magic_number_0 = 51;
    int magic_number_1 = 85;

    x = (x | (x << 2)) & magic_number_0;
    y = (y | (y << 2)) & magic_number_0;

    // Do the same thing, again
    x = (x | (x << 1)) & magic_number_1;
    y = (y | (y << 1)) & magic_number_1;

    // Now shift the y bits to the left once and combine the two
    int z_number = (y | (x << 1));
    
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

// Define main function with these arguments so we can accept command line 
// input from the user when needed.
int main(int argc, char *argv[]) {
    // First, check that we have enough arguments to perform calculations.
    if (argc < 2) {
        printf("Error: Missing an argument! Usage: %s <2|4|8|16>\n", argv[0]);
        return 1;
    }

    int N;
    if (strcmp(argv[1], "2") == 0)       { N = 2; }
    else if (strcmp(argv[1], "4") == 0)  { N = 4; }
    else if (strcmp(argv[1], "8") == 0)  { N = 8; }
    else if (strcmp(argv[1], "16") == 0) { N = 16; }
    else {
        printf("Error: Invalid argument '%s'. Must be 2, 4, 8, or 16!\n", argv[1]);
        return 1;
    }

    // Allocate the NxN matrix and call fill_matrix to fill it in
    int *matrix = malloc((N*N) * sizeof(int));
    fill_matrix(matrix, N);

    // Find the largest number in the matrix and calculate the largest width
    // we'll need to properly format the array/matrix.
    char width_probe[2];
    int width = snprintf(width_probe, sizeof(width_probe), "%d", N*N);

    // Once the matrix is filled, print it out in the proper format
    // Note the size of the prefix so that we can properly space the LHS of the array
    char *prefix = "A=[";
    int prefix_len = strlen(prefix);
 
    printf("%s", prefix);
    for (int i = 0; i < N; i++) {
        // For everything after the first row, we need to print a space that's 
        // as large as the prefix.
        if (i > 0) {
            printf("%*s", prefix_len, "");
        }

        // For all of the entries, print the numbers using the proper width, 
        // which we found above and is fixed to the largest number printed
        for (int j = 0; j < N; j++) {
            if (j == 0) {
                printf("%*d", width, matrix[i*N+j]);
            } else {
                printf(" %*d", width, matrix[i*N+j]);
            }
        }

        // If we're on the last line, print the ending bracket, otherwise print
        // a new line to continue the matrix
        if (i == N - 1) {
            printf("]\n");
        } else {
            printf("\n");
        }
    }
    return 0;
}
