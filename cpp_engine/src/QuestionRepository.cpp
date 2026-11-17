#include "QuestionRepository.h"
#include "Engine.h"
#include <algorithm>
#include <cctype>
#include <cstdio>
#include <fstream>
#include <unordered_set>
namespace {
const char* MAGIC="SMARTPYQ_REPOSITORY_V1";
std::string lower(std::string s){for(char& c:s)c=static_cast<char>(std::tolower(static_cast<unsigned char>(c)));return s;}
std::vector<std::string> fields(const std::string& s){
 std::vector<std::string> out;std::size_t p=0;
 for(std::size_t i=0;i<=s.size();++i)if(i==s.size()||s[i]=='\t'){out.push_back(s.substr(p,i-p));p=i+1;}
 return out;
}
}
std::string QuestionRepository::encode(const std::string& s){
 std::string o;for(char c:s)switch(c){case '\\':o+="\\\\";break;case '\t':o+="\\t";break;case '\n':o+="\\n";break;case '\r':o+="\\r";break;default:o+=c;}return o;
}
bool QuestionRepository::decode(const std::string& s,std::string& o){
 o.clear();for(std::size_t i=0;i<s.size();++i){if(s[i]!='\\'){o+=s[i];continue;}if(++i==s.size())return false;
 switch(s[i]){case '\\':o+='\\';break;case 't':o+='\t';break;case 'n':o+='\n';break;case 'r':o+='\r';break;default:return false;}}return true;
}
std::string QuestionRepository::fingerprintFor(const Question& q){
 if(!q.fingerprint.empty())return q.fingerprint;
 return SHA256::hash(q.normalized.empty()?TextNormalizer::normalize(q.text):q.normalized);
}
RepositoryResult QuestionRepository::load(const std::string& path){
 std::ifstream in(path,std::ios::binary);if(!in)return {false,0,"Cannot open repository: "+path};
 std::string line;if(!std::getline(in,line)||line!=MAGIC)return {false,0,"Unsupported repository format"};
 std::vector<Question> staged;std::size_t n=1;
 while(std::getline(in,line)){++n;if(line.empty())continue;auto f=fields(line);
 if(f.size()!=10)return {false,0,"Malformed record at line "+std::to_string(n)};
 std::vector<std::string> d(10);for(std::size_t i=0;i<10;++i)if(!decode(f[i],d[i]))return {false,0,"Invalid escape at line "+std::to_string(n)};
 Question q;q.number=d[0];q.text=d[1];q.normalized=d[2];q.fingerprint=d[3];
 q.paper.course=d[4];q.paper.academicYear=d[5];q.paper.examYear=d[6];q.paper.subject=d[7];q.paper.term=d[8];q.paper.paperCode=d[9];
 staged.push_back(std::move(q));}
 questions_.swap(staged);return {true,questions_.size(),"Repository loaded"};
}
RepositoryResult QuestionRepository::save(const std::string& path)const{
 const std::string temp=path+".tmp";std::ofstream out(temp,std::ios::binary|std::ios::trunc);
 if(!out)return {false,0,"Cannot create repository file"};
 out<<MAGIC<<'\n';for(const auto& q:questions_){
 std::vector<std::string> f={q.number,q.text,q.normalized,fingerprintFor(q),q.paper.course,q.paper.academicYear,q.paper.examYear,q.paper.subject,q.paper.term,q.paper.paperCode};
 for(std::size_t i=0;i<f.size();++i){if(i)out<<'\t';out<<encode(f[i]);}out<<'\n';}
 out.flush();if(!out)return {false,0,"Repository write failed"};out.close();
 std::remove(path.c_str());if(std::rename(temp.c_str(),path.c_str())!=0)return {false,0,"Could not finalize repository file"};
 return {true,questions_.size(),"Repository saved"};
}
RepositoryResult QuestionRepository::insert(Question q){
 if(q.text.empty())return {false,0,"Question text is empty"};q.fingerprint=fingerprintFor(q);
 if(findByFingerprint(q.fingerprint))return {false,0,"Duplicate question"};
 if(q.normalized.empty())q.normalized=TextNormalizer::normalize(q.text);questions_.push_back(std::move(q));return {true,1,"Inserted"};
}
RepositoryResult QuestionRepository::insertMany(const std::vector<Question>& batch){
 std::unordered_set<std::string> seen;for(const auto& q:questions_)seen.insert(fingerprintFor(q));
 std::size_t added=0;for(auto q:batch){if(q.text.empty())continue;q.fingerprint=fingerprintFor(q);
 if(!seen.insert(q.fingerprint).second)continue;if(q.normalized.empty())q.normalized=TextNormalizer::normalize(q.text);
 questions_.push_back(std::move(q));++added;}return {true,added,"Unique questions imported"};
}
RepositoryResult QuestionRepository::eraseByFingerprint(const std::string& key){
 auto old=questions_.size();questions_.erase(std::remove_if(questions_.begin(),questions_.end(),[&](const Question&q){return fingerprintFor(q)==key;}),questions_.end());
 auto n=old-questions_.size();return {n!=0,n,n?"Removed":"No match"};
}
RepositoryResult QuestionRepository::eraseByPaperCode(const std::string& code){
 auto old=questions_.size();questions_.erase(std::remove_if(questions_.begin(),questions_.end(),[&](const Question&q){return q.paper.paperCode==code;}),questions_.end());
 auto n=old-questions_.size();return {n!=0,n,n?"Paper removed":"No matching paper"};
}
const Question* QuestionRepository::findByFingerprint(const std::string& key)const{
 for(const auto& q:questions_)if(fingerprintFor(q)==key)return &q;return nullptr;
}
std::vector<Question> QuestionRepository::findByPaperCode(const std::string& code)const{
 std::vector<Question> r;for(const auto&q:questions_)if(q.paper.paperCode==code)r.push_back(q);return r;
}
std::vector<Question> QuestionRepository::findBySubject(const std::string& subject)const{
 std::vector<Question> r;const auto key=lower(subject);for(const auto&q:questions_)if(lower(q.paper.subject)==key)r.push_back(q);return r;
}
const std::vector<Question>& QuestionRepository::all()const{return questions_;}
std::size_t QuestionRepository::size()const{return questions_.size();}
void QuestionRepository::clear(){questions_.clear();}
