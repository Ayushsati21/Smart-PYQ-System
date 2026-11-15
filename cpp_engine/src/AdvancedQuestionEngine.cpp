#include "AdvancedQuestionEngine.h"

#include <algorithm>
#include <cmath>
#include <cctype>
#include <sstream>
#include <unordered_set>

namespace smartpyq {
namespace {
constexpr double kBm25K1 = 1.35;
constexpr double kBm25B = 0.72;
constexpr double kEpsilon = 1e-12;

const std::unordered_set<std::string>& stopWords() {
    static const std::unordered_set<std::string> words = {
        "a", "an", "and", "are", "as", "at", "be", "been", "being",
        "by", "can", "could", "define", "describe", "do", "does", "for",
        "from", "give", "has", "have", "how", "in", "into", "is", "it",
        "its", "of", "on", "or", "state", "such", "that", "the", "their",
        "these", "this", "those", "to", "using", "was", "were", "what",
        "when", "where", "which", "who", "why", "will", "with", "would"
    };
    return words;
}

bool containsIgnoreCase(const std::string& value, const std::string& expected) {
    if (expected.empty()) return true;
    auto lower = [](unsigned char c) { return static_cast<char>(std::tolower(c)); };
    std::string a(value.size(), '\0');
    std::string b(expected.size(), '\0');
    std::transform(value.begin(), value.end(), a.begin(), lower);
    std::transform(expected.begin(), expected.end(), b.begin(), lower);
    return a == b;
}

double clamp01(double value) {
    return std::max(0.0, std::min(1.0, value));
}

std::size_t countSyllableGroups(const std::string& word) {
    std::size_t groups = 0;
    bool previousVowel = false;
    for (unsigned char raw : word) {
        const char c = static_cast<char>(std::tolower(raw));
        const bool vowel = c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u';
        if (vowel && !previousVowel) ++groups;
        previousVowel = vowel;
    }
    if (groups == 0 && !word.empty()) groups = 1;
    if (word.size() > 2 && word.back() == 'e' && groups > 1) --groups;
    return groups;
}

std::string difficultyLabel(double score) {
    if (score < 0.34) return "Easy";
    if (score < 0.67) return "Medium";
    return "Hard";
}
} // namespace

std::string AdvancedQuestionEngine::normalizeToken(const std::string& token) {
    std::string result;
    result.reserve(token.size());
    for (unsigned char raw : token) {
        const char c = static_cast<char>(std::tolower(raw));
        if (std::isalnum(static_cast<unsigned char>(c))) result.push_back(c);
    }
    if (result.size() > 4 && result.compare(result.size() - 3, 3, "ing") == 0) {
        result.resize(result.size() - 3);
    } else if (result.size() > 3 && result.compare(result.size() - 2, 2, "ed") == 0) {
        result.resize(result.size() - 2);
    } else if (result.size() > 3 && result.back() == 's') {
        result.pop_back();
    }
    return result;
}

std::vector<std::string> AdvancedQuestionEngine::tokenize(const std::string& text) {
    std::vector<std::string> tokens;
    std::string current;
    auto flush = [&]() {
        if (current.empty()) return;
        std::string token = normalizeToken(current);
        if (!token.empty() && stopWords().count(token) == 0) tokens.push_back(std::move(token));
        current.clear();
    };

    for (unsigned char raw : text) {
        if (std::isalnum(raw)) current.push_back(static_cast<char>(raw));
        else flush();
    }
    flush();
    return tokens;
}

void AdvancedQuestionEngine::build(const std::vector<Question>& questions) {
    documents_ = questions;
    vectors_.clear();
    invertedIndex_.clear();
    inverseDocumentFrequency_.clear();
    averageLength_ = 0.0;

    std::vector<std::unordered_map<std::string, std::size_t>> termFrequencies;
    termFrequencies.reserve(documents_.size());
    std::unordered_map<std::string, std::size_t> documentFrequency;

    for (std::size_t index = 0; index < documents_.size(); ++index) {
        const auto tokens = tokenize(documents_[index].text);
        std::unordered_map<std::string, std::size_t> frequencies;
        for (const auto& token : tokens) ++frequencies[token];
        for (const auto& entry : frequencies) ++documentFrequency[entry.first];

        DocumentVector vector;
        vector.tokenCount = tokens.size();
        averageLength_ += static_cast<double>(tokens.size());
        termFrequencies.push_back(std::move(frequencies));
        vectors_.push_back(std::move(vector));
    }

    if (!documents_.empty()) averageLength_ /= static_cast<double>(documents_.size());
    const double documentCount = static_cast<double>(documents_.size());

    for (const auto& entry : documentFrequency) {
        const double df = static_cast<double>(entry.second);
        inverseDocumentFrequency_[entry.first] =
            std::log(1.0 + (documentCount - df + 0.5) / (df + 0.5));
    }

    for (std::size_t index = 0; index < termFrequencies.size(); ++index) {
        auto& vector = vectors_[index];
        const double length = static_cast<double>(std::max<std::size_t>(1, vector.tokenCount));
        for (const auto& term : termFrequencies[index]) {
            const double frequency = static_cast<double>(term.second);
            const double idf = inverseDocumentFrequency_[term.first];
            const double denominator = frequency + kBm25K1 *
                (1.0 - kBm25B + kBm25B * length / std::max(1.0, averageLength_));
            const double weight = idf * frequency * (kBm25K1 + 1.0) /
                std::max(kEpsilon, denominator);
            vector.weights[term.first] = weight;
            vector.norm += weight * weight;
            invertedIndex_[term.first].push_back({index, term.second});
        }
        vector.norm = std::sqrt(vector.norm);
    }
}

bool AdvancedQuestionEngine::matches(const PaperMetadata& paper,
                                     const AdvancedSearchOptions& options) const {
    return (options.subject.empty() || containsIgnoreCase(paper.subject, options.subject)) &&
           (options.term.empty() || containsIgnoreCase(paper.term, options.term)) &&
           (options.examYear.empty() || paper.examYear == options.examYear);
}

std::vector<AdvancedSearchResult> AdvancedQuestionEngine::search(
    const std::string& query, const AdvancedSearchOptions& options) const {
    const auto queryTokens = tokenize(query);
    std::unordered_map<std::string, std::size_t> queryFrequency;
    for (const auto& token : queryTokens) ++queryFrequency[token];

    std::vector<AdvancedSearchResult> results;
    if (queryFrequency.empty() || documents_.empty()) return results;

    for (std::size_t index = 0; index < documents_.size(); ++index) {
        if (!matches(documents_[index].paper, options)) continue;
        double score = 0.0;
        std::vector<std::string> matched;
        const double documentLength = static_cast<double>(std::max<std::size_t>(1, vectors_[index].tokenCount));

        for (const auto& term : queryFrequency) {
            const auto postingList = invertedIndex_.find(term.first);
            if (postingList == invertedIndex_.end()) continue;
            auto posting = std::find_if(postingList->second.begin(), postingList->second.end(),
                [index](const Posting& item) { return item.document == index; });
            if (posting == postingList->second.end()) continue;

            const double tf = static_cast<double>(posting->frequency);
            const double idf = inverseDocumentFrequency_.at(term.first);
            const double normLength = documentLength / std::max(1.0, averageLength_);
            const double denominator = tf + kBm25K1 * (1.0 - kBm25B + kBm25B * normLength);
            score += idf * tf * (kBm25K1 + 1.0) / std::max(kEpsilon, denominator);
            matched.push_back(term.first);
        }

        if (!matched.empty()) {
            const double queryCoverage = static_cast<double>(matched.size()) /
                static_cast<double>(queryFrequency.size());
            score *= 0.75 + 0.25 * queryCoverage;
            if (score >= options.minimumScore) {
                results.push_back({index, score, std::move(matched)});
            }
        }
    }

    std::stable_sort(results.begin(), results.end(), [](const auto& left, const auto& right) {
        if (left.score != right.score) return left.score > right.score;
        return left.questionIndex < right.questionIndex;
    });

    const std::size_t begin = std::min(options.offset, results.size());
    const std::size_t end = std::min(results.size(), begin + options.limit);
    return std::vector<AdvancedSearchResult>(results.begin() + begin, results.begin() + end);
}

double AdvancedQuestionEngine::cosine(const DocumentVector& left,
                                      const DocumentVector& right) {
    if (left.norm <= kEpsilon || right.norm <= kEpsilon) return 0.0;
    const DocumentVector* smaller = &left;
    const DocumentVector* larger = &right;
    if (smaller->weights.size() > larger->weights.size()) std::swap(smaller, larger);

    double dot = 0.0;
    for (const auto& term : smaller->weights) {
        const auto found = larger->weights.find(term.first);
        if (found != larger->weights.end()) dot += term.second * found->second;
    }
    return clamp01(dot / (left.norm * right.norm));
}

double AdvancedQuestionEngine::jaccard(const std::vector<std::string>& left,
                                       const std::vector<std::string>& right) {
    std::unordered_set<std::string> a(left.begin(), left.end());
    std::unordered_set<std::string> b(right.begin(), right.end());
    if (a.empty() && b.empty()) return 1.0;
    std::size_t intersection = 0;
    for (const auto& token : a) if (b.count(token)) ++intersection;
    const std::size_t unionSize = a.size() + b.size() - intersection;
    return unionSize == 0 ? 0.0 : static_cast<double>(intersection) /
        static_cast<double>(unionSize);
}

std::vector<SimilarQuestionPair> AdvancedQuestionEngine::findSimilarPairs(
    double minimumScore, std::size_t maximumPairs) const {
    std::vector<SimilarQuestionPair> pairs;
    const double threshold = clamp01(minimumScore);
    for (std::size_t i = 0; i < documents_.size(); ++i) {
        const auto leftTokens = tokenize(documents_[i].text);
        for (std::size_t j = i + 1; j < documents_.size(); ++j) {
            const auto rightTokens = tokenize(documents_[j].text);
            const double cosineScore = cosine(vectors_[i], vectors_[j]);
            const double jaccardScore = jaccard(leftTokens, rightTokens);
            const double combined = 0.8 * cosineScore + 0.2 * jaccardScore;
            if (combined >= threshold) {
                pairs.push_back({i, j, cosineScore, jaccardScore, combined});
            }
        }
    }

    std::stable_sort(pairs.begin(), pairs.end(), [](const auto& left, const auto& right) {
        if (left.combinedScore != right.combinedScore)
            return left.combinedScore > right.combinedScore;
        if (left.firstIndex != right.firstIndex) return left.firstIndex < right.firstIndex;
        return left.secondIndex < right.secondIndex;
    });
    if (pairs.size() > maximumPairs) pairs.resize(maximumPairs);
    return pairs;
}

std::vector<QuestionDifficulty> AdvancedQuestionEngine::estimateDifficulty() const {
    std::vector<QuestionDifficulty> result;
    result.reserve(documents_.size());

    for (std::size_t index = 0; index < documents_.size(); ++index) {
        const auto tokens = tokenize(documents_[index].text);
        if (tokens.empty()) {
            result.push_back({index, 0.0, 0.0, 0.0, "Easy"});
            continue;
        }

        double syllables = 0.0;
        std::size_t longWords = 0;
        std::unordered_set<std::string> unique;
        for (const auto& token : tokens) {
            syllables += static_cast<double>(countSyllableGroups(token));
            if (token.size() >= 9) ++longWords;
            unique.insert(token);
        }

        const double averageSyllables = syllables / static_cast<double>(tokens.size());
        const double longWordRatio = static_cast<double>(longWords) /
            static_cast<double>(tokens.size());
        const double lexical = clamp01((averageSyllables - 1.0) / 2.5 * 0.65 +
                                       longWordRatio * 0.35);
        const double density = clamp01(static_cast<double>(unique.size()) /
            static_cast<double>(tokens.size()));
        const double lengthFactor = clamp01(std::log1p(static_cast<double>(tokens.size())) / 5.0);
        const double concept = clamp01(0.55 * density + 0.45 * lengthFactor);
        const double score = clamp01(0.55 * lexical + 0.45 * concept);

        result.push_back({index, lexical, concept, score, difficultyLabel(score)});
    }
    return result;
}

std::vector<std::string> AdvancedQuestionEngine::explainSearch(
    const AdvancedSearchResult& result) const {
    std::vector<std::string> explanation;
    if (result.questionIndex >= documents_.size()) return explanation;
    explanation.push_back("Matched question: " + documents_[result.questionIndex].number);
    explanation.push_back("Rank score: " + std::to_string(result.score));
    if (!result.matchedTerms.empty()) {
        std::ostringstream terms;
        terms << "Matched terms: ";
        for (std::size_t index = 0; index < result.matchedTerms.size(); ++index) {
            if (index) terms << ", ";
            terms << result.matchedTerms[index];
        }
        explanation.push_back(terms.str());
    }
    explanation.push_back("Ranking uses BM25-style term weighting and query coverage.");
    return explanation;
}

std::size_t AdvancedQuestionEngine::documentCount() const { return documents_.size(); }
std::size_t AdvancedQuestionEngine::vocabularySize() const { return invertedIndex_.size(); }
double AdvancedQuestionEngine::averageDocumentLength() const { return averageLength_; }

} // namespace smartpyq
