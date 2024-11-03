#include <stdio.h>
#include <stdlib.h>

int main() {
  int a = 1;
  while (a < 10) {
    a += 1;
    if (a % 2 == 0) {
      printf("%d\n", a);
    }
  }
  puts("Done");
}