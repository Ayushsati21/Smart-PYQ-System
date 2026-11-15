#include "Export.h"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

int main() {
    const std::string path = "smart_pyq_export_test.csv";
    Question q;
    q.paper.paperCode = "DS-2024";
    q.paper.subject = "Data Structures";
    q.paper.academicYear = "2023-2024";
    q.paper.examYear = "2024";
    q.paper.term = "End Term";
    q.number = "2(a)";
    q.text = "Explain, \"compare\" stacks";
    q.fingerprint = "abc123";

    std::string error;
    assert(QuestionExport::toCsv(path, std::vector<Question>{q}, &error));
    std::ifstream input(path, std::ios::binary);
    assert(input.good());
    const std::string csv((std::istreambuf_iterator<char>(input)),
                          std::istreambuf_iterator<char>());
    assert(csv.find("\"Explain, \"\"compare\"\" stacks\"") != std::string::npos);
    assert(csv.find("\"DS-2024\",\"Data Structures\"") != std::string::npos);
    input.close();
    std::remove(path.c_str());
    return 0;
}
