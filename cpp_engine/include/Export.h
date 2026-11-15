#pragma once
#include "Question.h"
#include <string>
#include <vector>

class QuestionExport {
public:
    static bool toCsv(const std::string& path, const std::vector<Question>& questions,
                      std::string* error = nullptr);
};
