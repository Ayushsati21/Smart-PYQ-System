
#include <iostream>
#include <string>
using namespace std;

class QuestionPaper {
public:
    int paperId;
    int examYear;
    string fileName;
    string subject;
    string academicYear;
    string term;

    QuestionPaper(int id, int year, string file, string sub,
                  string academic, string t) {
        paperId = id;
        examYear = year;
        fileName = file;
        subject = sub;
        academicYear = academic;
        term = t;
    }
};

int main() {
    QuestionPaper p(101, 2025, "DSA.pdf",
                    "Data Structures", "2024-2025", "End Term");

    cout << "Paper ID: " << p.paperId << endl;
    cout << "Subject: " << p.subject << endl;
    cout << "Exam Year: " << p.examYear << endl;
    cout << "File Name: " << p.fileName << endl;
    cout << "Academic Year: " << p.academicYear << endl;
    cout << "Term: " << p.term << endl;

    return 0;
}
