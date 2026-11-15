#include "MockExamGenerator.h"
#include "Engine.h"

#include <algorithm>
#include <cctype>
#include <random>
#include <unordered_map>
#include <unordered_set>

namespace {
std::string lower(std::string value) {
    for (char& ch : value) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    return value;
}

std::string fingerprintOf(const Question& question) {
    if (!question.fingerprint.empty()) return question.fingerprint;
    const std::string normalized = question.normalized.empty()
        ? TextNormalizer::normalize(question.text)
        : question.normalized;
    return SHA256::hash(normalized);
}

bool matches(const PaperMetadata& paper, const MockExamCriteria& criteria) {
    if (!criteria.subject.empty() && lower(paper.subject) != lower(criteria.subject)) return false;
    if (!criteria.term.empty() && lower(paper.term) != lower(criteria.term)) return false;
    if (!criteria.examYear.empty() && paper.examYear != criteria.examYear) return false;
    return true;
}
}

MockExam MockExamGenerator::generate(const std::vector<Question>& corpus,
                                     const MockExamCriteria& criteria) const {
    MockExam result;
    result.sourceQuestionCount = corpus.size();
    result.seed = criteria.seed;

    std::unordered_map<std::string, std::size_t> frequency;
    for (const auto& question : corpus) {
        if (matches(question.paper, criteria) && !question.text.empty()) {
            ++frequency[fingerprintOf(question)];
        }
    }

    std::vector<Question> candidates;
    std::unordered_set<std::string> selectedFingerprints;
    candidates.reserve(frequency.size());

    for (const auto& question : corpus) {
        if (question.text.empty() || !matches(question.paper, criteria)) continue;
        const std::string fingerprint = fingerprintOf(question);
        if (criteria.repeatedQuestionsOnly && frequency[fingerprint] < 2) continue;
        if (!selectedFingerprints.insert(fingerprint).second) continue;
        candidates.push_back(question);
    }

    result.eligibleUniqueCount = candidates.size();
    std::mt19937 generator(criteria.seed);
    std::shuffle(candidates.begin(), candidates.end(), generator);

    const std::size_t count = std::min(criteria.questionCount, candidates.size());
    result.questions.assign(candidates.begin(), candidates.begin() + count);
    return result;
}
