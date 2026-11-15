#include "Engine.h"
#include <set>
#include <cctype>
namespace {
std::set<std::string> words(const std::string&s) {
    std::set<std::string> out; std::string w;
    for(unsigned char c:s) { if(std::isalnum(c))w+=std::tolower(c); else if(!w.empty()){out.insert(w);w.clear();} }
    if(!w.empty()) out.insert(w);
    return out;
}
}
double SimilarityEngine::jaccard(const std::string&a,const std::string&b) {
    auto x=words(a),y=words(b); if(x.empty()&&y.empty())return 1.0;
    if(x.empty()||y.empty())return 0.0;
    std::size_t common=0;for(const auto&w:x)if(y.count(w))++common;
    return static_cast<double>(common)/(x.size()+y.size()-common);
}
