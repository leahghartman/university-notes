// Include all of the standard library headers needed for file I/O, containers,
// sorting, and timing.
#include <cstdio>
#include <chrono>
#include <ios>
#include <string>
#include <utility>
#include <vector>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <numeric>
#include <algorithm>

// The Matrix Market I/O library is written in C, so its header has to be
// wrapped in extern "C" for the C++ compiler to link against it correctly.
extern "C" {
    #include "mmio.h"
}

// ----------------------------------------------------------------------------
// -- STORAGE STRUCTS
// ----------------------------------------------------------------------------
// Dense: every element of the matrix, zeros included, stored in one flat 
// vector in row-major order. Element (i, j) is then at values[i * num_cols + j].
struct Dense {
    int num_rows;
    int num_cols;

    std::vector<double> values;  // Size: num_rows x num_cols
};

// Coordinate (COO): one (row, column, value) triplet stored per entry, kept
// in three parallel arrays. Therefore, entry k is at (rows[k], cols[k]) 
// with value values[k].
struct COO {
    int num_rows;
    int num_cols;
    int nnz;                     // Number of stored entries
    std::vector<int> rows;       // Size: nnz
    std::vector<int> cols;       // Size: nnz
    std::vector<double> values;  // Size: nnz
};

// Compressed sparse row (CSR): entries grouped per row. Row i's entries are 
// at positions row_ptr[i] through row_ptr[i+1] - 1 of col_ind and values.
struct CSR {
    int num_rows;
    int num_cols;
    int nnz;                     // Number of stored entries
    std::vector<int> row_ptr;    // Size: num_rows + 1
    std::vector<int> col_ind;    // Size: nnz
    std::vector<double> values;  // Size: nnz
};

// ELLPACK (ELL): every row padded to the same length K, then stored in
// column-major order. The k-th entry of row i is at index k * num_rows + i.
struct ELL {
    int num_rows;
    int num_cols;
    int K;                       // Padded row width; length of the longest row
    std::vector<int> col_ind;    // Size: num_rows x K
    std::vector<double> values;  // Size: num_rows x K
};

// Jagged diagonal storage (JDS): rows sorted from longest to shortest, then
// stored one "jagged diagonal" at a time.
struct JDS {
    int num_rows;
    int num_cols;
    int nnz;
    int num_jagged_diagonals;    // Equal to the length of the longest row
    std::vector<int> row_perm;   // Size: num_rows
    std::vector<int> iter_ptr;   // Size: num_jagged_diagonals + 1
    std::vector<int> col_ind;    // Size: nnz
    std::vector<double> values;  // Size: nnz
};

// ----------------------------------------------------------------------------
// -- SHARED READERS/WRITERS
// ----------------------------------------------------------------------------
// The below function will read a Matrix Market file using their own I/O
// implementation. Most of this code references their website and the examples
// that were provided there. It returns 0 on success and 1 if there is some 
// error.
//
// Something that is also worth noting is that this function reads the data 
// straight into a COO format. From there, we can convert to other matrix 
// formats.
int matrix_reader(const std::string &mmfile, COO &coo) {

    // The Matrix Market I/O is written in C, not C++, hence why fopen is used.
    FILE *f = fopen(mmfile.c_str(), "r");
    if (f == NULL) {
        std::cout << "Error: Could not open matrix market file: " << mmfile << "\n";
        return 1;
    }

    // Parses the Matrix Market header line into a typecode which describes
    // the matrix itself (e.g. real, coordinate, general or symmetric).
    MM_typecode matcode{};
    if (mm_read_banner(f, &matcode) != 0) {
        std::cout << "Error: Could not process matrix market banner!" << "\n";
        fclose(f);
        return 1;
    }

    // Skips the comment lines and records the number of rows, columns, and
    // the number of entries listed in the file.
    int num_rows, num_cols, non_zero;
    if (mm_read_mtx_crd_size(f, &num_rows, &num_cols, &non_zero) != 0) {
        fclose(f);
        return 1;
    }

    // Check if the matrix is symmetric. If this is the case, then the Matrix
    // Market file will only contain one triangle and the off-diagonal entries
    // will need to be mirrored across the diagonal.
    bool is_symmetric = mm_is_symmetric(matcode);

    // Store these values in our COO struct for later
    coo.num_rows = num_rows;
    coo.num_cols = num_cols;

    // Make sure to clear the old COO data
    coo.rows.clear();
    coo.cols.clear();
    coo.values.clear();

    // This preallocates capacity to avoid repeated reallocation. This is 
    // doubled for symmetric matrices as the Matrix Market file, as mentioned
    // above, will only contain half of the entries.
    coo.rows.reserve(is_symmetric ? 2 * non_zero : non_zero);
    coo.cols.reserve(is_symmetric ? 2 * non_zero : non_zero);
    coo.values.reserve(is_symmetric ? 2 * non_zero : non_zero);

    // Read the actual data points; once per entry line in the file
    for (int i = 0; i < non_zero; i++) {
        
        // Initialize holders for the current entry's row index, column index,
        // and value at that location.
        int row, col;
        double value;

        // Read on line's worth of data and convert to C++ 0-indexing instead
        // of C's 1-indexing.
        fscanf(f, "%d %d %lg\n", &row, &col, &value);
        row--;
        col--;

        // Append this entry to the end of the COO arrays.
        coo.rows.push_back(row);
        coo.cols.push_back(col);
        coo.values.push_back(value);

        // If the matrix is symmetric, append a second copy, but with the row
        // and column switched.
        if (is_symmetric && row != col) {
            coo.rows.push_back(col);
            coo.cols.push_back(row);
            coo.values.push_back(value);
        }
    }
   
    // Set the number stored entries. This comes from the stored vector's size 
    // so it will include mirrored entries, unlike what comes directly from 
    // the file.
    coo.nnz = coo.values.size();

    fclose(f);
    return 0;
}

// The below function reads an input vector from a text file. It expects a file
// with no header and numbers separated by new lines. It returns 0 on success 
// and 1 if the file can't be opened.
int vector_reader(const std::string &vecfilein, std::vector<double> &vector) {
    std::ifstream vecfile(vecfilein);
    if (!vecfile.is_open()) {
        std::cout << "Error: Could not open vector input file: " << vecfilein << "\n";
        return 1;
    }

    // This while loop finds the next available piece of data and places it
    // in the initialized value variable. It stops at the end of the file.
    double value{};
    while (vecfile >> value) {
        vector.push_back(value);
    }
    vecfile.close();
    return 0;
}

// The below function writes a result vector to a given text file, one value
// per line. It returns 0 on success and 1 if the file can't be opened.
int result_writer(const std::string &vecfileout, std::vector<double> &vector) {
    std::ofstream vecfile(vecfileout);
    if (!vecfile.is_open()) {
        std::cout << "Error: Could not open vector output file: " << vecfileout << "\n";
        return 1;
    }

    // Write every value in exponent form and set the precision to 16 digits
    // after the decimal point (17 significant digits in total).
    vecfile << std::scientific << std::setprecision(16);
    for (const double &value : vector) {
        vecfile << value << "\n";
    }
    vecfile.close();
    return 0;
}

// ----------------------------------------------------------------------------
// -- FILL FUNCTIONS
// -- Note in this section that each fill function converts the COO matrix 
// -- produced by the reader to the correct matrix format.
// ----------------------------------------------------------------------------
// The below function builds a fully dense representation of the matrix, with 
// zeros included. The storage choice here is one contiguous vector in row-major
// order. So it's essentially a 2D matrix stored flat.
Dense dense_fill(const COO &coo) {

    // Initialize a dense matrix object and assign the correct number of rows
    // and columns to the correct fields.
    Dense dense;
    dense.num_rows = coo.num_rows;
    dense.num_cols = coo.num_cols;

    // Assign zeros to every entry of the matrix
    dense.values.resize(dense.num_rows * dense.num_cols, 0.0);

    // Fill the matrix with its actual values. Any position not listed in the
    // COO matrix will remain zero from the initialization.
    for (int i = 0; i < coo.nnz; i++) {
        int row = coo.rows[i];
        int col = coo.cols[i];
        double value = coo.values[i];
        dense.values[row * coo.num_cols + col] = value;
    }
    return dense;
}

// The below function converts a COO object into a compressed sparse row (CSR)
// format. The approach for this format is to group the nonzeros by row and then
// counting each row's number of entries, turn those counts into the starting 
// position of each row with a running sum, then place every COO entry into its
// row's section of the col_ind and value arrays.
CSR csr_fill(const COO &coo) {

    // Initialize a CSR matrix object and assign the correct number of rows,
    // columns, and nonzeros to the correct fields.
    CSR csr{};
    csr.num_rows = coo.num_rows;
    csr.num_cols = coo.num_cols;
    csr.nnz      = coo.nnz;

    // Count the number of entries in each row. Row i's count is stored at 
    // row_ptr[i + 1], leaving row_ptr[0] = 0 for the running sum below.
    csr.row_ptr.resize(csr.num_rows + 1, 0);
    for (int i = 0; i < csr.nnz; i++) {
        int row = coo.rows[i];
        csr.row_ptr[row + 1] += 1;
    }

    // Next, cycle through the row_ptr vector again and calculate a running sum.
    // Afterwards, row_ptr[i] is the position where row i's entries start, and
    // row_ptr[num_rows] is the total number of entries.
    for (int i = 1; i < csr.row_ptr.size(); i++) {
        csr.row_ptr[i] += csr.row_ptr[i - 1];
    }

    // Place each COO entry properly. next[row] tracks the next open position
    // in each row's section, starting at the beginning of the row and moving
    // forward by one each time an entry is placed.
    std::vector<int> next(csr.row_ptr);
    csr.col_ind.resize(csr.nnz);
    csr.values.resize(csr.nnz);
    for (int i = 0; i < csr.nnz; i++) {
        int row = coo.rows[i];
        csr.values[next[row]]  = coo.values[i];
        csr.col_ind[next[row]] = coo.cols[i];

        next[row] += 1;
    }
    return csr;
}

// The below function converts a COO object into an ELL format. Every
// row is padded to the length of the longest row, K, and the resulting
// num_rows x K arrays are stored in column-major order, so that the k-th entry
// of every row is stored together.
ELL ell_fill(const COO &coo) {

    // Initialize an ELL matrix object and assign the correct number of rows
    // and columns to the correct fields.
    ELL ell{};
    ell.num_rows = coo.num_rows;
    ell.num_cols = coo.num_cols;

    // First pass: count the entries in each row and find K, the maximum count
    // over all rows. Every row will be padded to this length.
    std::vector<int> counts(ell.num_rows, 0);
    for (int i = 0; i < coo.nnz; i++) {
        int row = coo.rows[i];
        counts[row] += 1;
    }
    ell.K = *std::max_element(counts.begin(), counts.end());

    // Allocate with the padding already in place. resize() fills every slot 
    // with 0, so any slot that isn't filled below stays as a padding entry
    // with value 0 and column index 0.
    ell.col_ind.resize(ell.num_rows * ell.K);
    ell.values.resize(ell.num_rows * ell.K);

    // Finally, place each COO entry properly. next[row] tracks how many entries
    // of each row have been placed so far, so the k-th entry of row i goes to
    // the column-major index k * num_rows + i.
    std::vector<int> next(ell.num_rows, 0);
    for (int i = 0; i < coo.nnz; i++) {
        int row = coo.rows[i];
        ell.values[next[row] * ell.num_rows + row]  = coo.values[i];
        ell.col_ind[next[row] * ell.num_rows + row] = coo.cols[i];

        next[row] += 1;
    }
    return ell;
}

// The below function converts a COO object into a JDS format. The rows are 
// sorted from longest to shortest, and the entries are then stored one jagged 
// diagonal at a time: first the 1st entry of every row, then the 2nd entry of 
// every row that has one, and so on. Because the rows are sorted, each jagged 
// diagonal covers a contiguous block of sorted rows starting from the first, 
// so no padding is needed.
JDS jds_fill(const COO &coo) {

    // Initialize a JDS matrix object and assign the correct number of rows 
    // and columns to the correct fields.
    JDS jds{};
    jds.num_rows = coo.num_rows;
    jds.num_cols = coo.num_cols;
    jds.nnz      = coo.nnz;

    // Use the same loop as the ELL case to count the entries in each row. The
    // number of jagged diagonals is the length of the longest row.
    std::vector<int> counts(jds.num_rows, 0);
    for (int i = 0; i < jds.nnz; i++) {
        int row = coo.rows[i];
        counts[row] += 1;
    }
    jds.num_jagged_diagonals = *std::max_element(counts.begin(), counts.end());

    // Create row_perm and fill it with 0, 1, ..., num_rows - 1.
    jds.row_perm.resize(jds.num_rows);
    std::iota(jds.row_perm.begin(), jds.row_perm.end(), 0);

    // Sort the rows from longest to shortest. After sorting, row_perm[p] should
    // be the original index of the row in sorted position p. 
    std::stable_sort(jds.row_perm.begin(), jds.row_perm.end(), [&](int a, int b) {
        return counts[a] > counts[b];
    });

    // Fill in iter_ptr. 
    jds.iter_ptr.resize(jds.num_jagged_diagonals + 1, 0);
    for (int i = 0; i < jds.num_rows; i++) {
        int num_entries = counts[i];
        for (int j = 0; j < num_entries; j++) {
            jds.iter_ptr[j + 1] += 1;
        }
    }

    // Next, cycle through the row_ptr vector again and calculate a running sum
    for (int i = 1; i < jds.iter_ptr.size(); i++) {
        jds.iter_ptr[i] += jds.iter_ptr[i - 1];
    }

    // Allocate
    jds.col_ind.resize(jds.nnz);
    jds.values.resize(jds.nnz);

    // Finally, place each COO entry properly
    std::vector<int> next(jds.num_rows, 0);
    std::vector<int> pos(jds.num_rows, 0);
    for (int p = 0; p < jds.row_perm.size(); p++) {
        pos[jds.row_perm[p]] = p;
    }

    for (int i = 0; i < jds.nnz; i++) {
        int row = coo.rows[i];
        int s = next[row];
        jds.values[jds.iter_ptr[s] + pos[row]]  = coo.values[i];
        jds.col_ind[jds.iter_ptr[s] + pos[row]] = coo.cols[i];

        next[row] += 1;
    }
    return jds;
}

// ----------------------------------------------------------------------------
// -- MATVEC FUNCTIONS
// ----------------------------------------------------------------------------
// The below function performs the matvec for a dense matrix. For each row, it
// multiplies every element of the row by the matching element of the input
// vector, including all of the zeros, and sums the products.
void dense_matvec(const Dense &dense, 
                  const std::vector<double> &vector,
                  std::vector<double> &result) {

    const int num_cols = dense.num_cols;
    const int num_rows = dense.num_rows;
    for (int i = 0; i < num_rows; i++) {
        // Accumulate row i's dot product in a local variable, then write it
        // to the result once the row is finished.
        double sum{0.0};
        for (int j = 0; j < num_cols; j++) {
            sum += dense.values[(i * num_cols) + j] * vector[j];
        }
        result[i] = sum;
    }
}

// The below function performs the matvec for a COO matrix. The entries are not
// grouped by row, so each entry's product is added directly into the result at
// that entry's row.
void coo_matvec(const COO &coo,
                const std::vector<double> &vector, 
                std::vector<double> &result) {

    // The result is built up by adding to it, so it has to start at zero.
    result.assign(coo.num_rows, 0.0);
    
    for (int i = 0; i < coo.nnz; i++) {
        const int row = coo.rows[i];
        const int col = coo.cols[i];
        const double value = coo.values[i];

        result[row] += value * vector[col];
    }
}

// The below function performs the matvec for a CSR matrix. Since the entries
// are grouped by row, each row's dot product is computed in one go, and its
// result is written exactly once.
void csr_matvec(const CSR &csr, 
                const std::vector<double> &vector, 
                std::vector<double> &result) {

    for (int i = 0; i < csr.num_rows; i++) {
        double sum{0.0};
        for (int j = csr.row_ptr[i]; j < csr.row_ptr[i+1]; j++) {
            // Row i's entries are at positions row_ptr[i] through
            // row_ptr[i+1] - 1 of the values and col_ind arrays.
            sum += csr.values[j] * vector[csr.col_ind[j]];
        }
        result[i] = sum;
    }
}

// The below function performs the matvec for an ELL matrix. Because the data
// is stored in column-major order, the outer loop goes over the K padded
// columns and the inner loop goes over every row, adding each row's k-th entry
// into its result. Padding entries have a value of 0, so they add nothing.
void ell_matvec(const ELL &ell, 
                const std::vector<double> &vector,
                std::vector<double> &result) {

    // The result is built up over K passes, so it has to start at zero.
    result.assign(ell.num_rows, 0.0);

    for (int i = 0; i < ell.K; i++) {
        for (int j = 0; j < ell.num_rows; j++) {
            // The i-th entry of row j is at column-major index i * num_rows + j
            int idx = i * ell.num_rows + j;
            result[j] += ell.values[idx] * vector[ell.col_ind[idx]];
        }
    }
}

// The below function performs the matvec for a JDS matrix. The outer loop goes
// over the jagged diagonals and the inner loop over the entries in each one.
// The position of an entry within its jagged diagonal is its row's sorted
// position, and row_perm maps that back to the original row of the result.
void jds_matvec(const JDS &jds, 
                const std::vector<double> &vector, 
                std::vector<double> &result) {

    // The result is built up over many passes, so it has to start at zero.
    result.assign(jds.num_rows, 0.0);

    for (int i = 0; i < jds.num_jagged_diagonals; i++) {
        for (int j = jds.iter_ptr[i]; j < jds.iter_ptr[i+1]; j++) {
            // j - iter_ptr[i] is the entry's offset within jagged diagonal i,
            // which equals its row's sorted position.
            int row = jds.row_perm[j - jds.iter_ptr[i]];
            result[row] += jds.values[j] * vector[jds.col_ind[j]];
        }
    }
}

// ----------------------------------------------------------------------------
// -- MAIN FUNCTION
// ----------------------------------------------------------------------------
// Main function for the sparse matrix-vector multiplication (SpMV) assignment.
// Returns 0 on success, 1 on any input, read, or write error.
int main(int argc, char *argv[]) {
    // First, check that we have enough/not too many arguments to run the code.
    if (argc != 6) {
        std::cout << "Error: You must have exactly 5 arguments! Usage: " << argv[0] 
                  << " <spfmt> <nmults> <mmfile> <vecfilein> <vecfileout>" << "\n";
        return 1;
    }

    // Validate the sparse format keyword against the list of supported formats.
    std::string spfmt = argv[1];
    std::vector<std::string> valid_options = {"DEN", "COO", "CSR", "ELL", "JDS"};
    if (std::find(valid_options.begin(), valid_options.end(), spfmt) == valid_options.end()) {
        std::cout << "Error: Invalid argument " << spfmt 
                  << ". Must be DEN, COO, CSR, ELL, or JDS!" << "\n";
        return 1;
    }

    // Check and make sure that the user inputs for <mmfile> and <vecfilein> exist
    // and can be opened. If not, produce an error message and quit.
    std::string mmfile    = argv[3];
    std::string vecfilein = argv[4];
    if (!std::ifstream(mmfile).good()) {
        std::cout << "Error: Provided <mmfile> does not exist!" << "\n";
        return 1;
    }
    
    if (!std::ifstream(vecfilein).good()) {
        std::cout << "Error: Provided <vecfilein> does not exist!" << "\n";
        return 1;
    }

    // All input checks are done. Read the Matrix Market file into COO format,
    // which serves as the common starting point for building every other format.
    COO coo;
    if (matrix_reader(mmfile, coo) != 0) {
        return 1;
    }

    // Also read the starting vector from <vecfilein>.
    std::vector<double> vector{};
    if (vector_reader(vecfilein, vector) != 0) {
        return 1;
    }

    // Allocate the output vector b, which will have a length equal to the 
    // number of rows. 
    std::vector<double> b(coo.num_rows, 0.0);
    int nmults = std::stoi(argv[2]);

    // Timing: only the matvec loop is timed.
    std::chrono::steady_clock::time_point start, end;

    // Build the matrix in the requested format, then apply it nmults times.
    // After each input, b and x are switched so the result becomes the input
    // to the next multiplication. Swapping should just exchange pointers, so
    // no data is copied. When the loop ends, the final result will be stored 
    // in 'vector'.
    if (spfmt == "DEN") {
        // Dense: full num_rows x num_columns storage, including zeros.
        Dense dense = dense_fill(coo);

        start = std::chrono::steady_clock::now();
        for (int i = 0; i < nmults; i++) {
            dense_matvec(dense, vector, b);
            std::swap(vector, b);
        }
        end = std::chrono::steady_clock::now();
    } else if (spfmt == "COO") {
        // Coordinate: use the (row, column, value) triplets directly, no conversion.
        start = std::chrono::steady_clock::now();
        for (int i = 0; i < nmults; i++) {
            coo_matvec(coo, vector, b);
            std::swap(vector, b);
        }
        end = std::chrono::steady_clock::now();
    } else if (spfmt == "CSR") {
        // Compressed Sparse Row: row pointers + column indices + values.
        CSR csr = csr_fill(coo);

        start = std::chrono::steady_clock::now();
        for (int i = 0; i < nmults; i++) {
            csr_matvec(csr, vector, b);
            std::swap(vector, b);
        }
        end = std::chrono::steady_clock::now();
    } else if (spfmt == "ELL") {
        // ELL: each row padded to the length of the longest row.
        ELL ell = ell_fill(coo);

        start = std::chrono::steady_clock::now();
        for (int i = 0; i < nmults; i++) {
            ell_matvec(ell, vector, b);
            std::swap(vector, b);
        }
        end = std::chrono::steady_clock::now();
    } else if (spfmt == "JDS") {
        // Jagged Diagonal Storage: rows sorted by nonzero count, stored by
        // jagged diagonals, with a permutation to map back to the original
        // order.
        JDS jds = jds_fill(coo);

        start = std::chrono::steady_clock::now();
        for (int i = 0; i < nmults; i++) {
            jds_matvec(jds, vector, b);
            std::swap(vector, b);
        }
        end = std::chrono::steady_clock::now();
    }

    // Write the final vector result to <vecfileout>.
    std::string vecfileout = argv[5];
    if (result_writer(vecfileout, vector) != 0) {
        return 1;
    }

    // Average time per matvec in seconds. Printed to stderr so it stays out of
    // the result file the autograder checks.
    std::chrono::duration<double> elapsed = end - start;
    double avg_time = (nmults > 0) ? elapsed.count() / nmults : 0.0;
    std::cerr << "Average SpMV time (" << spfmt << ", " << nmults << " mults): "
              << avg_time << " s\n";

    return 0;
}
