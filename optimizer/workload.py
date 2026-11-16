"""Fixed integer workload. No user-provided executable code is accepted."""
MODULUS = 1_000_000_007
MAX_N = 1_000_000
FIXTURES = (0, 1, 2, 7, 31, 999, 10_000, MAX_N)
PYTHON_SOURCE = '''import sys
n = int(sys.argv[1])
if not 0 <= n <= 1_000_000:
    raise ValueError("n outside workload contract")
total = 0
for i in range(1, n + 1):
    total = (total + i * i) % 1_000_000_007
print(total)
'''
CPP_SOURCE = '''#include <cstdint>
#include <cstdlib>
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const auto n = std::strtoll(argv[1], nullptr, 10);
    if (n < 0 || n > 1000000) return 2;
    std::int64_t total = 0;
    for (std::int64_t i = 1; i <= n; ++i) {
        total = (total + i * i) % 1000000007LL;
    }
    std::cout << total << '\\n';
    return 0;
}
'''
WRONG_SOURCE = CPP_SOURCE.replace('i <= n', 'i < n')
COMPILE_ERROR_SOURCE = '#include <iostream>\nint main() { deliberate_compile_error; }\n'
CANDIDATES = {
    'correct': {'label': 'Reviewed C++ loop', 'source': CPP_SOURCE},
    'wrong': {'label': 'Off-by-one regression', 'source': WRONG_SOURCE},
    'compile-error': {'label': 'Compile-error fixture', 'source': COMPILE_ERROR_SOURCE},
}

def reference(n):
    """Independent closed-form oracle using arbitrary-precision Python integers."""
    if type(n) is not int or not 0 <= n <= MAX_N:
        raise ValueError('n outside workload contract')
    return (n * (n + 1) * (2 * n + 1) // 6) % MODULUS
