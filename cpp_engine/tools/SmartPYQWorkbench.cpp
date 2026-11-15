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

class TrendAnalyzer {
public:
 struct Trend { std::string term; std::map<std::string,std::size_t> counts; std::size_t total=0; };
 static std::vector<Trend> analyze(const std::vector<Question>&q,std::size_t minimum=2){
  std::map<std::string,Trend> trends;
  for(const auto&x:q){std::set<std::string>seen(x.tokens.begin(),x.tokens.end());
   for(const auto&t:seen){auto&v=trends[t];v.term=t;++v.counts[x.paper.year];++v.total;}}
  std::vector<Trend>out;for(auto&x:trends)if(x.second.total>=minimum)out.push_back(std::move(x.second));
  std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.total!=b.total?a.total>b.total:a.term<b.term;});return out;
 }
 static double growth(const Trend&t,const std::string&early,const std::string&late){
  auto a=t.counts.find(early),b=t.counts.find(late);double x=a==t.counts.end()?0:a->second,y=b==t.counts.end()?0:b->second;
  return x==0?(y>0?1.0:0.0):(y-x)/x;
 }
};
class SubjectCoverage {
public:
 struct Coverage { std::string subject; std::size_t papers=0,questions=0,years=0; double averagePerPaper=0; };
 static std::vector<Coverage> summarize(const std::vector<Question>&q){
  struct Acc {std::set<std::string>papers,years;std::size_t questions=0;};
  std::map<std::string,Acc>data;
  for(const auto&x:q){auto&v=data[x.paper.subject];v.papers.insert(x.paper.code);v.years.insert(x.paper.year);++v.questions;}
  std::vector<Coverage>out;for(const auto&x:data){Coverage c;c.subject=x.first;c.papers=x.second.papers.size();c.years=x.second.years.size();c.questions=x.second.questions;c.averagePerPaper=c.papers?double(c.questions)/c.papers:0;out.push_back(c);}
  std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.questions>b.questions;});return out;
 }
};
class PaperComparator {
public:
 struct Difference { std::string paperA,paperB;std::size_t sharedTerms=0,uniqueA=0,uniqueB=0;double overlap=0; };
 static std::vector<Difference> compare(const std::vector<Question>&q){
  std::map<std::string,std::unordered_set<std::string>> vocab;
  for(const auto&x:q)for(const auto&t:x.tokens)vocab[x.paper.code].insert(t);
  std::vector<Difference>out;
  for(auto a=vocab.begin();a!=vocab.end();++a)for(auto b=std::next(a);b!=vocab.end();++b){
   std::size_t shared=0;for(const auto&t:a->second)if(b->second.count(t))++shared;
   std::size_t uni=a->second.size()+b->second.size()-shared;
   Difference d;d.paperA=a->first;d.paperB=b->first;d.sharedTerms=shared;d.uniqueA=a->second.size()-shared;d.uniqueB=b->second.size()-shared;d.overlap=uni?double(shared)/uni:0;out.push_back(d);
  }
  std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.overlap>b.overlap;});return out;
 }
};
class FrequencyReport {
public:
 static std::map<std::string,std::size_t> exactGroups(const std::vector<Question>&q){
  std::map<std::string,std::size_t>groups;for(const auto&x:q)++groups[canonical(x.text)];return groups;
 }
 static double exactRepeatRate(const std::vector<Question>&q){
  if(q.empty())return 0;auto groups=exactGroups(q);std::size_t repeated=0;
  for(const auto&g:groups)if(g.second>1)repeated+=g.second;
  return double(repeated)/q.size();
 }
 static std::size_t uniqueQuestionCount(const std::vector<Question>&q){
  return exactGroups(q).size();
 }
};
class SearchExplanation {
public:
 static std::vector<std::string> explain(const SearchHit&hit,const std::vector<Question>&q){
  std::vector<std::string>out;if(hit.index>=q.size())return out;
  out.push_back("Question "+q[hit.index].number+" from "+q[hit.index].paper.code);
  out.push_back("BM25-style relevance score: "+std::to_string(hit.score));
  std::ostringstream terms;terms<<"Matched query terms: ";
  for(std::size_t i=0;i<hit.terms.size();++i){if(i)terms<<", ";terms<<hit.terms[i];}
  out.push_back(terms.str());out.push_back("Ranking combines inverse document frequency, term frequency, document length, and query coverage.");return out;
 }
};
void printUsage(const char*exe){
 std::cout<<"Smart PYQ Workbench (C++17)\n"
 <<"Usage: "<<exe<<" <questions.tsv> [report.html] [--csv]\n"
 <<"Input columns: paper_code, subject, exam_year, term, question_number, question_text\n"
 <<"Use tabs between columns; escape embedded tabs as \\t.\n";
}
int runWorkbench(const std::string&path,const std::string&report,bool csvMode){
 Corpus corpus;corpus.load(path,csvMode);const auto&q=corpus.questions;
 if(q.empty()){std::cerr<<"No questions were loaded.\n";return 2;}
 Metrics metrics(q);SearchIndex index;index.build(q);
 auto pairs=Similarity::find(q,.70,100);auto difficulty=DifficultyEstimator::estimate(q);
 auto priorities=RepetitionPlanner::rank(q);auto warnings=QualityAudit::inspect(q);
 std::cout<<"Questions: "<<q.size()<<"\nTokens: "<<metrics.tokens()
 <<"\nVocabulary: "<<metrics.vocabulary()<<"\nAverage length: "<<metrics.averageLength()<<"\n";
 std::cout<<"Exact unique questions: "<<FrequencyReport::uniqueQuestionCount(q)
 <<"\nExact repeat rate: "<<FrequencyReport::exactRepeatRate(q)<<"\n";
 std::cout<<"\nSubject distribution:\n";
 for(const auto&x:metrics.bySubject())std::cout<<"  "<<x.first<<": "<<x.second<<"\n";
 std::cout<<"\nYear distribution:\n";
 for(const auto&x:metrics.byYear())std::cout<<"  "<<x.first<<": "<<x.second<<"\n";
 std::cout<<"\nFrequent terms:\n";
 for(const auto&x:metrics.topTerms(12))std::cout<<"  "<<x.first<<": "<<x.second<<"\n";
 std::cout<<"\nHigh-priority questions:\n";
 for(std::size_t i=0;i<std::min<std::size_t>(10,priorities.size());++i){
  const auto&p=priorities[i];const auto&x=q[p.index];
  std::cout<<"  "<<x.paper.code<<"/"<<x.number<<" appearances="<<p.occurrences
   <<" years="<<p.years<<" papers="<<p.papers<<" "<<x.text.substr(0,100)<<"\n";
 }
 std::cout<<"\nSimilar pairs: "<<pairs.size()<<"\n";
 for(std::size_t i=0;i<std::min<std::size_t>(10,pairs.size());++i){
  const auto&p=pairs[i];std::cout<<"  "<<q[p.a].paper.code<<"/"<<q[p.a].number
   <<" <-> "<<q[p.b].paper.code<<"/"<<q[p.b].number<<" score="<<p.score<<"\n";
 }
 std::map<std::string,std::size_t>bands;for(const auto&d:difficulty)++bands[d.band];
 std::cout<<"\nDifficulty distribution:\n";for(const auto&x:bands)std::cout<<"  "<<x.first<<": "<<x.second<<"\n";
 std::cout<<"\nQuality warnings: "<<warnings.size()<<"\n";
 for(std::size_t i=0;i<std::min<std::size_t>(12,warnings.size());++i)std::cout<<"  - "<<warnings[i]<<"\n";
 auto hits=index.search("data structure algorithm");
 std::cout<<"\nExample ranked search:\n";
 for(const auto&hit:hits){const auto&x=q[hit.index];std::cout<<"  ["<<hit.score<<"] "<<x.number<<": "<<x.text.substr(0,100)<<"\n";}
 std::cout<<"\nSuggested related terms:\n";
 for(const auto&t:QueryExpander::suggest(q,"data structure algorithm"))std::cout<<"  "<<t<<"\n";
 auto blueprint=MockExamBuilder::create(q,difficulty,"",10,2026,true);
 std::cout<<"\nSample mock exam: "<<blueprint.indices.size()<<" questions (easy "
 <<blueprint.easy<<", medium "<<blueprint.medium<<", hard "<<blueprint.hard<<")\n";
 std::cout<<"\nSubject coverage:\n";
 for(const auto&x:SubjectCoverage::summarize(q))std::cout<<"  "<<x.subject<<": "<<x.questions
 <<" questions across "<<x.papers<<" papers and "<<x.years<<" years\n";
 auto trends=TrendAnalyzer::analyze(q,2);
 std::cout<<"\nRecurring topic terms: "<<trends.size()<<"\n";
 for(std::size_t i=0;i<std::min<std::size_t>(10,trends.size());++i)
  std::cout<<"  "<<trends[i].term<<": "<<trends[i].total<<" occurrences\n";
 auto comparisons=PaperComparator::compare(q);
 std::cout<<"\nPaper vocabulary comparisons: "<<comparisons.size()<<"\n";
 for(std::size_t i=0;i<std::min<std::size_t>(8,comparisons.size());++i)
  std::cout<<"  "<<comparisons[i].paperA<<" vs "<<comparisons[i].paperB
   <<" overlap="<<comparisons[i].overlap<<"\n";
 if(!report.empty()){ReportWriter::htmlReport(report,q,pairs,difficulty,metrics);std::cout<<"HTML report written: "<<report<<"\n";}
 return 0;
}

/*
 * Additional study-support utilities. These functions are intentionally
 * independent of the command-line entry point so they can be reused when this
 * companion is later split into library modules.
 */
namespace study_support {
struct Flashcard {
 std::string front,back,subject,source;
 std::size_t questionIndex=0;
};
struct StudySession {
 std::string subject,topic;
 std::vector<std::size_t> questionIndices;
 std::size_t estimatedMinutes=0;
 double priority=0;
};
struct CalendarDay {
 std::string date;
 std::vector<StudySession> sessions;
 std::size_t totalMinutes=0;
};
struct LearningObjective {
 std::string topic;
 std::size_t questionCount=0,distinctYears=0;
 double recurrence=0,coverage=0,priority=0;
};
struct RevisionPlan {
 std::vector<CalendarDay> days;
 std::size_t scheduledQuestions=0,unscheduledQuestions=0;
};

static std::string shorten(const std::string&s,std::size_t n){
 if(s.size()<=n)return s;return s.substr(0,n>3?n-3:0)+"...";
}
static std::string makeQuestionPrompt(const smartpyq::Question&q){
 std::ostringstream o;o<<"Explain or solve the following question from "
 <<q.paper.subject<<": "<<q.text;return o.str();
}
static std::string makeAnswerCue(const smartpyq::Question&q){
 auto tokens=smartpyq::tokenize(q.text);std::ostringstream o;
 o<<"Key concepts to revise: ";std::set<std::string>unique(tokens.begin(),tokens.end());
 std::size_t count=0;for(const auto&t:unique){if(count==8)break;if(count++)o<<", ";o<<t;}
 return o.str();
}
class FlashcardBuilder {
public:
 static std::vector<Flashcard> fromQuestions(const std::vector<smartpyq::Question>&q){
  std::vector<Flashcard>cards;cards.reserve(q.size());
  for(std::size_t i=0;i<q.size();++i){
   Flashcard c;c.front=makeQuestionPrompt(q[i]);c.back=makeAnswerCue(q[i]);
   c.subject=q[i].paper.subject;c.source=q[i].paper.code+" / "+q[i].number;c.questionIndex=i;
   cards.push_back(std::move(c));
  }return cards;
 }
 static void exportTsv(const std::string&path,const std::vector<Flashcard>&cards){
  std::ofstream out(path);if(!out)throw std::runtime_error("cannot write flashcards");
  out<<"front\tback\tsubject\tsource\n";
  for(const auto&c:cards)out<<escape(c.front)<<'\t'<<escape(c.back)<<'\t'
   <<escape(c.subject)<<'\t'<<escape(c.source)<<'\n';
 }
private:
 static std::string escape(const std::string&s){
  std::string out;for(char c:s){if(c=='\\')out+="\\\\";else if(c=='\t')out+="\\t";
   else if(c=='\n')out+="\\n";else out+=c;}return out;
 }
};
class ObjectiveMiner {
public:
 static std::vector<LearningObjective> mine(const std::vector<smartpyq::Question>&q){
  struct Aggregate{std::size_t count=0;std::set<std::string>years,papers;};
  std::map<std::string,Aggregate>aggregate;
  for(const auto&question:q){
   std::set<std::string>unique(question.tokens.begin(),question.tokens.end());
   for(const auto&term:unique){auto&a=aggregate[term];++a.count;a.years.insert(question.paper.year);a.papers.insert(question.paper.code);}
  }
  std::vector<LearningObjective>result;
  for(const auto&item:aggregate){
   LearningObjective x;x.topic=item.first;x.questionCount=item.second.count;
   x.distinctYears=item.second.years.size();
   x.recurrence=std::log1p(double(x.questionCount));
   x.coverage=double(x.distinctYears);
   x.priority=.65*x.recurrence+.35*x.coverage;
   result.push_back(x);
  }
  std::sort(result.begin(),result.end(),[](const auto&a,const auto&b){
   return a.priority!=b.priority?a.priority>b.priority:a.topic<b.topic;
  });return result;
 }
};
class RevisionScheduler {
public:
 static RevisionPlan build(const std::vector<smartpyq::Question>&q,
  const std::vector<smartpyq::Difficulty>&difficulty,
  const std::vector<smartpyq::Priority>&priority,
  const std::vector<std::string>&dates,std::size_t minutesPerDay=90){
  RevisionPlan plan;std::vector<std::size_t>order;
  for(const auto&p:priority)if(p.index<q.size())order.push_back(p.index);
  std::set<std::size_t>scheduled;
  std::size_t cursor=0;
  for(const auto&date:dates){
   CalendarDay day;day.date=date;
   while(cursor<order.size()){
    const std::size_t index=order[cursor];
    const std::size_t length=q[index].tokens.size();
    const std::size_t base=std::max<std::size_t>(8,std::min<std::size_t>(35,8+length/4));
    const double difficultyFactor=index<difficulty.size()?1.0+difficulty[index].score:1.0;
    const std::size_t estimate=static_cast<std::size_t>(std::ceil(base*difficultyFactor));
    if(day.totalMinutes+estimate>minutesPerDay&&!day.sessions.empty())break;
    StudySession session;session.subject=q[index].paper.subject;
    session.topic=shorten(q[index].text,70);session.questionIndices.push_back(index);
    session.estimatedMinutes=estimate;
    session.priority=index<priority.size()?priority[index].score:0;
    day.sessions.push_back(std::move(session));day.totalMinutes+=estimate;
    scheduled.insert(index);++cursor;
    if(day.totalMinutes>=minutesPerDay)break;
   }
   plan.days.push_back(std::move(day));
   if(cursor>=order.size())break;
  }
  plan.scheduledQuestions=scheduled.size();plan.unscheduledQuestions=q.size()-scheduled.size();
  return plan;
 }
};
class RevisionPlanExporter {
public:
 static void markdown(const std::string&path,const RevisionPlan&plan){
  std::ofstream out(path);if(!out)throw std::runtime_error("cannot write revision plan");
  out<<"# Smart PYQ Revision Plan\n\n";
  out<<"Scheduled questions: "<<plan.scheduledQuestions
     <<"  |  Unscheduled: "<<plan.unscheduledQuestions<<"\n\n";
  for(const auto&day:plan.days){
   out<<"## "<<day.date<<" — "<<day.totalMinutes<<" minutes\n\n";
   for(const auto&s:day.sessions){
    out<<"- **"<<s.subject<<"** ("<<s.estimatedMinutes<<" min): "
       <<s.topic<<"\n";
   }out<<"\n";
  }
 }
};
class TopicCoverageMatrix {
public:
 static std::map<std::string,std::map<std::string,std::size_t>>
 build(const std::vector<smartpyq::Question>&q){
  std::map<std::string,std::map<std::string,std::size_t>>matrix;
  for(const auto&question:q){
   std::set<std::string>unique(question.tokens.begin(),question.tokens.end());
   for(const auto&term:unique)++matrix[question.paper.subject][term];
  }return matrix;
 }
 static void exportCsv(const std::string&path,
  const std::map<std::string,std::map<std::string,std::size_t>>&matrix){
  std::ofstream out(path);if(!out)throw std::runtime_error("cannot write coverage matrix");
  out<<"subject,topic,question_count\n";
  for(const auto&subject:matrix)for(const auto&topic:subject.second)
   out<<smartpyq::csv(subject.first)<<','<<smartpyq::csv(topic.first)<<','
      <<topic.second<<'\n';
 }
};
class QuestionSampler {
public:
 static std::vector<std::size_t> stratified(const std::vector<smartpyq::Question>&q,
  std::size_t sampleSize,std::uint32_t seed){
  std::map<std::string,std::vector<std::size_t>>groups;
  for(std::size_t i=0;i<q.size();++i)
   groups[q[i].paper.subject+"|"+q[i].paper.year].push_back(i);
  std::uint32_t state=seed?seed:0x85ebca6bu;
  auto random=[&](){state^=state<<13;state^=state>>17;state^=state<<5;return state;};
  std::vector<std::size_t>result;
  bool changed=true;
  while(result.size()<sampleSize&&changed){
   changed=false;
   for(auto&group:groups){
    if(group.second.empty()||result.size()>=sampleSize)continue;
    std::size_t pick=random()%group.second.size();
    result.push_back(group.second[pick]);
    group.second.erase(group.second.begin()+static_cast<std::ptrdiff_t>(pick));
    changed=true;
   }
  }return result;
 }
};
class StudyStatistics {
public:
 struct Summary {std::size_t days=0,sessions=0,minutes=0,questions=0;double averageMinutes=0;};
 static Summary summarize(const RevisionPlan&plan){
  Summary s;s.days=plan.days.size();s.questions=plan.scheduledQuestions;
  for(const auto&day:plan.days){s.sessions+=day.sessions.size();s.minutes+=day.totalMinutes;}
  s.averageMinutes=s.days?double(s.minutes)/s.days:0;return s;
 }
};
} // namespace study_support

} // namespace smartpyq

int main(int argc,char**argv){
 if(argc<2||std::string(argv[1])=="--help"){smartpyq::printUsage(argv[0]);return argc<2?1:0;}
 try{
  std::string path=argv[1],report;bool csvMode=false;
  for(int i=2;i<argc;++i){std::string arg=argv[i];if(arg=="--csv")csvMode=true;else report=arg;}
  return smartpyq::runWorkbench(path,report,csvMode);
 }catch(const std::exception&e){std::cerr<<"Error: "<<e.what()<<"\n";return 2;}
}
