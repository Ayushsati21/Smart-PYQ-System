#include "QuestionAnalytics.h"
#include <algorithm>
#include <map>
#include <set>
#include <unordered_map>

std::vector<YearCount> QuestionAnalytics::questionsByExamYear(const std::vector<Question>& questions) {
    std::map<std::string, std::size_t> counts;
    for (const auto& q : questions) ++counts[q.paper.examYear.empty() ? "Unknown" : q.paper.examYear];
    std::vector<YearCount> result;
    for (const auto& item : counts) result.push_back({item.first, item.second});
    return result;
}

std::vector<SubjectCount> QuestionAnalytics::questionsBySubject(const std::vector<Question>& questions) {
    struct Aggregate { std::set<std::string> papers; std::size_t questions = 0; };
    std::map<std::string, Aggregate> aggregates;
    for (const auto& q : questions) {
        const std::string subject = q.paper.subject.empty() ? "Unknown" : q.paper.subject;
        auto& a = aggregates[subject];
        ++a.questions;
        const std::string paper = !q.paper.paperCode.empty() ? q.paper.paperCode
            : q.paper.examYear + "|" + q.paper.term;
        a.papers.insert(paper);
    }
    std::vector<SubjectCount> result;
    for (const auto& item : aggregates)
        result.push_back({item.first, item.second.papers.size(), item.second.questions});
    return result;
}

std::vector<QuestionTrend> QuestionAnalytics::recurringQuestions(
    const std::vector<Question>& questions, std::size_t minimumOccurrences) {
    struct Aggregate { std::size_t count = 0; std::set<std::string> years; };
    std::map<std::string, Aggregate> groups;
    for (const auto& q : questions) {
        const std::string key = q.normalized.empty() ? q.text : q.normalized;
        if (key.empty()) continue;
        auto& group = groups[key];
        ++group.count;
        if (!q.paper.examYear.empty()) group.years.insert(q.paper.examYear);
    }
    std::vector<QuestionTrend> result;
    for (const auto& item : groups) if (item.second.count >= minimumOccurrences)
        result.push_back({item.first, item.second.count,
                          std::vector<std::string>(item.second.years.begin(), item.second.years.end())});
    std::sort(result.begin(), result.end(), [](const QuestionTrend& a, const QuestionTrend& b) {
        if (a.occurrences != b.occurrences) return a.occurrences > b.occurrences;
        return a.normalizedText < b.normalizedText;
    });
    return result;
}

double QuestionAnalytics::exactRepeatRate(const std::vector<Question>& questions) {
    if (questions.empty()) return 0.0;
    std::unordered_map<std::string, std::size_t> counts;
    for (const auto& q : questions) ++counts[q.fingerprint.empty() ? q.normalized : q.fingerprint];
    std::size_t repeated = 0;
    for (const auto& item : counts) if (item.second > 1) repeated += item.second;
    return static_cast<double>(repeated) / static_cast<double>(questions.size());
}
