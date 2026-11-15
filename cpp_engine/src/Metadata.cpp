#include "Engine.h"
#include <fstream>
#include <algorithm>
#include <cctype>

namespace {
std::string trimValue(std::string s) {
    const auto a=s.find_first_not_of(" \t\r\n");
    if(a==std::string::npos) return {};
    const auto b=s.find_last_not_of(" \t\r\n");
    return s.substr(a,b-a+1);
}
std::string lowerKey(std::string s) {
    std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return static_cast<char>(std::tolower(c));});
    return s;
}
}

PaperMetadata loadMetadata(const std::string& path) {
    PaperMetadata m;
    std::ifstream in(path);
    if(!in) return m;
    std::string line;
    while(std::getline(in,line)) {
        auto pos=line.find('=');
        if(pos==std::string::npos) continue;
        auto key=lowerKey(trimValue(line.substr(0,pos)));
        auto value=trimValue(line.substr(pos+1));
        if(key=="course") m.course=value;
        else if(key=="academicyear" || key=="academic_year") m.academicYear=value;
        else if(key=="examyear" || key=="exam_year") m.examYear=value;
        else if(key=="subject") m.subject=value;
        else if(key=="term") m.term=value;
        else if(key=="papercode" || key=="paper_code") m.paperCode=value;
    }
    return m;
}
