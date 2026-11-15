#include "Export.h"
#include <fstream>

namespace {
std::string quoteCsv(const std::string& value) {
    std::string out = "\"";
    for (char ch : value) {
        if (ch == '"') out += "\"\"";
        else out += ch;
    }
    out += "\"";
    return out;
}
}
bool QuestionExport::toCsv(const std::string& path, const std::vector<Question>& questions,
                           std::string* error) {
    std::ofstream out(path, std::ios::binary);
    if (!out) { if (error) *error = "Unable to open output file: " + path; return false; }
    out << "paper_code,subject,academic_year,exam_year,term,question_number,question_text,fingerprint\r\n";
    for (const auto& q : questions) {
        out << quoteCsv(q.paper.paperCode) << ','
            << quoteCsv(q.paper.subject) << ','
            << quoteCsv(q.paper.academicYear) << ','
            << quoteCsv(q.paper.examYear) << ','
            << quoteCsv(q.paper.term) << ','
            << quoteCsv(q.number) << ','
            << quoteCsv(q.text) << ','
            << quoteCsv(q.fingerprint) << "\r\n";
    }
    if (!out.good()) { if (error) *error = "Write failed while exporting CSV"; return false; }
    return true;
}
