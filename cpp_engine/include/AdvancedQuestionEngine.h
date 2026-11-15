#pragma once

#include "Question.h"
#include <cstddef>
#include <string>
#include <unordered_map>
#include <vector>

namespace smartpyq {

struct AdvancedSearchOptions {
    std::string subject;
    std::string examYear;
    std::string term;
    std::size_t offset = 0;
    std::size_t limit = 20;
    double minimumScore = 0.0;
};

struct AdvancedSearchResult {
    std::size_t questionIndex = 0;
    double score = 0.0;
    std::vector<std::string> matchedTerms;
};

struct QuestionDifficulty {
    std::size_t questionIndex = 0;
    double lexicalComplexity = 0.0;
    double conceptDensity = 0.0;
    double estimatedDifficulty = 0.0;
    std::string label;
};

struct SimilarQuestionPair {
    std::size_t firstIndex = 0;
    std::size_t secondIndex = 0;
    double cosineSimilarity = 0.0;
    double jaccardSimilarity = 0.0;
    double combinedScore = 0.0;
};

class AdvancedQuestionEngine {
public:
    void build(const std::vector<Question>& questions);
    std::vector<AdvancedSearchResult> search(
        const std::string& query,
        const AdvancedSearchOptions& options = {}) const;
    std::vector<SimilarQuestionPair> findSimilarPairs(
        double minimumScore = 0.65,
        std::size_t maximumPairs = 100) const;
    std::vector<QuestionDifficulty> estimateDifficulty() const;
    std::vector<std::string> explainSearch(const AdvancedSearchResult& result) const;
    std::size_t documentCount() const;
    std::size_t vocabularySize() const;
    double averageDocumentLength() const;

private:
    struct Posting {
        std::size_t document = 0;
        std::size_t frequency = 0;
    };
    struct DocumentVector {
        std::unordered_map<std::string, double> weights;
        double norm = 0.0;
        std::size_t tokenCount = 0;
    };

    std::vector<Question> documents_;
    std::vector<DocumentVector> vectors_;
    std::unordered_map<std::string, std::vector<Posting>> invertedIndex_;
    std::unordered_map<std::string, double> inverseDocumentFrequency_;
    double averageLength_ = 0.0;

    static std::vector<std::string> tokenize(const std::string& text);
    static std::string normalizeToken(const std::string& token);
    static double cosine(const DocumentVector& left, const DocumentVector& right);
    static double jaccard(const std::vector<std::string>& left,
                          const std::vector<std::string>& right);
    bool matches(const PaperMetadata& paper,
                 const AdvancedSearchOptions& options) const;
};

} // namespace smartpyq
