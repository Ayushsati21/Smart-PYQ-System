#include "Engine.h"
#include <regex>
#include <sstream>
#include <algorithm>
#include <cctype>
namespace {
std::string trim(const std::string& s) {
    auto a=s.find_first_not_of(" \t\r\n"); if(a==std::string::npos)return {};
    return s.substr(a,s.find_last_not_of(" \t\r\n")-a+1);
}
}
std::vector<Question> QuestionParser::parse(const std::string& input, const PaperMetadata& metadata) const {
    const std::regex mainRe(R"(^\s*(?:Q\s*)?(\d{1,3})\s*[.)]\s*(.*?)\s*$)",std::regex::icase);
    const std::regex subRe(R"(^\s*(?:\(([a-z])\)|([a-z])[.)])\s*(.*?)\s*$)",std::regex::icase);
    const std::regex romanRe(R"(^\s*\(([ivxlcdm]+)\)\s*(.*?)\s*$)",std::regex::icase);
    std::vector<Question> out; std::istringstream in(input); std::string line, main, sub, parentSub, body;
    auto save=[&](){ auto t=trim(body); if(!main.empty()&&!t.empty()) { auto normalized = TextNormalizer::normalize(t); out.push_back({main+sub,t,normalized,SHA256::hash(normalized),metadata}); } body.clear(); };
    while(std::getline(in,line)) {
        line=trim(line); if(line.empty()||line=="OR"||line=="or")continue;
        if(std::regex_match(line,std::regex(R"(^---\s*PAGE\s+\d+\s*---$)",std::regex::icase)))continue;
        std::smatch m;
        if(std::regex_match(line,m,mainRe)) {
            save(); main=m[1]; sub.clear(); parentSub.clear(); std::string rest=trim(m[2]);
            std::smatch sm;
            if(std::regex_match(rest,sm,subRe) && (sm[1].matched?sm[1].str():sm[2].str())=="a") {
                sub="(a)"; parentSub=sub; body=trim(sm[3]);
            } else {
                std::string lower = rest;
                std::transform(lower.begin(), lower.end(), lower.begin(),
                    [](unsigned char c){ return static_cast<char>(std::tolower(c)); });
                if (lower.rfind("answer the following", 0) == 0 ||
                    lower.rfind("attempt any", 0) == 0 ||
                    lower.rfind("answer any", 0) == 0 || lower.rfind("answer briefly", 0) == 0) body.clear();
                else body=rest;
            }
            continue;
        }
        if(!main.empty()&&std::regex_match(line,m,subRe)) {
            std::string label=m[1].matched?m[1].str():m[2].str();
            std::transform(label.begin(),label.end(),label.begin(),[](unsigned char c){return static_cast<char>(std::tolower(c));});
            const bool nextAlpha = label.size()==1 && label[0]>='a' && label[0]<='z' &&
                (parentSub.empty()?label=="a":(parentSub.size()==3 && parentSub[0]=='(' && parentSub[2]==')' && label[0]==parentSub[1]+1));
            if(nextAlpha) { save(); sub="("+label+")"; parentSub=sub; body=trim(m[3]); continue; }
        }
        if(!main.empty() && !sub.empty() && std::regex_match(line,m,romanRe)) {
            save();
            std::string roman=m[1];
            std::transform(roman.begin(),roman.end(),roman.begin(),[](unsigned char c){return static_cast<char>(std::tolower(c));});
            sub = parentSub + "(" + roman + ")";
            body=trim(m[2]);
            continue;
        }
        if(!body.empty()) body+=' ';
        body+=line;
    }
    save(); return out;
}
