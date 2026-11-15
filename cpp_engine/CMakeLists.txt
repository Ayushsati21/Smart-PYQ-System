cmake_minimum_required(VERSION 3.16)
project(SmartPYQCppEngine LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(smart_pyq_cpp
    src/main.cpp
    src/TextNormalizer.cpp
    src/QuestionParser.cpp
    src/FrequencyAnalyzer.cpp
    src/SimilarityEngine.cpp
    src/SHA256.cpp
    src/Metadata.cpp
    src/SearchEngine.cpp
    src/QuestionAnalytics.cpp
    src/Export.cpp
)
target_include_directories(smart_pyq_cpp PRIVATE include)

add_executable(test_search_analytics
    tests/test_search_analytics.cpp
    src/SearchEngine.cpp
    src/QuestionAnalytics.cpp
)
target_include_directories(test_search_analytics PRIVATE include)
add_executable(test_engine_core
    tests/test_engine.cpp
    src/QuestionParser.cpp
    src/TextNormalizer.cpp
    src/SHA256.cpp
)
target_include_directories(test_engine_core PRIVATE include)

add_executable(test_export
    tests/test_export.cpp
    src/Export.cpp
)
target_include_directories(test_export PRIVATE include)

enable_testing()
add_test(NAME search_analytics COMMAND test_search_analytics)
add_test(NAME engine_core COMMAND test_engine_core)
add_test(NAME csv_export COMMAND test_export)
