#pragma once
#include "Question.h"
#include <string>
#include <vector>
struct RepositoryResult { bool success=false; std::size_t affected=0; std::string message; };
class QuestionRepository {
public:
 RepositoryResult load(const std::string& path);
 RepositoryResult save(const std::string& path) const;
 RepositoryResult insert(Question question);
 RepositoryResult insertMany(const std::vector<Question>& questions);
 RepositoryResult eraseByFingerprint(const std::string& fingerprint);
 RepositoryResult eraseByPaperCode(const std::string& paperCode);
 const Question* findByFingerprint(const std::string& fingerprint) const;
 std::vector<Question> findByPaperCode(const std::string& paperCode) const;
 std::vector<Question> findBySubject(const std::string& subject) const;
 const std::vector<Question>& all() const;
 std::size_t size() const;
 void clear();
private:
 std::vector<Question> questions_;
 static std::string encode(const std::string&);
 static bool decode(const std::string&,std::string&);
 static std::string fingerprintFor(const Question&);
};