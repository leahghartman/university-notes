CC       = gcc
CXX      = g++
CFLAGS   = -O3
CXXFLAGS = -O3 -std=c++11 -Wall -Wextra

all: SpMV.exe

# mmio.c is C code, so it is compiled with the C compiler (matches extern "C")
mmio.o: mmio.c mmio.h
	$(CC) $(CFLAGS) -c mmio.c -o mmio.o

SpMV.o: SpMV.cpp mmio.h
	$(CXX) $(CXXFLAGS) -c SpMV.cpp -o SpMV.o

SpMV.exe: SpMV.o mmio.o
	$(CXX) $(CXXFLAGS) SpMV.o mmio.o -o SpMV.exe

clean:
	rm -f *.o SpMV.exe

.PHONY: all clean
