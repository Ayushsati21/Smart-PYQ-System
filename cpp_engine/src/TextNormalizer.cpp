#include "Engine.h"
#include <cctype>
std::string TextNormalizer::normalize(const std::string& input) {
    std::string out; bool space=false;
    for (unsigned char c : input) {
        if (std::isspace(c)) { space=!out.empty(); continue; }
        if (space) { out+=' '; space=false; }
        out+=static_cast<char>(std::tolower(c));
    }
    for (std::size_t i=1;i<out.size();) {
        if ((out[i]==','||out[i]==';'||out[i]==':'||out[i]=='.'||out[i]=='?'||out[i]=='!') && out[i-1]==' ')
            out.erase(i-1,1);
        else ++i;
    }
    return out;
}
