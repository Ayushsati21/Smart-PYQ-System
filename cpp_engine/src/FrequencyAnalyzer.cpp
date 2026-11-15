#include "Engine.h"
#include <unordered_map>
#include <algorithm>
std::vector<FrequencyRecord> FrequencyAnalyzer::analyze(const std::vector<Question>& qs) const {
    std::unordered_map<std::string,FrequencyRecord> map;
    for(const auto& q:qs) { auto& r=map[q.normalized]; if(r.count==0)r.text=q.text; ++r.count; }
    std::vector<FrequencyRecord> out;
    for(auto& p:map)if(p.second.count>1)out.push_back(p.second);
    std::sort(out.begin(),out.end(),[](const auto&a,const auto&b){return a.count>b.count;});
    return out;
}
