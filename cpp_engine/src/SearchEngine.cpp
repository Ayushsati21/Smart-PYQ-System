#include "SearchEngine.h"
#include <algorithm>
#include <cmath>
#include <cctype>
#include <unordered_set>

std::vector<std::string> SearchEngine::tokenize(const std::string& text) {
    std::vector<std::string> tokens;
    std::string token;
    for (unsigned char ch : text) {
        if (std::isalnum(ch)) token.push_back(static_cast<char>(std::tolower(ch)));
        else if (!token.empty()) { tokens.push_back(token); token.clear(); }
    }
    if (!token.empty()) tokens.push_back(token);
    return tokens;
}

void SearchEngine::build(const std::vector<Question>& questions) {
    documents_ = questions;
    inverted_.clear();
    lengths_.assign(documents_.size(), 0);
    averageLength_ = 0.0;
    for (std::size_t doc = 0; doc < documents_.size(); ++doc) {
        const auto terms = tokenize(documents_[doc].normalized.empty()
                                    ? documents_[doc].text : documents_[doc].normalized);
        std::unordered_map<std::string, std::size_t> counts;
        for (const auto& term : terms) ++counts[term];
        lengths_[doc] = terms.size();
        averageLength_ += static_cast<double>(terms.size());
        for (const auto& entry : counts)
            inverted_[entry.first].push_back({doc, entry.second});
    }
    if (!documents_.empty()) averageLength_ /= static_cast<double>(documents_.size());
}

bool SearchEngine::matchesFilter(const PaperMetadata& m, const SearchFilter& f) const {
    return (f.subject.empty() || m.subject == f.subject) &&
           (f.academicYear.empty() || m.academicYear == f.academicYear) &&
           (f.examYear.empty() || m.examYear == f.examYear) &&
           (f.term.empty() || m.term == f.term);
}

SearchPage SearchEngine::search(const std::string& query, const SearchFilter& filter,
                                std::size_t page, std::size_t pageSize) const {
    SearchPage result;
    result.page = page;
    result.pageSize = pageSize;
    if (pageSize == 0) return result;
    const auto terms = tokenize(query);
    if (terms.empty()) return result;

    std::unordered_map<std::size_t, double> scores;
    constexpr double k1 = 1.5;
    constexpr double b = 0.75;
    const double n = static_cast<double>(documents_.size());
    for (const auto& term : terms) {
        const auto found = inverted_.find(term);
        if (found == inverted_.end()) continue;
        const double df = static_cast<double>(found->second.size());
        const double idf = std::log(1.0 + (n - df + 0.5) / (df + 0.5));
        for (const auto& posting : found->second) {
            const auto doc = posting.document;
            if (!matchesFilter(documents_[doc].paper, filter)) continue;
            const double length = static_cast<double>(lengths_[doc]);
            const double norm = averageLength_ > 0.0
                ? (1.0 - b + b * length / averageLength_) : 1.0;
            const double tf = static_cast<double>(posting.frequency);
            scores[doc] += idf * (tf * (k1 + 1.0)) / (tf + k1 * norm);
        }
    }

    std::vector<SearchHit> ranked;
    ranked.reserve(scores.size());
    for (const auto& item : scores) ranked.push_back({item.first, item.second});
    std::sort(ranked.begin(), ranked.end(), [](const SearchHit& a, const SearchHit& b) {
        if (a.score != b.score) return a.score > b.score;
        return a.questionIndex < b.questionIndex;
    });
    result.totalMatches = ranked.size();
    const std::size_t begin = std::min(page * pageSize, ranked.size());
    const std::size_t end = std::min(begin + pageSize, ranked.size());
    result.hits.assign(ranked.begin() + static_cast<std::ptrdiff_t>(begin),
                       ranked.begin() + static_cast<std::ptrdiff_t>(end));
    return result;
}

CorpusStats SearchEngine::stats() const {
    return {documents_.size(), inverted_.size(), averageLength_};
}
