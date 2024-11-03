long bar(long b) {
  return b + 1;
}

long foo(long a, long b) {
  return a + b;
}

long first(long a, long b) {
  return a;
}

long second(long a, long b) {
  return b;
}

long third(long a, long b, long c) {
  return c;
}

int third_int(int a, int b, int c) {
  return c;
}

int fourth_int(int a, int b, int c, int d) {
  return d;
}

int main(int argc, char** argv) {
  return foo(4, 5);
}