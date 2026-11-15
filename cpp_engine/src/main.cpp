#include "Engine.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
#include <algorithm>

static std::string paperLabel(const PaperMetadata& m, const std::string& fallback) {
    if(!m.paperCode.empty()) return m.paperCode;
    if(!m.subject.empty() || !m.examYear.empty()) return m.subject + " " + m.examYear;
    return fallback;
}

int main(int argc,char**argv) {
    if(argc<2){std::cerr<<"Usage: smart_pyq_cpp <paper1.txt> [paper2.txt ...]\nEach TXT may have a same-name .meta sidecar.\n";return 1;}
    std::vector<Question> all;
    for(int i=1;i<argc;++i) {
        const std::string path=argv[i];
        std::ifstream f(path);
        if(!f){std::cerr<<"Cannot open input file: "<<path<<"\n";continue;}
        std::string content((std::istreambuf_iterator<char>(f)),{});
        const std::string metaPath=path.substr(0,path.find_last_of('.'))+".meta";
        PaperMetadata meta=loadMetadata(metaPath);
        std::string label=paperLabel(meta,path);
        auto parsed=QuestionParser{}.parse(content,meta);
        for(auto& q:parsed) all.push_back(std::move(q));
        std::cout<<"Loaded "<<path<<" as ["<<label<<"]: "<<parsed.size()<<" questions\n";
    }
    std::cout<<"\nSMART PYQ C++ PROCESSING ENGINE — MILESTONE 3\nTotal questions parsed: "<<all.size()<<"\n";
    for(const auto&q:all) {
        std::cout<<q.paper.paperCode<<" | "<<q.paper.subject<<" | "<<q.paper.examYear<<" | "<<q.number<<" | "<<q.text<<"\n";
    }
    std::cout<<"\nEXACT REPEATS ACROSS ALL LOADED PAPERS\n";
    auto repeated=FrequencyAnalyzer{}.analyze(all);
    if(repeated.empty()) std::cout<<"No exact repeats found.\n";
    for(const auto&r:repeated) std::cout<<r.count<<"x | "<<r.text<<"\n";
    std::cout<<"\nCROSS-PAPER SIMILARITY PAIRS (Jaccard >= 0.50)\n";
    bool found=false;
    for(std::size_t i=0;i<all.size();++i) for(std::size_t j=i+1;j<all.size();++j) {
        const auto a=paperLabel(all[i].paper,"unknown"), b=paperLabel(all[j].paper,"unknown");
        if(a==b) continue;
        const double score=SimilarityEngine::jaccard(all[i].normalized,all[j].normalized);
        if(score>=0.50) { found=true; std::cout<<a<<" ["<<all[i].number<<"] vs "<<b<<" ["<<all[j].number<<"]: "<<score*100<<"%\n"; }
    }
    if(!found) std::cout<<"No cross-paper pairs met the threshold.\n";
}
