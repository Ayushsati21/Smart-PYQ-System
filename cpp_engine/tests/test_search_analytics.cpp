#include "SearchEngine.h"
#include "QuestionAnalytics.h"
#include <cassert>
#include <iostream>

static Question makeQuestion(std::string text, std::string subject, std::string year) {
    Question q;
    q.text = text; q.normalized = text; q.fingerprint = text;
    q.paper.subject = subject; q.paper.examYear = year; q.paper.paperCode = subject + year;
    return q;
}
int main() {
    std::vector<Question> docs{
        makeQuestion("Explain binary search algorithm", "DS", "2024"),
        makeQuestion("Explain linear search algorithm", "DS", "2025"),
        makeQuestion("Database normalization forms", "DBMS", "2024")
    };
    SearchEngine search; search.build(docs);
    SearchFilter filter; filter.subject = "DS";
    auto page = search.search("search algorithm", filter, 0, 10);
    assert(page.totalMatches == 2);
    assert(page.hits.size() == 2);
    auto years = QuestionAnalytics::questionsByExamYear(docs);
    assert(years.size() == 2);
    auto subjects = QuestionAnalytics::questionsBySubject(docs);
    assert(subjects.size() == 2);
    auto trends = QuestionAnalytics::recurringQuestions(docs);
    assert(trends.empty());
    std::cout << "Search and analytics tests passed.\n";
}
