#pragma once
#include "Question.h"
#include <string>
#include <vector>
#include <cstddef>

struct FrequencyRecord { std::string text; std::size_t count; };
class SHA256 { public: static std::string hash(const std::string&); };
class TextNormalizer { public: static std::string normalize(const std::string&); };
class QuestionParser { public: std::vector<Question> parse(const std::string&, const PaperMetadata& = {}) const; };
class FrequencyAnalyzer { public: std::vector<FrequencyRecord> analyze(const std::vector<Question>&) const; };
class SimilarityEngine { public: static double jaccard(const std::string&, const std::string&); };
PaperMetadata loadMetadata(const std::string& path);
