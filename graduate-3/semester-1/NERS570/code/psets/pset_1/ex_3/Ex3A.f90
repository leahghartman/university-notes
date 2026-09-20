    !This function will cycle through the array and assign it integer values
    ! from 1 to N^2 in Z-order
    subroutine fill_matrix(matrix, N) bind(c, name="fill_matrix")
       use iso_c_binding
       implicit none

       ! Declare all of the proper inputs and outputs to the subroutine
       integer(c_int), intent(in), value :: N
       integer(c_int), intent(inout) :: matrix(N, N)

       ! Declare all of the other variables that we need in this subroutine
       integer :: i, j  ! Just loop counters
       integer :: z_number

       do i = 1, N
          do j = 1, N
             call z_order2d(i - 1, j - 1, z_number)
             matrix(i, j) = z_number + 1
          end do
       end do

    end subroutine fill_matrix

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
       write (binary_x, '(B16.16)') x
       write (binary_y, '(B16.16)') y

       ! (2) Cycle through and interleave the bits of the binary numbers
       do i = 1, 32
          int_binary(2*i - 1:2*i - 1) = binary_x(i:i)
          int_binary(2*i:2*i) = binary_y(i:i)
       end do

       ! (3) Convert the interleaved number back to decimal and return
       read (int_binary, '(B32.32)') z_number

    end subroutine z_order2d
