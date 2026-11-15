#pragma once
#include "Question.h"
#include <cstddef>
#include <string>
#include <vector>

struct YearCount { std::string year; std::size_t count = 0; };
struct SubjectCount { std::string subject; std::size_t papers = 0; std::size_t questions = 0; };
struct QuestionTrend { std::string normalizedText; std::size_t occurrences = 0; std::vector<std::string> years; };

class QuestionAnalytics {
public:
    static std::vector<YearCount> questionsByExamYear(const std::vector<Question>&);
    static std::vector<SubjectCount> questionsBySubject(const std::vector<Question>&);
    static std::vector<QuestionTrend> recurringQuestions(const std::vector<Question>&,
                                                          std::size_t minimumOccurrences = 2);
    static double exactRepeatRate(const std::vector<Question>&);
};
