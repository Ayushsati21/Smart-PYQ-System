/*
 * Smart PYQ Workbench — standalone C++17 corpus analysis utility.
 * Input TSV: paper_code<TAB>subject<TAB>year<TAB>term<TAB>number<TAB>question_text
 * Build: g++ -std=c++17 -O2 SmartPYQWorkbench.cpp -o smart-pyq-workbench
 * This offline utility does not touch the live Flask/OCR/database/frontend stack.
 */
#include <algorithm>
#include <array>
#include <cmath>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace smartpyq {
constexpr double EPS=1e-12, K1=1.45, B=0.72;
struct Paper { std::string code,subject,year,term; };
struct Question {
 Paper paper; std::string number,text; std::size_t line=0;
 std::vector<std::string> tokens;
 std::unordered_map<std::string,std::size_t> tf;
};
struct SearchOptions {
 std::string subject,year,term; std::size_t offset=0,limit=20; double minScore=0;
};
struct SearchHit { std::size_t index=0; double score=0; std::vector<std::string> terms; };
struct SimilarPair { std::size_t a=0,b=0; double cosine=0,jaccard=0,edit=0,score=0; };
struct Difficulty {
 std::size_t index=0; double vocabulary=0,length=0,reasoning=0,formula=0,score=0;
 std::string band; std::vector<std::string> signals;
};
struct Priority { std::size_t index=0,occurrences=0,years=0,papers=0; double score=0; };
struct MockPaper { std::vector<std::size_t> indices; std::size_t easy=0,medium=0,hard=0; };

std::string lower(std::string s) {
 std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return char(std::tolower(c));}); return s;
}
std::string trim(const std::string& s) {
 std::size_t a=0,b=s.size(); while(a<b&&std::isspace((unsigned char)s[a]))++a;
 while(b>a&&std::isspace((unsigned char)s[b-1]))--b; return s.substr(a,b-a);
}
double clamp(double x){return std::max(0.0,std::min(1.0,x));}
double divide(double a,double b){return std::abs(b)<EPS?0.0:a/b;}
std::string html(const std::string& s) {
 std::string o; for(char c:s){switch(c){case '&':o+="&amp;";break;case '<':o+="&lt;";break;
 case '>':o+="&gt;";break;case '"':o+="&quot;";break;case '\'':o+="&#39;";break;default:o+=c;}} return o;
}
std::string csv(const std::string& s) {
 if(s.find_first_of(",\"\r\n")==std::string::npos)return s;
 std::string o="\"";for(char c:s){if(c=='\"')o+="\"\"";else o+=c;}return o+"\"";
}
std::vector<std::string> splitTsv(const std::string& s) {
 std::vector<std::string> out;std::string f;bool esc=false;
 for(char c:s){if(esc){if(c=='t')f+='\t';else if(c=='n')f+='\n';else if(c=='r')f+='\r';else f+=c;esc=false;}
 else if(c=='\\')esc=true;else if(c=='\t'){out.push_back(f);f.clear();}else f+=c;}
 if(esc)f+='\\';out.push_back(f);return out;
}
std::vector<std::string> splitCsv(const std::string& s) {
 std::vector<std::string> out;std::string f;bool quoted=false;
 for(std::size_t i=0;i<s.size();++i){char c=s[i];if(c=='\"'){
 if(quoted&&i+1<s.size()&&s[i+1]=='\"'){f+='\"';++i;}else quoted=!quoted;
 }else if(c==','&&!quoted){out.push_back(f);f.clear();}else f+=c;}
 if(quoted)throw std::runtime_error("unclosed CSV quote");out.push_back(f);return out;
}
const std::unordered_set<std::string>& stops(){
 static const std::unordered_set<std::string> w={
 "a","an","and","are","as","at","be","been","before","being","by","can","could",
 "did","do","does","for","from","had","has","have","he","her","here","him","his",
 "how","i","if","in","into","is","it","its","me","more","most","my","no","not",
 "of","on","or","our","out","over","she","should","so","some","such","than","that",
 "the","their","them","then","there","these","they","this","those","to","too","under",
 "up","was","we","were","what","when","where","which","who","why","will","with","you",
 "your","define","describe","explain","discuss","state","write","give","list","using",
 "used","use","show","illustrate","following"};
 return w;
}
std::string stem(std::string s) {
 std::string o;for(unsigned char c:s)if(std::isalnum(c))o+=char(std::tolower(c));
 if(o.size()>6&&o.substr(o.size()-3)=="ing")o.resize(o.size()-3);
 else if(o.size()>5&&o.substr(o.size()-2)=="ed")o.resize(o.size()-2);
 else if(o.size()>4&&o.substr(o.size()-3)=="ies")o.replace(o.size()-3,3,"y");
 else if(o.size()>4&&o.substr(o.size()-2)=="es")o.resize(o.size()-2);
 else if(o.size()>3&&o.back()=='s')o.pop_back();return o;
}
std::vector<std::string> tokenize(const std::string& s,bool removeStops=true) {
 std::vector<std::string> out;std::string w;
 auto flush=[&](){if(w.empty())return;auto t=stem(w);if(!t.empty()&&(!removeStops||!stops().count(t)))out.push_back(t);w.clear();};
 for(unsigned char c:s){if(std::isalnum(c))w+=char(c);else flush();}flush();return out;
}
std::string canonical(const std::string& s) {
 auto t=tokenize(s);std::sort(t.begin(),t.end());t.erase(std::unique(t.begin(),t.end()),t.end());
 std::ostringstream o;for(const auto& x:t)o<<x<<' ';return o.str();
}
class Corpus {
public:
 void load(const std::string& path,bool csvMode=false){
  std::ifstream in(path);if(!in)throw std::runtime_error("cannot open "+path);
  questions.clear();std::string line;std::size_t n=0;
  while(std::getline(in,line)){++n;if(trim(line).empty()||line[0]=='#')continue;
   auto f=csvMode?splitCsv(line):splitTsv(line);if(f.size()<6)throw std::runtime_error("expected 6 columns at line "+std::to_string(n));
   Question q;q.paper={trim(f[0]),trim(f[1]),trim(f[2]),trim(f[3])};q.number=trim(f[4]);q.text=trim(f[5]);q.line=n;
   if(q.text.empty())continue;q.tokens=tokenize(q.text);for(const auto& t:q.tokens)++q.tf[t];questions.push_back(std::move(q));
  }
 }
 std::vector<Question> questions;
};
class Metrics {
 const std::vector<Question>& q_;
public:
 explicit Metrics(const std::vector<Question>& q):q_(q){}
 std::size_t tokens()const{std::size_t n=0;for(const auto& x:q_)n+=x.tokens.size();return n;}
 std::size_t vocabulary()const{std::unordered_set<std::string>s;for(const auto&x:q_)s.insert(x.tokens.begin(),x.tokens.end());return s.size();}
 double averageLength()const{return q_.empty()?0.0:double(tokens())/q_.size();}
 std::map<std::string,std::size_t> bySubject()const{std::map<std::string,std::size_t>m;for(const auto&x:q_)++m[x.paper.subject];return m;}
 std::map<std::string,std::size_t> byYear()const{std::map<std::string,std::size_t>m;for(const auto&x:q_)++m[x.paper.year];return m;}
 std::vector<std::pair<std::string,std::size_t>> topTerms(std::size_t limit)const{
  std::unordered_map<std::string,std::size_t>m;for(const auto&x:q_)for(const auto&t:x.tokens)++m[t];
  std::vector<std::pair<std::string,std::size_t>>v(m.begin(),m.end());
  std::sort(v.begin(),v.end(),[](const auto&a,const auto&b){return a.second!=b.second?a.second>b.second:a.first<b.first;});
  if(v.size()>limit)v.resize(limit);return v;
 }
};
class SearchIndex {
 struct Posting{std::size_t doc,frequency;};
 const std::vector<Question>* q_=nullptr;
 std::unordered_map<std::string,std::vector<Posting>> postings_;
 std::unordered_map<std::string,double> idf_;
 std::vector<std::size_t> lengths_;double avg_=0;
public:
 void build(const std::vector<Question>& q){
  q_=&q;postings_.clear();idf_.clear();lengths_.clear();avg_=0;
  std::unordered_map<std::string,std::size_t> df;
  for(std::size_t i=0;i<q.size();++i){lengths_.push_back(q[i].tokens.size());avg_+=lengths_.back();
   for(const auto& t:q[i].tf){postings_[t.first].push_back({i,t.second});++df[t.first];}}
  if(!q.empty())avg_/=q.size();double n=double(q.size());
  for(const auto&x:df){double d=double(x.second);idf_[x.first]=std::log(1+(n-d+0.5)/(d+0.5));}
 }
 std::vector<SearchHit> search(const std::string& query,const SearchOptions&o={})const{
  if(!q_)return{};std::unordered_map<std::string,std::size_t> terms;
  for(const auto&t:tokenize(query))++terms[t];if(terms.empty())return{};
  std::vector<SearchHit> hits;
  for(std::size_t i=0;i<q_->size();++i){const auto&x=(*q_)[i];
   if(!o.subject.empty()&&lower(x.paper.subject)!=lower(o.subject))continue;
   if(!o.year.empty()&&x.paper.year!=o.year)continue;
   if(!o.term.empty()&&lower(x.paper.term)!=lower(o.term))continue;
   double score=0;std::vector<std::string> matched;
   for(const auto&t:terms){auto f=x.tf.find(t.first);if(f==x.tf.end())continue;
    double tf=double(f->second),dl=double(std::max<std::size_t>(1,lengths_[i]));
    double norm=dl/std::max(1.0,avg_),den=tf+K1*(1-B+B*norm);
    score+=idf_.at(t.first)*tf*(K1+1)/std::max(EPS,den);matched.push_back(t.first);}
   if(matched.empty())continue;score*=0.8+0.2*matched.size()/double(terms.size());
   if(score>=o.minScore)hits.push_back({i,score,std::move(matched)});
  }
  std::stable_sort(hits.begin(),hits.end(),[](const auto&a,const auto&b){return a.score!=b.score?a.score>b.score:a.index<b.index;});
  auto first=std::min(o.offset,hits.size()),last=std::min(hits.size(),first+o.limit);
  return{hits.begin()+std::ptrdiff_t(first),hits.begin()+std::ptrdiff_t(last)};
 }
};
class Similarity {
public:
 static double cosine(const Question&a,const Question&b){
  double dot=0,aa=0,bb=0;for(const auto&x:a.tf){double v=x.second;aa+=v*v;auto i=b.tf.find(x.first);if(i!=b.tf.end())dot+=v*i->second;}
  for(const auto&x:b.tf){double v=x.second;bb+=v*v;}return clamp(divide(dot,std::sqrt(aa*bb)));
 }
 static double jaccard(const Question&a,const Question&b){
  std::size_t common=0;for(const auto&x:a.tf)if(b.tf.count(x.first))++common;
  auto total=a.tf.size()+b.tf.size()-common;return total?double(common)/total:0;
 }
 static std::size_t editDistance(const std::string&a,const std::string&b){
  if(a.size()>b.size()+512||b.size()>a.size()+512)return std::max(a.size(),b.size());
  std::vector<std::size_t>p(b.size()+1),c(b.size()+1);std::iota(p.begin(),p.end(),0);
  for(std::size_t i=1;i<=a.size();++i){c[0]=i;for(std::size_t j=1;j<=b.size();++j){
   auto cost=a[i-1]==b[j-1]?0u:1u;c[j]=std::min({c[j-1]+1,p[j]+1,p[j-1]+cost});}p.swap(c);}return p.back();
 }
 static double editSimilarity(const std::string&a,const std::string&b){
  auto n=std::max(a.size(),b.size());return n?1.0-double(editDistance(lower(a),lower(b)))/n:1.0;
 }
 static std::vector<SimilarPair> find(const std::vector<Question>&q,double threshold=.68,std::size_t limit=500){
  std::vector<SimilarPair> out;for(std::size_t i=0;i<q.size();++i)for(std::size_t j=i+1;j<q.size();++j){
   double c=cosine(q[i],q[j]),d=jaccard(q[i],q[j]),e=editSimilarity(q[i].text,q[j].text),s=.65*c+.25*d+.10*e;
   if(s>=threshold)out.push_back({i,j,c,d,e,s});}
  std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.score!=b.score?a.score>b.score:std::tie(a.a,a.b)<std::tie(b.a,b.b);});
  if(out.size()>limit)out.resize(limit);return out;
 }
};

class DifficultyEstimator {
 static std::size_t syllables(const std::string&w){
  std::size_t n=0;bool previous=false;
  for(unsigned char raw:w){char c=char(std::tolower(raw));bool vowel=c=='a'||c=='e'||c=='i'||c=='o'||c=='u';if(vowel&&!previous)++n;previous=vowel;}
  if(!n&&!w.empty())n=1;if(w.size()>3&&w.back()=='e'&&n>1)--n;return n;
 }
public:
 static std::vector<Difficulty> estimate(const std::vector<Question>&q){
  std::vector<Difficulty> out;const std::array<std::string,20> cues={
   "derive","prove","calculate","compute","algorithm","complexity","recurrence",
   "integral","differentiate","matrix","equation","theorem","optimize","evaluate",
   "justify","compare","design","analyze","implement","demonstrate"};
  for(std::size_t i=0;i<q.size();++i){Difficulty d;d.index=i;const auto&x=q[i];
   if(x.tokens.empty()){d.band="Unknown";out.push_back(d);continue;}
   std::size_t longWords=0,totalSyllables=0;
   for(const auto&t:x.tokens){if(t.size()>=9)++longWords;totalSyllables+=syllables(t);}
   d.vocabulary=clamp((double(totalSyllables)/x.tokens.size()-1.0)/2.8);
   d.length=clamp(std::log1p(double(x.tokens.size()))/5.0);
   d.reasoning=clamp(.65*d.vocabulary+.35*double(longWords)/x.tokens.size());
   auto text=lower(x.text);
   for(const auto&cue:cues)if(text.find(cue)!=std::string::npos)d.signals.push_back(cue);
   std::size_t operators=0;for(char c:x.text)if(c=='='||c=='+'||c=='/'||c=='^'||c=='*')++operators;
   d.formula=clamp(.10*d.signals.size()+.025*operators);
   d.score=clamp(.30*d.vocabulary+.25*d.length+.25*d.reasoning+.20*d.formula);
   d.band=d.score<.34?"Easy":d.score<.67?"Medium":"Hard";out.push_back(std::move(d));
  }return out;
 }
};
class RepetitionPlanner {
public:
 static std::vector<Priority> rank(const std::vector<Question>&q){
  std::unordered_map<std::string,std::vector<std::size_t>>groups;
  for(std::size_t i=0;i<q.size();++i)groups[canonical(q[i].text)].push_back(i);
  std::vector<Priority> out;
  for(std::size_t i=0;i<q.size();++i){const auto&members=groups[canonical(q[i].text)];std::set<std::string>years,papers;
   for(auto j:members){years.insert(q[j].paper.year);papers.insert(q[j].paper.code);}
   double score=.55*std::log1p(double(members.size()))+.30*years.size()+.15*papers.size();
   out.push_back({i,members.size(),years.size(),papers.size(),score});}
  std::stable_sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.score!=b.score?a.score>b.score:a.index<b.index;});return out;
 }
};
class MockExamBuilder {
public:
 static MockPaper create(const std::vector<Question>&q,const std::vector<Difficulty>&d,
                         const std::string&subject,std::size_t count,std::uint32_t seed,bool balanced=true){
  MockPaper result;std::vector<std::size_t>candidates;
  for(std::size_t i=0;i<q.size();++i)if(subject.empty()||lower(q[i].paper.subject)==lower(subject))candidates.push_back(i);
  std::uint32_t state=seed?seed:0x9e3779b9u;
  auto random=[&](){state^=state<<13;state^=state>>17;state^=state<<5;return state;};
  for(std::size_t i=candidates.size();i>1;--i)std::swap(candidates[i-1],candidates[random()%i]);
  if(!balanced){for(auto i:candidates){if(result.indices.size()>=count)break;result.indices.push_back(i);}}
  else{
   std::array<std::pair<std::string,std::size_t>,3>targets={{{"Easy",count/3},{"Medium",count-count/3-count/3},{"Hard",count/3}}};
   for(const auto&t:targets){std::size_t added=0;for(auto i:candidates){if(added>=t.second)break;
    if(std::find(result.indices.begin(),result.indices.end(),i)!=result.indices.end())continue;
    if(d[i].band==t.first){result.indices.push_back(i);++added;}}}
   for(auto i:candidates){if(result.indices.size()>=count)break;if(std::find(result.indices.begin(),result.indices.end(),i)==result.indices.end())result.indices.push_back(i);}
  }
  if(result.indices.size()>count)result.indices.resize(count);
  for(auto i:result.indices){if(d[i].band=="Easy")++result.easy;else if(d[i].band=="Medium")++result.medium;else if(d[i].band=="Hard")++result.hard;}
  return result;
 }
};
class DuplicateClusterer {
public:
 static std::vector<std::vector<std::size_t>> cluster(const std::vector<Question>&q,double threshold=.72){
  std::vector<std::size_t>parent(q.size());std::iota(parent.begin(),parent.end(),0);
  auto root=[&](std::size_t x){while(parent[x]!=x){parent[x]=parent[parent[x]];x=parent[x];}return x;};
  for(std::size_t i=0;i<q.size();++i)for(std::size_t j=i+1;j<q.size();++j)
   if(Similarity::cosine(q[i],q[j])>=threshold){auto a=root(i),b=root(j);if(a!=b)parent[b]=a;}
  std::map<std::size_t,std::vector<std::size_t>>groups;
  for(std::size_t i=0;i<q.size();++i)groups[root(i)].push_back(i);
  std::vector<std::vector<std::size_t>>out;for(auto&g:groups)if(g.second.size()>1)out.push_back(std::move(g.second));
  std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.size()!=b.size()?a.size()>b.size():a.front()<b.front();});return out;
 }
};
class QualityAudit {
public:
 static std::vector<std::string> inspect(const std::vector<Question>&q){
  std::vector<std::string>out;std::unordered_map<std::string,std::size_t>keys;
  for(std::size_t i=0;i<q.size();++i){const auto&x=q[i];auto add=[&](const std::string&s){out.push_back("Record "+std::to_string(i+1)+": "+s);};
   if(x.paper.code.empty())add("missing paper code");if(x.paper.subject.empty())add("missing subject");
   if(x.paper.year.empty())add("missing exam year");if(x.number.empty())add("missing question number");
   if(x.text.size()<8)add("very short question text");if(x.tokens.empty())add("no searchable tokens");
   if(++keys[x.paper.code+"|"+x.number]>1)add("duplicate paper/question-number key");
   if(x.text.find("�")!=std::string::npos)add("replacement character; inspect encoding");
  }return out;
 }
};
class QueryExpander {
public:
 static std::vector<std::string> suggest(const std::vector<Question>&q,const std::string&query,std::size_t limit=10){
  auto terms=tokenize(query);std::unordered_set<std::string>known(terms.begin(),terms.end());
  std::unordered_map<std::string,std::size_t>co;
  for(const auto&x:q){bool related=false;for(const auto&t:x.tokens)if(known.count(t)){related=true;break;}
   if(related)for(const auto&t:x.tokens)if(!known.count(t))++co[t];}
  std::vector<std::pair<std::string,std::size_t>>ranked(co.begin(),co.end());
  std::sort(ranked.begin(),ranked.end(),[](const auto&a,const auto&b){return a.second!=b.second?a.second>b.second:a.first<b.first;});
  std::vector<std::string>out;for(const auto&x:ranked){if(out.size()>=limit)break;out.push_back(x.first);}return out;
 }
};
class ReportWriter {
public:
 static void htmlReport(const std::string&path,const std::vector<Question>&q,
  const std::vector<SimilarPair>&pairs,const std::vector<Difficulty>&difficulty,const Metrics&m){
  std::ofstream out(path);if(!out)throw std::runtime_error("cannot write HTML report");
  out<<"<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Smart PYQ Report</title><style>";
  out<<"body{font:15px/1.55 system-ui,sans-serif;margin:32px;color:#20242a}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #d8dde5;padding:8px;text-align:left;vertical-align:top}th{background:#f2f5f8}.muted{color:#667085}</style></head><body>";
  out<<"<h1>Smart PYQ Workbench</h1><p class=\"muted\">Offline corpus report</p><h2>Corpus</h2><ul><li>Questions: "<<q.size()<<"</li><li>Tokens: "<<m.tokens()<<"</li><li>Vocabulary: "<<m.vocabulary()<<"</li><li>Average length: "<<m.averageLength()<<"</li></ul>";
  out<<"<h2>Subject distribution</h2><table><tr><th>Subject</th><th>Count</th></tr>";
  for(const auto&x:m.bySubject())out<<"<tr><td>"<<html(x.first)<<"</td><td>"<<x.second<<"</td></tr>";out<<"</table>";
  out<<"<h2>Difficulty estimates</h2><p class=\"muted\">Heuristic indicators, not validated grades.</p><table><tr><th>Paper</th><th>Number</th><th>Score</th><th>Band</th></tr>";
  for(const auto&d:difficulty)if(d.index<q.size())out<<"<tr><td>"<<html(q[d.index].paper.code)<<"</td><td>"<<html(q[d.index].number)<<"</td><td>"<<d.score<<"</td><td>"<<d.band<<"</td></tr>";
  out<<"</table><h2>Similar question candidates</h2><p class=\"muted\">Review these candidates manually.</p><table><tr><th>Question A</th><th>Question B</th><th>Score</th></tr>";
  for(const auto&p:pairs)if(p.a<q.size()&&p.b<q.size())out<<"<tr><td>"<<html(q[p.a].text)<<"</td><td>"<<html(q[p.b].text)<<"</td><td>"<<p.score<<"</td></tr>";
  out<<"</table></body></html>";
 }
 static void questionsCsv(const std::string&path,const std::vector<Question>&q){
  std::ofstream out(path);if(!out)throw std::runtime_error("cannot write CSV");
  out<<"paper_code,subject,year,term,number,text\n";
  for(const auto&x:q)out<<csv(x.paper.code)<<','<<csv(x.paper.subject)<<','<<csv(x.paper.year)<<','<<csv(x.paper.term)<<','<<csv(x.number)<<','<<csv(x.text)<<'\n';
 }
 static void pairsCsv(const std::string&path,const std::vector<Question>&q,const std::vector<SimilarPair>&pairs){
  std::ofstream out(path);if(!out)throw std::runtime_error("cannot write similarity CSV");
  out<<"paper_a,number_a,paper_b,number_b,cosine,jaccard,edit,combined\n";
  for(const auto&p:pairs)if(p.a<q.size()&&p.b<q.size())out<<csv(q[p.a].paper.code)<<','<<csv(q[p.a].number)<<','<<csv(q[p.b].paper.code)<<','<<csv(q[p.b].number)<<','<<p.cosine<<','<<p.jaccard<<','<<p.edit<<','<<p.score<<'\n';
 }
};
