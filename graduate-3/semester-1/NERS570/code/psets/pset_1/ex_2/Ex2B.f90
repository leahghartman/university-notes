program Ex2B
    implicit none

    integer :: N
    character(len=10) :: arg, exe_name
    real, dimension(:, :), allocatable :: matrix

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

    ! Allocate the NxN matrix
    allocate(matrix(N, N))

    ! Deallocate the matrix once we're done
    deallocate(matrix)

contains

    ! To calculate a binary number, we need to go through the following steps:
    !   (1) Divide the decimal number by 2 and write down the remainder
    !   (2) Take the new quotient and divide by 2; write down the remainder
    !   (3) Continue dividing until the quotient becomes 0
    !   (4) Read the remainders in REVERSE ORDER -- this is the binary value
    !
    ! The following subroutine implements this.
    subroutine to_binary(quotient, binary, size)
        implicit none

        ! Input arguments
        integer, intent(in) :: quotient
        real, intent(inout) :: binary      ! TODO: need to change this to the actual type
        integer, intent(in) :: size

        ! We're going to fill the array starting at the back, so we can satisfy
        ! (4) easily.
        binary
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



    end subroutine to_binary

    ! This subroutine will calculate and return the Z number for a given two-dimensional
    ! coordinate. It proceeds through the following three steps:
    !   (1) Converts x and y into binary numbers
    !   (2) Interleaves the bits of the binary numbers
    !   (3) Converts the interleaved number back to decimal and returns it
    subroutine z_order2d


    end subroutine z_order2d

    ! some comment here about the function
    subroutine fill_matrix

    end subroutine fill_matrix


end program Ex2B
