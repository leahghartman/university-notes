program Ex2B
    use iso_c_binding
    implicit none

    ! Define an interface for the 
    interface
        subroutine fill_matrix(matrix, N) bind(c, name="fill_matrix")
            use iso_c_binding
            implicit none

            integer(c_int), value :: N
            integer(c_int) :: matrix(N, N)
            
        end subroutine fill_matrix
    end interface

    integer(c_int) :: N
    integer :: i, width, prefix_len
    character(len=10) :: arg, exe_name
    integer, dimension(:, :), allocatable :: matrix
    character(len=*), parameter :: prefix = "A=["

    character(len=32) :: row_fmt

    ! First, check that we have enough arguments to perform calculations
    call get_command_argument(0, exe_name)
    if (command_argument_count() < 1) then
        print *, "Error: Missing an argument! Usage: ", trim(exe_name), " <2|4|8|16>"
        stop
    end if

    ! Check that the inputs the user provides are valid.
    call get_command_argument(1, arg)
    select case (trim(arg))
        case ("2") ; N = 2
        case ("4") ; N = 4
        case ("8") ; N = 8
        case ("16"); N = 16
        case default
            print *, "Error: Invalid argument '", trim(arg), "'. Must be 2, 4, 8, or 16!"
    end select

    ! Allocate the NxN matrix and call fill_matrix to fill it in
    allocate(matrix(N, N))
    call fill_matrix(matrix, N)

    ! Find the largest number in the matrix and calculate the largest width 
    ! we'll need to properly format the array/matrix.
    width = int(log10(real(N*N))) + 1
    prefix_len = len(prefix)
    write(row_fmt, '("(I", i0, ", ", i0, "(1X,I", i0, "))")') width, N-1, width

    ! Once the matrix is filled, print it out in the proper format.
    ! First, print the prefix to the terminal, then print the first row of the
    ! matrix using our pre-calculated row format. Then, write a new line.
    write(*, '(A)', advance='no') prefix
    write(*, row_fmt, advance='no') matrix(1, :)
    write(*, '(A)') ''
    do i = 2, N
        ! For every row after the first, add spacing equal to the prefix length.
        ! Then, in the row format we found, write the row to the terminal.
        write(*, '(A)', advance='no') repeat(' ', prefix_len)
        write(*, row_fmt, advance='no') matrix(i,:)

        ! If we're on the last row of the matrix, print the ending bracket. 
        ! Otherwise, print a new line.
        if (i == N) then
            write(*, "(A)") "]"
        else
            write(*, "(A)") ''
        end if
    end do

    ! Deallocate the matrix once we're done
    deallocate(matrix)

end program Ex2B
