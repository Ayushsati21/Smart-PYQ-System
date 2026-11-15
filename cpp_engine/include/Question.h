#pragma once
#include <string>

struct PaperMetadata {
    std::string course;
    std::string academicYear;
    std::string examYear;
    std::string subject;
    std::string term;
    std::string paperCode;
};

struct Question {
    std::string number, text, normalized, fingerprint;
    PaperMetadata paper;
};
