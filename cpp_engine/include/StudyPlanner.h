#pragma once
#include "Question.h"
#include <cstddef>
#include <string>
#include <vector>
struct StudyPriority {
 std::string questionNumber,questionText,subject;
 std::size_t appearances=0,distinctExamYears=0;
 double priorityScore=0.0;
 std::vector<std::string> years;
};
struct StudyPlan { std::vector<StudyPriority> priorities;std::size_t sourceQuestions=0,uniqueTopics=0; };
class StudyPlanner {
public:
 StudyPlan build(const std::vector<Question>& questions,std::size_t limit=20,std::size_t minimumAppearances=2)const;
 static std::string explain(const StudyPriority&);
};
