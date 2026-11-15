#include "StudyPlanner.h"
#include "Engine.h"
#include <algorithm>
#include <cmath>
#include <map>
#include <set>
namespace {
struct Bucket{StudyPriority row;std::set<std::string> years,papers;};
std::string keyOf(const Question&q){if(!q.fingerprint.empty())return q.fingerprint;
 return SHA256::hash(q.normalized.empty()?TextNormalizer::normalize(q.text):q.normalized);}
}
StudyPlan StudyPlanner::build(const std::vector<Question>& questions,std::size_t limit,std::size_t minimum)const{
 StudyPlan plan;plan.sourceQuestions=questions.size();std::map<std::string,Bucket> groups;
 for(const auto&q:questions){auto& b=groups[keyOf(q)];if(!b.row.appearances){b.row.questionNumber=q.number;b.row.questionText=q.text;b.row.subject=q.paper.subject;}
 ++b.row.appearances;if(!q.paper.examYear.empty())b.years.insert(q.paper.examYear);
 if(!q.paper.paperCode.empty())b.papers.insert(q.paper.paperCode);}
 plan.uniqueTopics=groups.size();
 for(auto& pair:groups){auto& b=pair.second;b.row.distinctExamYears=b.years.size();b.row.years.assign(b.years.begin(),b.years.end());
 if(b.row.appearances<minimum)continue;
 const double frequency=std::log1p(static_cast<double>(b.row.appearances))*10.0;
 const double recurrence=static_cast<double>(b.row.distinctExamYears)*3.0;
 const double spread=static_cast<double>(std::min<std::size_t>(b.papers.size(),5));
 b.row.priorityScore=frequency+recurrence+spread;plan.priorities.push_back(std::move(b.row));}
 std::stable_sort(plan.priorities.begin(),plan.priorities.end(),[](const StudyPriority&a,const StudyPriority&b){
 if(a.priorityScore!=b.priorityScore)return a.priorityScore>b.priorityScore;
 if(a.appearances!=b.appearances)return a.appearances>b.appearances;return a.questionText<b.questionText;});
 if(plan.priorities.size()>limit)plan.priorities.resize(limit);return plan;
}
std::string StudyPlanner::explain(const StudyPriority&p){
 std::string s=std::to_string(p.appearances)+" appearances";
 if(p.distinctExamYears)s+=" across "+std::to_string(p.distinctExamYears)+" exam years";
 if(!p.years.empty()){s+=" (";for(std::size_t i=0;i<p.years.size();++i){if(i)s+=", ";s+=p.years[i];}s+=")";}return s;
}