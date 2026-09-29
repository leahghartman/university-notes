#include <cstdio>
#include <ios>
#include <string>
#include <utility>
#include <vector>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <algorithm>
#include <filesystem>

extern "C" {
    #include "mmio.h"
}

namespace fs = std::filesystem;

struct Dense {
    int num_rows;
    int num_cols;

    std::vector<double> values;
};

struct COO {
    int num_rows;
    int num_cols;
    int nnz;
    std::vector<int> rows;
    std::vector<int> cols;
    std::vector<double> values;
};

struct CSR {
    int num_rows;
    int num_cols;
    int nnz;

    std::vector<int> row_ptr;    // Size: num_rows + 1
    std::vector<int> col_ind;    // Size: nnz
    std::vector<double> values;  // Size: nnz
};

struct ELL {
    int num_rows;
    int num_cols;
    int K;          // Padded row width; length of the longest row

    std::vector<int> col_ind;    // Size: num_rows x K
    std::vector<double> values;  // Size: num_rows x K
};

struct JDS {
    int num_rows;
    int num_cols;
    int nnz;
    int num_jagged_diagonals;

    std::vector<int> row_perm;   // Size: num_rows
    std::vector<int> iter_ptr;   // Size: num_jagged_diagonals
    std::vector<int> col_ind;    // Size: nnz
    std::vector<double> values;  // Size: nnz
};

// ----------------------------------------------------------------------------
// -- SHARED READERS/WRITERS
// ----------------------------------------------------------------------------
int matrix_reader(const fs::path &mmfile, COO &coo) {
    FILE *f = fopen(mmfile.c_str(), "r");
    if (f == NULL) {
        std::cout << "Error: Could not open matrix market file: " << mmfile << "\n";
        return 1;
    }

    MM_typecode matcode{};
    if (mm_read_banner(f, &matcode) != 0) {
        std::cout << "Error: Could not process matrix market banner!" << "\n";
        fclose(f);
        return 1;
    }

    // Read sizes (rows, columns)
    int num_rows, num_cols, non_zero;
    if (mm_read_mtx_crd_size(f, &num_rows, &num_cols, &non_zero) != 0) {
        fclose(f);
        return 1;
    }

    // Store these values in our struct for later
    coo.num_rows = num_rows;
    coo.num_cols = num_cols;
    coo.nnz      = non_zero;

    // Go ahead and resize vectors to the number of nonzero elements we now know
    coo.rows.resize(non_zero);
    coo.cols.resize(non_zero);
    coo.values.resize(non_zero);

    // Read the actual data points
    for (int i = 0; i < non_zero; i++) {
        fscanf(f, "%d %d %lg\n", &coo.rows[i], &coo.cols[i], &coo.values[i]);
        coo.rows[i]--;
        coo.cols[i]--;
    }
    fclose(f);
    return 0;
}

int vector_reader(const fs::path &vecfilein, std::vector<double> &vector) {
    std::ifstream vecfile(vecfilein.string());
    if (!vecfile.is_open()) {
        std::cout << "Error: Could not open vector input file: " << vecfilein << "\n";
        return 1;
    }

    double value{};
    // Finds the next available piece of data and places it in the value variable
    while (vecfile >> value) {
        vector.push_back(value);
    }

    vecfile.close();
    return 0;
}

int result_writer(const fs::path &vecfileout, std::vector<double> &vector) {
    // Create and open the output file stream
    std::ofstream vecfile(vecfileout.string());
    if (!vecfile.is_open()) {
        std::cout << "Error: Could not open vector output file: " << vecfileout << "\n";
        return 1;
    }

    vecfile << std::scientific << std::setprecision(16);
    for (const double &value : vector) {
        vecfile << value << "\n";
    }
    vecfile.close();
    return 0;
}

// ----------------------------------------------------------------------------
// -- FILL FUNCTIONS
// -- These functions provide ...
// ----------------------------------------------------------------------------
Dense dense_fill(const COO &coo) {

    //
    Dense dense;
    dense.num_rows = coo.num_rows;
    dense.num_cols = coo.num_cols;

    // Assign 0's to a matrix
    dense.values.resize(dense.num_rows * dense.num_cols, 0.0);

    // Fill the matrix with its actual values
    for (int i = 0; i < coo.nnz; i++) {
        int row = coo.rows[i];
        int col = coo.cols[i];
        double value = coo.values[i];
        dense.values[row * coo.num_cols + col] = value;
    }
    return dense;
}

CSR csr_fill(const COO &coo) {

    // Create, allocate, and assign 0's to a matrix
    CSR csr{};

    return csr;
}

ELL ell_fill(const COO &coo) {

    // Create, allocate, and assign 0's to a matrix
    ELL ell{};

    return ell;
}

JDS jds_fill(const COO &coo) {

    // Create, allocate, and assign 0's to a matrix
    JDS jds{};

    return jds;
}

// ----------------------------------------------------------------------------
// -- matvec FUNCTIONS
// -- These functions provide ...
// ----------------------------------------------------------------------------
void dense_matvec(const Dense &dense, 
                  const std::vector<double> &vector,
                  std::vector<double> &result) {

    const int num_cols = dense.num_cols;
    const int num_rows = dense.num_rows;
    for (int i = 0; i < num_rows; i++) {
        double sum{0.0};
        for (int j = 0; j < num_cols; j++) {
            sum += dense.values[(i * num_cols) + j] * vector[j];
        }
        result[i] = sum;
    }
}

void coo_matvec(const COO &coo,
                const std::vector<double> &vector, 
                std::vector<double> &result) {

    result.assign(coo.num_rows, 0.0);
    
    for (int i = 0; i < coo.nnz; i++) {
        const int row = coo.rows[i];
        const int col = coo.cols[i];
        const double value = coo.values[i];

        result[row] += value * vector[col];
    }
}

void csr_matvec(const CSR &csr, 
                const std::vector<double> &vector, 
                std::vector<double> &result) {

}

void ell_matvec(const ELL &ell, 
                const std::vector<double> &vector,
                std::vector<double> &result) {

}

void jds_matvec(const JDS &jds, 
                const std::vector<double> &vector, 
                std::vector<double> &result) {

}

// ----------------------------------------------------------------------------
// -- MAIN FUNCTION
// ----------------------------------------------------------------------------
int main(int argc, char *argv[]) {
    // First, check that we have enough arguments to run the code.
    if (argc != 6) {
        std::cout << "Error: Missing an argument! Usage: " << argv[0] 
                  << " <spfmt> <nmults> <mmfile> <vecfilein> <vecfileout>" << "\n";
        return 1;
    }

    // TODO: Add a check that nmults is a positive integer!!

    // Check that the inputs the user provides are valid.
    std::string spfmt = argv[1];
    std::vector<std::string> valid_options = {"DEN", "COO", "CSR", "ELL", "JDS"};
    if (std::find(valid_options.begin(), valid_options.end(), spfmt) == valid_options.end()) {
        std::cout << "Error: Invalid argument " << spfmt 
                  << ". Must be DEN, COO, CSR, ELL, or JDS!" << "\n";
        return 1;
    }

    // Check and make sure that the user inputs for <mmfile> and <vecfilein> exist.
    // If they don't, provide an error message and exit.
    fs::path mmfile    = argv[3];
    fs::path vecfilein = argv[4];
    if (!fs::exists(mmfile)) {
        std::cout << "Error: Provided <mmfile> does not exist!" << "\n";
        return 1;
    }
    
    if (!fs::exists(vecfilein)) {
        std::cout << "Error: Provided <vecfilein> does not exist!" << "\n";
        return 1;
    }

    // All checks on user input should now be complete. Next, we will read the 
    // Matrix Market file using their I/O.
    COO coo;
    if (matrix_reader(mmfile, coo) != 0) {
        return 1;
    }

    // Also read the vector from the <vecfilein> given by the user
    std::vector<double> vector{};
    if (vector_reader(vecfilein, vector) != 0) {
        return 1;
    }

    // Now, based on what sparse matrix format keyword the user provided, call 
    // that function to properly allocate and fill the matrix. Then, run the 
    // matvec for that format.
    std::vector<double> b(coo.num_rows, 0.0);
    int nmults = std::stoi(argv[2]);
    if (spfmt == "DEN") {
        Dense dense = dense_fill(coo);
        for (int i = 0; i < nmults; i++) {
            dense_matvec(dense, vector, b);
            std::swap(vector, b);
        }
    } else if (spfmt == "COO") {
        for (int i = 0; i < nmults; i++) {
            coo_matvec(coo, vector, b);
            std::swap(vector, b);
        }
    } else if (spfmt == "CSR") {
        CSR csr = csr_fill(coo);
        for (int i = 0; i < nmults; i++) {
            csr_matvec(csr, vector, b);
            std::swap(vector, b);
        }
    } else if (spfmt == "ELL") {
        ELL ell = ell_fill(coo);
        for (int i = 0; i < nmults; i++) {
            ell_matvec(ell, vector, b);
            std::swap(vector, b);
        }
    } else if (spfmt == "JDS") {
        JDS jds = jds_fill(coo);
        for (int i = 0; i < nmults; i++) {
            jds_matvec(jds, vector, b);
            std::swap(vector, b);
        }
    }

    // Write the final vector result to a file of the user's choice
    fs::path vecfileout = argv[5];
    if (result_writer(vecfileout, vector) != 0) {
        return 1;
    }

    return 0;
}
