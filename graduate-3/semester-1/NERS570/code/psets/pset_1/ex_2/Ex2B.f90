program Ex2B
    implicit none

    integer :: N, i, j, width
    character(len=10) :: arg, exe_name
    integer, dimension(:, :), allocatable :: matrix
    character(len=*), parameter :: prefix = "A=["

    character(len=32) :: row_fmt
    integer :: prefix_len

    ! First, check that we have enough arguments to perform calculations
    call get_command_argument(0, exe_name)
    if (command_argument_count() < 1) then
        print *, "Error: Missing an argument! Usage: ", trim(exe_name), " <2|4|8|16>"
        stop
    end if

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

    write(*, '(A)', advance='no') prefix
    write(*, row_fmt, advance='no') matrix(1, :)
    write(*, '(A)') ''
    do i = 2, N
        write(*, '(A)', advance='no') repeat(' ', prefix_len)
        write(*, row_fmt, advance='no') matrix(i,:)
        if (i == N) then
            write(*, "(A)") "]"
        else
            write(*, "(A)") ''
        end if
    end do

    ! Deallocate the matrix once we're done
    deallocate(matrix)

contains

    ! This subroutine will calculate and return the Z number for a given two-dimensional
    ! coordinate. It proceeds through the following three steps:
    !   (1) Converts x and y into binary numbers
    !   (2) Interleaves the bits of the binary numbers
    !   (3) Converts the interleaved number back to decimal and returns it
    subroutine z_order2d(x, y, z_number)
        implicit none

        ! Declare the proper inputs and outputs to the subroutine
        integer, intent(in)  :: x, y
        integer, intent(out) :: z_number

        ! Declare all of the other variables that we need in this subroutine
        character(len=32) :: binary_x, binary_y  ! To hold the binary versions of x and y
        character(len=64) :: int_binary          ! To hold the interleaved binary number
        integer           :: i                   ! Just a loop counter

        ! (1) Convert x and y to binary values
        write(binary_x, '(B16.16)') x
        write(binary_y, '(B16.16)') y

        ! (2) Cycle through and interleave the bits of the binary numbers
        do i = 1, 32
            int_binary(2*i-1 : 2*i-1) = binary_x(i:i)
            int_binary(2*i : 2*i)     = binary_y(i:i)
        end do

        ! (3) Convert the interleaved number back to decimal and return
        read(int_binary, '(B32.32)') z_number

    end subroutine z_order2d

    ! This function will cycle through the array and assign it integer values
    ! from 1 to N^2 in Z-order
    subroutine fill_matrix(matrix, N)
        implicit none

        ! Declare all of the proper inputs and outputs to the subroutine
        integer, dimension(:,:), allocatable, intent(inout) :: matrix
        integer, intent(in)                              :: N

        ! Declare all of the other variables that we need in this subroutine
        integer :: i, j  ! Just loop counters
        integer :: z_number

        do i = 1, N
            do j = 1, N
                call z_order2d(i-1, j-1, z_number)
                !print *, z_number
                matrix(i, j) = z_number + 1
            end do
        end do

    end subroutine fill_matrix

end program Ex2B
