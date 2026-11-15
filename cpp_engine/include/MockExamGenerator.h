#pragma once

#include "Question.h"
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

struct MockExamCriteria {
    std::string subject;
    std::string term;
    std::string examYear;
    std::size_t questionCount = 10;
    bool repeatedQuestionsOnly = false;
    std::uint32_t seed = 0;
};

struct MockExam {
    std::vector<Question> questions;
    std::size_t sourceQuestionCount = 0;
    std::size_t eligibleUniqueCount = 0;
    std::uint32_t seed = 0;
};

class MockExamGenerator {
public:
    MockExam generate(const std::vector<Question>& corpus,
                      const MockExamCriteria& criteria = {}) const;
};
