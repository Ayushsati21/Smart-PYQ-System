#pragma once
#include "Question.h"
#include <cstddef>
#include <string>
#include <unordered_map>
#include <vector>

struct SearchFilter {
    std::string subject;
    std::string academicYear;
    std::string examYear;
    std::string term;
};
struct SearchHit {
    std::size_t questionIndex;
    double score;
};
struct SearchPage {
    std::vector<SearchHit> hits;
    std::size_t totalMatches = 0;
    std::size_t page = 0;
    std::size_t pageSize = 0;
};
struct CorpusStats {
    std::size_t documents = 0;
    std::size_t uniqueTerms = 0;
    double averageDocumentLength = 0.0;
};

class SearchEngine {
public:
    void build(const std::vector<Question>& questions);
    SearchPage search(const std::string& query, const SearchFilter& filter = {},
                      std::size_t page = 0, std::size_t pageSize = 20) const;
    CorpusStats stats() const;
private:
    struct Posting { std::size_t document; std::size_t frequency; };
    std::vector<Question> documents_;
    std::unordered_map<std::string, std::vector<Posting>> inverted_;
    std::vector<std::size_t> lengths_;
    double averageLength_ = 0.0;
    static std::vector<std::string> tokenize(const std::string& text);
    bool matchesFilter(const PaperMetadata&, const SearchFilter&) const;
};
