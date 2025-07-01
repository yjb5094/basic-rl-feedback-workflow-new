#include <klee/klee.h>
#include <stdio.h>

// TEST CODE

int add(char x[10], int y, int z[111], double i, float j, long int k) {
    return x + y;
}

int main() {
    char x[10];
    klee_make_symbolic(x, sizeof(x), "x");
    int y;
    klee_make_symbolic(&y, sizeof(y), "y");
    int z[111];
    klee_make_symbolic(z, sizeof(z), "z");
    double i;
    klee_make_symbolic(&i, sizeof(i), "i");
    float j;
    klee_make_symbolic(&j, sizeof(j), "j");
    long int k;
    klee_make_symbolic(&k, sizeof(k), "k");
    add(x, y, z, i, j, k);
    return 0;
}