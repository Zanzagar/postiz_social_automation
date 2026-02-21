---
name: cpp-testing
description: Google Test and Catch2 patterns, test fixtures, parameterized tests, GMock mocking, AddressSanitizer memory leak detection, benchmark testing
---
# C++ Testing Skill

## Google Test (gtest)

### Basic Tests
```cpp
#include <gtest/gtest.h>

TEST(DistanceTest, SamePointReturnsZero) {
    EXPECT_DOUBLE_EQ(distance(0, 0, 0, 0), 0.0);
}

TEST(DistanceTest, KnownDistance) {
    double result = distance(0, 0, 3, 4);
    EXPECT_NEAR(result, 5.0, 1e-10);
}

TEST(DistanceTest, NegativeCoordinates) {
    EXPECT_GT(distance(-1, -1, 1, 1), 0.0);
}
```

### Test Fixtures
```cpp
class GridTest : public ::testing::Test {
protected:
    void SetUp() override {
        grid = std::make_unique<Grid>(100, 100);
        grid->fill(0.0);
    }

    void TearDown() override {
        grid.reset();
    }

    std::unique_ptr<Grid> grid;
};

TEST_F(GridTest, DefaultValueIsZero) {
    EXPECT_DOUBLE_EQ(grid->at(0, 0), 0.0);
}

TEST_F(GridTest, SetAndGet) {
    grid->set(50, 50, 42.0);
    EXPECT_DOUBLE_EQ(grid->at(50, 50), 42.0);
}

TEST_F(GridTest, OutOfBoundsThrows) {
    EXPECT_THROW(grid->at(200, 200), std::out_of_range);
}
```

### Parameterized Tests
```cpp
struct VariogramTestCase {
    std::string model;
    double sill;
    double range;
    double nugget;
    double expected_at_half_range;
};

class VariogramTest : public ::testing::TestWithParam<VariogramTestCase> {};

TEST_P(VariogramTest, EvaluatesCorrectly) {
    auto [model, sill, range, nugget, expected] = GetParam();
    Variogram v(model, sill, range, nugget);
    EXPECT_NEAR(v.evaluate(range / 2), expected, 0.01);
}

INSTANTIATE_TEST_SUITE_P(Models, VariogramTest, ::testing::Values(
    VariogramTestCase{"spherical", 1.0, 10.0, 0.0, 0.5625},
    VariogramTestCase{"exponential", 1.0, 10.0, 0.0, 0.3935},
    VariogramTestCase{"gaussian", 1.0, 10.0, 0.0, 0.2212}
));
```

### Assertions Reference

| Assertion | Checks |
|-----------|--------|
| `EXPECT_EQ(a, b)` | `a == b` |
| `EXPECT_NE(a, b)` | `a != b` |
| `EXPECT_LT(a, b)` | `a < b` |
| `EXPECT_DOUBLE_EQ(a, b)` | Float equality (4 ULPs) |
| `EXPECT_NEAR(a, b, tol)` | `|a - b| < tol` |
| `EXPECT_TRUE(cond)` | Boolean true |
| `EXPECT_THROW(expr, type)` | Throws specific exception |
| `EXPECT_NO_THROW(expr)` | No exception thrown |
| `ASSERT_*` variants | Fatal — stops test on failure |

## GMock (Mocking)

```cpp
#include <gmock/gmock.h>

// Interface
class DataSource {
public:
    virtual ~DataSource() = default;
    virtual std::vector<double> read(const std::string& path) = 0;
    virtual bool write(const std::string& path, const std::vector<double>& data) = 0;
};

// Mock
class MockDataSource : public DataSource {
public:
    MOCK_METHOD(std::vector<double>, read, (const std::string&), (override));
    MOCK_METHOD(bool, write, (const std::string&, const std::vector<double>&), (override));
};

TEST(PipelineTest, ReadsFromSource) {
    MockDataSource source;
    EXPECT_CALL(source, read("data.csv"))
        .Times(1)
        .WillOnce(::testing::Return(std::vector<double>{1.0, 2.0, 3.0}));

    Pipeline pipeline(&source);
    auto result = pipeline.process("data.csv");
    EXPECT_EQ(result.size(), 3);
}
```

## Catch2 (Alternative)

```cpp
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>

TEST_CASE("Variogram evaluation", "[variogram]") {
    Variogram v("spherical", 1.0, 10.0, 0.0);

    SECTION("at zero distance") {
        REQUIRE(v.evaluate(0.0) == Catch::Approx(0.0));
    }

    SECTION("at range") {
        REQUIRE(v.evaluate(10.0) == Catch::Approx(1.0));
    }

    SECTION("beyond range") {
        REQUIRE(v.evaluate(20.0) == Catch::Approx(1.0));
    }
}

// BDD style
SCENARIO("Grid interpolation", "[grid]") {
    GIVEN("A 100x100 grid with known values") {
        Grid grid(100, 100);
        grid.set(0, 0, 10.0);
        grid.set(99, 99, 20.0);

        WHEN("interpolating the center point") {
            double result = grid.interpolate(50, 50);

            THEN("result is between known values") {
                REQUIRE(result > 10.0);
                REQUIRE(result < 20.0);
            }
        }
    }
}
```

## Memory Safety Testing

### AddressSanitizer (ASan)
```cmake
# CMakeLists.txt
if(ENABLE_SANITIZERS)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
endif()
```

```bash
# Build with sanitizers
cmake -DENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug ..
make && ctest

# Catches: buffer overflow, use-after-free, memory leaks, stack overflow
```

### Valgrind
```bash
valgrind --leak-check=full --show-leak-kinds=all ./test_binary
```

## Benchmark Testing

```cpp
#include <benchmark/benchmark.h>

static void BM_VariogramEval(benchmark::State& state) {
    Variogram v("spherical", 1.0, 10.0, 0.0);
    for (auto _ : state) {
        benchmark::DoNotOptimize(v.evaluate(5.0));
    }
}
BENCHMARK(BM_VariogramEval);

static void BM_GridInterpolation(benchmark::State& state) {
    int size = state.range(0);
    Grid grid(size, size);
    // ... fill grid ...
    for (auto _ : state) {
        benchmark::DoNotOptimize(grid.interpolate(size/2, size/2));
    }
}
BENCHMARK(BM_GridInterpolation)->Range(64, 4096);

BENCHMARK_MAIN();
```

## CMake Test Integration

```cmake
enable_testing()

# Google Test
find_package(GTest REQUIRED)
add_executable(tests
    test_variogram.cpp
    test_grid.cpp
    test_pipeline.cpp
)
target_link_libraries(tests GTest::gtest_main GTest::gmock)
gtest_discover_tests(tests)

# Or with FetchContent
include(FetchContent)
FetchContent_Declare(googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)
```

## Test Organization

```
project/
├── src/
│   ├── variogram.cpp
│   └── grid.cpp
├── include/
│   ├── variogram.h
│   └── grid.h
├── tests/
│   ├── CMakeLists.txt
│   ├── test_variogram.cpp    # Unit tests
│   ├── test_grid.cpp
│   ├── test_pipeline.cpp     # Integration tests
│   └── benchmarks/
│       └── bench_variogram.cpp
└── CMakeLists.txt
```
