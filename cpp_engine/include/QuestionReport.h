#pragma once
#include "Question.h"
#include "StudyPlanner.h"
#include <string>
#include <vector>
class QuestionReport {
public:
 static bool writeStudyPlan(const std::string&,const StudyPlan&,std::string* error=nullptr);
 static bool writePaperSummary(const std::string&,const std::vector<Question>&,std::string* error=nullptr);
 static std::string paperLabel(const PaperMetadata&);
};