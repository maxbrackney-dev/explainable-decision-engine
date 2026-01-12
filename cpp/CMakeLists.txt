cmake_minimum_required(VERSION 3.16)
project(decision_engine_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Expect pybind11 installed in the active venv
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
  OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

set(pybind11_DIR "${PYBIND11_CMAKE_DIR}")
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(decision_engine_core bindings.cpp engine.cpp)
target_include_directories(decision_engine_core PRIVATE ${Python3_INCLUDE_DIRS})