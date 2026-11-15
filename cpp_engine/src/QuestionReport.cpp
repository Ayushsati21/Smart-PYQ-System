#include "QuestionReport.h"
#include <fstream>
#include <map>
#include <set>
namespace {
std::string esc(const std::string&s){std::string o;for(char c:s)switch(c){case '&':o+="&amp;";break;case '<':o+="&lt;";break;case '>':o+="&gt;";break;case '"':o+="&quot;";break;case '\'':o+="&#39;";break;default:o+=c;}return o;}
bool open(const std::string&p,std::ofstream&o,std::string*e){o.open(p,std::ios::binary|std::ios::trunc);if(o)return true;if(e)*e="Cannot write report: "+p;return false;}
}
std::string QuestionReport::paperLabel(const PaperMetadata&m){
 if(!m.paperCode.empty())return m.paperCode;if(!m.subject.empty()&&!m.examYear.empty())return m.subject+" - "+m.examYear;
 return m.subject.empty()?"Unlabelled paper":m.subject;
}
bool QuestionReport::writeStudyPlan(const std::string&path,const StudyPlan&plan,std::string*error){
 std::ofstream o;if(!open(path,o,error))return false;
 o<<"<!doctype html><html><head><meta charset=\"utf-8\"><title>Smart PYQ Study Plan</title>"
  <<"<style>body{font:16px/1.5 system-ui;max-width:950px;margin:36px auto;padding:0 20px;color:#20242b}"
  <<".item{border:1px solid #ddd;border-radius:10px;padding:16px;margin:12px 0}.meta{color:#657080}</style></head><body>"
  <<"<h1>Priority Study Plan</h1><p>Based on "<<plan.sourceQuestions<<" extracted questions and "
  <<plan.uniqueTopics<<" unique topics.</p>";
 for(std::size_t i=0;i<plan.priorities.size();++i){const auto&p=plan.priorities[i];
 o<<"<article class=\"item\"><strong>#"<<i+1<<" · Score "<<p.priorityScore<<"</strong><h2>"<<esc(p.questionText)
  <<"</h2><div class=\"meta\">"<<esc(p.subject)<<" · "<<esc(p.questionNumber)<<" · "<<esc(StudyPlanner::explain(p))<<"</div></article>";}
 o<<"</body></html>";if(!o&&error)*error="Study plan write failed";return static_cast<bool>(o);
}
bool QuestionReport::writePaperSummary(const std::string&path,const std::vector<Question>&qs,std::string*error){
 std::ofstream o;if(!open(path,o,error))return false;
 struct Row{std::size_t count=0;std::set<std::string>years;};std::map<std::string,Row>papers;
 std::map<std::string,std::size_t>subjects,years;
 for(const auto&q:qs){auto label=paperLabel(q.paper);++papers[label].count;
 if(!q.paper.examYear.empty()){papers[label].years.insert(q.paper.examYear);++years[q.paper.examYear];}
 if(!q.paper.subject.empty())++subjects[q.paper.subject];}
 o<<"<!doctype html><html><head><meta charset=\"utf-8\"><title>PYQ Summary</title>"
  <<"<style>body{font:15px system-ui;max-width:950px;margin:36px auto;padding:0 20px}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}</style></head><body>"
  <<"<h1>Question Paper Summary</h1><p>Total questions: "<<qs.size()<<"</p><h2>Papers</h2><table><tr><th>Paper</th><th>Questions</th><th>Years</th></tr>";
 for(const auto&x:papers){o<<"<tr><td>"<<esc(x.first)<<"</td><td>"<<x.second.count<<"</td><td>";bool first=true;
 for(const auto&y:x.second.years){if(!first)o<<", ";o<<esc(y);first=false;}o<<"</td></tr>";}
 o<<"</table><h2>By subject</h2><table><tr><th>Subject</th><th>Questions</th></tr>";
 for(const auto&x:subjects)o<<"<tr><td>"<<esc(x.first)<<"</td><td>"<<x.second<<"</td></tr>";
 o<<"</table><h2>By exam year</h2><table><tr><th>Year</th><th>Questions</th></tr>";
 for(const auto&x:years)o<<"<tr><td>"<<esc(x.first)<<"</td><td>"<<x.second<<"</td></tr>";
 o<<"</table></body></html>";if(!o&&error)*error="Paper summary write failed";return static_cast<bool>(o);
}